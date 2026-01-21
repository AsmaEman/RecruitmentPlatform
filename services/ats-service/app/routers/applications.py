from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from uuid import UUID
import asyncio
import logging

from ..database import get_db
from ..models import Application, ApplicationStatusHistory
from ..schemas import ApplicationCreate, ApplicationResponse, ApplicationStatusUpdate, BulkStatusUpdate
from ..services.workflow_service import WorkflowService
from ..services.notification_service import NotificationService

router = APIRouter()
logger = logging.getLogger(__name__)

# In-memory store for bulk operation progress (in production, use Redis)
bulk_operation_progress = {}

@router.post("/", response_model=ApplicationResponse, status_code=status.HTTP_201_CREATED)
async def create_application(application_data: ApplicationCreate, db: Session = Depends(get_db)):
    """Submit a new application"""
    # Check if application already exists
    existing_application = db.query(Application).filter(
        Application.candidate_id == application_data.candidate_id,
        Application.job_id == application_data.job_id
    ).first()
    
    if existing_application:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Application already exists for this candidate and job"
        )
    
    db_application = Application(**application_data.dict())
    db.add(db_application)
    db.commit()
    db.refresh(db_application)
    
    return db_application

@router.get("/", response_model=List[ApplicationResponse])
async def list_applications(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[str] = Query(None),
    candidate_id: Optional[UUID] = Query(None),
    job_id: Optional[UUID] = Query(None),
    db: Session = Depends(get_db)
):
    """List applications with pagination and filtering"""
    query = db.query(Application)
    
    if status:
        query = query.filter(Application.status == status)
    
    if candidate_id:
        query = query.filter(Application.candidate_id == candidate_id)
    
    if job_id:
        query = query.filter(Application.job_id == job_id)
    
    applications = query.offset(skip).limit(limit).all()
    return applications

@router.get("/{application_id}", response_model=ApplicationResponse)
async def get_application(application_id: UUID, db: Session = Depends(get_db)):
    """Get a specific application by ID"""
    application = db.query(Application).filter(Application.id == application_id).first()
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found"
        )
    return application

@router.put("/{application_id}/status", response_model=ApplicationResponse)
async def update_application_status(
    application_id: UUID,
    status_data: ApplicationStatusUpdate,
    db: Session = Depends(get_db)
):
    """Update application status"""
    application = db.query(Application).filter(Application.id == application_id).first()
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found"
        )
    
    # Record status change in history
    status_history = ApplicationStatusHistory(
        application_id=application.id,
        previous_status=application.status,
        new_status=status_data.status,
        changed_by=status_data.changed_by,
        change_reason=status_data.reason
    )
    
    # Update application status
    application.status = status_data.status
    
    db.add(status_history)
    db.commit()
    db.refresh(application)
    
    return application

@router.post("/bulk-action", status_code=status.HTTP_202_ACCEPTED)
async def bulk_status_update(
    bulk_data: BulkStatusUpdate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Perform bulk status updates on multiple applications with progress tracking"""
    
    # Validate applications exist
    applications = db.query(Application).filter(
        Application.id.in_(bulk_data.application_ids)
    ).all()
    
    if len(applications) != len(bulk_data.application_ids):
        missing_ids = set(bulk_data.application_ids) - {app.id for app in applications}
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Applications not found: {list(missing_ids)}"
        )
    
    # Create operation ID for progress tracking
    operation_id = f"bulk_{len(bulk_data.application_ids)}_{bulk_data.new_status}_{bulk_data.changed_by}"
    
    # Initialize progress tracking
    bulk_operation_progress[operation_id] = {
        "total": len(bulk_data.application_ids),
        "processed": 0,
        "successful": 0,
        "failed": 0,
        "status": "in_progress",
        "errors": [],
        "started_at": None,
        "completed_at": None
    }
    
    # Start background task for bulk processing
    background_tasks.add_task(
        process_bulk_status_update,
        operation_id,
        bulk_data,
        db
    )
    
    return {
        "operation_id": operation_id,
        "message": f"Bulk operation started for {len(bulk_data.application_ids)} applications",
        "total_applications": len(bulk_data.application_ids),
        "status": "in_progress"
    }

async def process_bulk_status_update(
    operation_id: str,
    bulk_data: BulkStatusUpdate,
    db: Session
):
    """Background task to process bulk status updates"""
    from datetime import datetime
    
    progress = bulk_operation_progress[operation_id]
    progress["started_at"] = datetime.utcnow()
    
    try:
        # Initialize services
        workflow_service = WorkflowService(db)
        notification_service = NotificationService(db)
        
        for app_id in bulk_data.application_ids:
            try:
                # Get the application
                application = db.query(Application).filter(
                    Application.id == app_id
                ).first()
                
                if not application:
                    progress["errors"].append(f"Application {app_id} not found")
                    progress["failed"] += 1
                    continue
                
                # Record status change in history
                status_history = ApplicationStatusHistory(
                    application_id=application.id,
                    previous_status=application.status,
                    new_status=bulk_data.new_status,
                    changed_by=bulk_data.changed_by,
                    change_reason=f"Bulk operation: {bulk_data.reason or 'No reason provided'}"
                )
                
                # Update application status
                old_status = application.status
                application.status = bulk_data.new_status
                
                db.add(status_history)
                db.commit()
                db.refresh(status_history)
                
                # Send notification if required
                if notification_service.should_send_notification(status_history):
                    try:
                        notification_service.send_status_change_notification(
                            application.id, status_history
                        )
                    except Exception as e:
                        logger.warning(f"Failed to send notification for application {app_id}: {e}")
                
                progress["successful"] += 1
                logger.info(f"Bulk operation: Updated application {app_id} from {old_status} to {bulk_data.new_status}")
                
            except Exception as e:
                progress["errors"].append(f"Application {app_id}: {str(e)}")
                progress["failed"] += 1
                logger.error(f"Bulk operation failed for application {app_id}: {e}")
                db.rollback()
            
            finally:
                progress["processed"] += 1
        
        progress["status"] = "completed"
        progress["completed_at"] = datetime.utcnow()
        
        logger.info(f"Bulk operation {operation_id} completed: {progress['successful']} successful, {progress['failed']} failed")
        
    except Exception as e:
        progress["status"] = "failed"
        progress["completed_at"] = datetime.utcnow()
        progress["errors"].append(f"Bulk operation failed: {str(e)}")
        logger.error(f"Bulk operation {operation_id} failed: {e}")
    
    finally:
        db.close()

@router.get("/bulk-action/{operation_id}/progress")
async def get_bulk_operation_progress(operation_id: str):
    """Get progress of a bulk operation"""
    if operation_id not in bulk_operation_progress:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bulk operation not found"
        )
    
    progress = bulk_operation_progress[operation_id]
    
    # Calculate progress percentage
    progress_percentage = 0
    if progress["total"] > 0:
        progress_percentage = (progress["processed"] / progress["total"]) * 100
    
    return {
        "operation_id": operation_id,
        "status": progress["status"],
        "total": progress["total"],
        "processed": progress["processed"],
        "successful": progress["successful"],
        "failed": progress["failed"],
        "progress_percentage": round(progress_percentage, 2),
        "errors": progress["errors"],
        "started_at": progress["started_at"],
        "completed_at": progress["completed_at"]
    }

@router.post("/bulk-reject", status_code=status.HTTP_202_ACCEPTED)
async def bulk_reject_applications(
    application_ids: List[UUID],
    rejection_reason: str,
    changed_by: UUID,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Bulk reject multiple applications"""
    
    bulk_data = BulkStatusUpdate(
        application_ids=application_ids,
        new_status="rejected",
        changed_by=changed_by,
        reason=f"Bulk rejection: {rejection_reason}"
    )
    
    return await bulk_status_update(bulk_data, background_tasks, db)

@router.post("/bulk-approve", status_code=status.HTTP_202_ACCEPTED)
async def bulk_approve_applications(
    application_ids: List[UUID],
    approval_reason: str,
    changed_by: UUID,
    background_tasks: BackgroundTasks,
    next_stage: str = "interview",
    db: Session = Depends(get_db)
):
    """Bulk approve multiple applications and move to next stage"""
    
    bulk_data = BulkStatusUpdate(
        application_ids=application_ids,
        new_status=next_stage,
        changed_by=changed_by,
        reason=f"Bulk approval: {approval_reason}"
    )
    
    return await bulk_status_update(bulk_data, background_tasks, db)

@router.post("/bulk-move-stage", status_code=status.HTTP_202_ACCEPTED)
async def bulk_move_to_stage(
    application_ids: List[UUID],
    stage_id: UUID,
    changed_by: UUID,
    background_tasks: BackgroundTasks,
    reason: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Bulk move applications to a specific workflow stage"""
    
    # Get the stage to determine the status name
    from ..models import WorkflowStage
    stage = db.query(WorkflowStage).filter(WorkflowStage.id == stage_id).first()
    
    if not stage:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow stage not found"
        )
    
    # Create operation ID for progress tracking
    operation_id = f"bulk_stage_{len(application_ids)}_{stage_id}_{changed_by}"
    
    # Initialize progress tracking
    bulk_operation_progress[operation_id] = {
        "total": len(application_ids),
        "processed": 0,
        "successful": 0,
        "failed": 0,
        "status": "in_progress",
        "errors": [],
        "started_at": None,
        "completed_at": None
    }
    
    # Start background task for bulk stage movement
    background_tasks.add_task(
        process_bulk_stage_movement,
        operation_id,
        application_ids,
        stage_id,
        changed_by,
        reason,
        db
    )
    
    return {
        "operation_id": operation_id,
        "message": f"Bulk stage movement started for {len(application_ids)} applications to stage '{stage.name}'",
        "total_applications": len(application_ids),
        "target_stage": stage.name,
        "status": "in_progress"
    }

async def process_bulk_stage_movement(
    operation_id: str,
    application_ids: List[UUID],
    stage_id: UUID,
    changed_by: UUID,
    reason: Optional[str],
    db: Session
):
    """Background task to process bulk stage movements"""
    from datetime import datetime
    
    progress = bulk_operation_progress[operation_id]
    progress["started_at"] = datetime.utcnow()
    
    try:
        workflow_service = WorkflowService(db)
        
        for app_id in application_ids:
            try:
                # Advance application to the specified stage
                workflow_service.advance_application_to_stage(
                    application_id=app_id,
                    stage_id=stage_id,
                    user_id=changed_by,
                    notes=reason
                )
                
                progress["successful"] += 1
                logger.info(f"Bulk stage movement: Moved application {app_id} to stage {stage_id}")
                
            except Exception as e:
                progress["errors"].append(f"Application {app_id}: {str(e)}")
                progress["failed"] += 1
                logger.error(f"Bulk stage movement failed for application {app_id}: {e}")
            
            finally:
                progress["processed"] += 1
        
        progress["status"] = "completed"
        progress["completed_at"] = datetime.utcnow()
        
        logger.info(f"Bulk stage movement {operation_id} completed: {progress['successful']} successful, {progress['failed']} failed")
        
    except Exception as e:
        progress["status"] = "failed"
        progress["completed_at"] = datetime.utcnow()
        progress["errors"].append(f"Bulk stage movement failed: {str(e)}")
        logger.error(f"Bulk stage movement {operation_id} failed: {e}")
    
    finally:
        db.close()

@router.get("/bulk-operations")
async def list_bulk_operations():
    """List all bulk operations and their status"""
    operations = []
    
    for operation_id, progress in bulk_operation_progress.items():
        progress_percentage = 0
        if progress["total"] > 0:
            progress_percentage = (progress["processed"] / progress["total"]) * 100
        
        operations.append({
            "operation_id": operation_id,
            "status": progress["status"],
            "total": progress["total"],
            "processed": progress["processed"],
            "successful": progress["successful"],
            "failed": progress["failed"],
            "progress_percentage": round(progress_percentage, 2),
            "started_at": progress["started_at"],
            "completed_at": progress["completed_at"],
            "error_count": len(progress["errors"])
        })
    
    return {"operations": operations}

@router.delete("/bulk-operations/{operation_id}")
async def cleanup_bulk_operation(operation_id: str):
    """Clean up completed bulk operation from memory"""
    if operation_id not in bulk_operation_progress:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bulk operation not found"
        )
    
    progress = bulk_operation_progress[operation_id]
    
    if progress["status"] == "in_progress":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot cleanup operation that is still in progress"
        )
    
    del bulk_operation_progress[operation_id]
    
    return {"message": f"Bulk operation {operation_id} cleaned up successfully"}