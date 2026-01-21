from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID

from ..database import get_db
from ..models import Application, ApplicationStatusHistory
from ..schemas import ApplicationCreate, ApplicationResponse, ApplicationStatusUpdate, BulkStatusUpdate

router = APIRouter()

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

@router.post("/bulk-action", status_code=status.HTTP_200_OK)
async def bulk_status_update(
    bulk_data: BulkStatusUpdate,
    db: Session = Depends(get_db)
):
    """Perform bulk status updates on multiple applications"""
    applications = db.query(Application).filter(
        Application.id.in_(bulk_data.application_ids)
    ).all()
    
    if len(applications) != len(bulk_data.application_ids):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Some applications not found"
        )
    
    updated_count = 0
    for application in applications:
        # Record status change in history
        status_history = ApplicationStatusHistory(
            application_id=application.id,
            previous_status=application.status,
            new_status=bulk_data.new_status,
            changed_by=bulk_data.changed_by,
            change_reason=bulk_data.reason
        )
        
        # Update application status
        application.status = bulk_data.new_status
        db.add(status_history)
        updated_count += 1
    
    db.commit()
    
    return {
        "message": f"Successfully updated {updated_count} applications",
        "updated_count": updated_count
    }