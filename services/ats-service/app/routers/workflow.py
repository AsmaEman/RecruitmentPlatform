from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from uuid import UUID

from ..database import get_db
from ..models import WorkflowStage, StageTransition, SLAEscalation
from ..schemas import (
    WorkflowStageCreate, WorkflowStageResponse, 
    StageTransitionCreate, StageTransitionResponse,
    SLAEscalationResponse
)
from ..services.workflow_service import WorkflowService

router = APIRouter()

@router.post("/stages", response_model=WorkflowStageResponse, status_code=status.HTTP_201_CREATED)
async def create_workflow_stage(
    stage_data: WorkflowStageCreate, 
    db: Session = Depends(get_db)
):
    """Create a new workflow stage for a job"""
    db_stage = WorkflowStage(**stage_data.dict())
    db.add(db_stage)
    db.commit()
    db.refresh(db_stage)
    return db_stage

@router.get("/stages/job/{job_id}", response_model=List[WorkflowStageResponse])
async def get_job_workflow_stages(
    job_id: UUID,
    db: Session = Depends(get_db)
):
    """Get all workflow stages for a specific job"""
    workflow_service = WorkflowService(db)
    stages = workflow_service.get_workflow_stages(job_id)
    return stages

@router.post("/stages/job/{job_id}/default", response_model=List[WorkflowStageResponse])
async def create_default_workflow_stages(
    job_id: UUID,
    db: Session = Depends(get_db)
):
    """Create default workflow stages for a job"""
    workflow_service = WorkflowService(db)
    stages = workflow_service.create_default_workflow_stages(job_id)
    return stages

@router.post("/transitions", response_model=StageTransitionResponse, status_code=status.HTTP_201_CREATED)
async def advance_application_stage(
    transition_data: StageTransitionCreate,
    user_id: UUID = Query(..., description="ID of the user making the transition"),
    db: Session = Depends(get_db)
):
    """Advance an application to a specific workflow stage"""
    workflow_service = WorkflowService(db)
    
    try:
        transition = workflow_service.advance_application_to_stage(
            application_id=transition_data.application_id,
            stage_id=transition_data.stage_id,
            user_id=user_id,
            notes=transition_data.notes
        )
        return transition
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/transitions/application/{application_id}/current", response_model=Optional[StageTransitionResponse])
async def get_current_stage_transition(
    application_id: UUID,
    db: Session = Depends(get_db)
):
    """Get the current active stage transition for an application"""
    workflow_service = WorkflowService(db)
    transition = workflow_service.get_current_stage_transition(application_id)
    return transition

@router.get("/transitions/application/{application_id}/timeline")
async def get_application_timeline(
    application_id: UUID,
    db: Session = Depends(get_db)
):
    """Get the complete timeline of stage transitions for an application"""
    workflow_service = WorkflowService(db)
    timeline = workflow_service.get_application_timeline(application_id)
    return {"application_id": application_id, "timeline": timeline}

@router.get("/sla/violations", response_model=List[StageTransitionResponse])
async def check_sla_violations(db: Session = Depends(get_db)):
    """Check for applications that have exceeded their SLA deadlines"""
    workflow_service = WorkflowService(db)
    violations = workflow_service.check_sla_violations()
    return violations

@router.post("/sla/escalate/{stage_transition_id}", response_model=SLAEscalationResponse)
async def escalate_sla_violation(
    stage_transition_id: UUID,
    escalation_type: str = Query("overdue", description="Type of escalation"),
    db: Session = Depends(get_db)
):
    """Escalate an SLA violation to the hiring manager"""
    workflow_service = WorkflowService(db)
    
    # Get the stage transition
    stage_transition = db.query(StageTransition).filter(
        StageTransition.id == stage_transition_id
    ).first()
    
    if not stage_transition:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stage transition not found"
        )
    
    try:
        escalation = workflow_service.escalate_sla_violation(
            stage_transition=stage_transition,
            escalation_type=escalation_type
        )
        return escalation
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/escalations/user/{user_id}")
async def get_user_escalations(
    user_id: UUID,
    db: Session = Depends(get_db)
):
    """Get all applications escalated to a specific user"""
    workflow_service = WorkflowService(db)
    escalations = workflow_service.get_escalated_applications(user_id)
    return {"user_id": user_id, "escalations": escalations}

@router.put("/escalations/{escalation_id}/resolve", response_model=SLAEscalationResponse)
async def resolve_escalation(
    escalation_id: UUID,
    resolved_by: UUID = Query(..., description="ID of the user resolving the escalation"),
    db: Session = Depends(get_db)
):
    """Mark an escalation as resolved"""
    workflow_service = WorkflowService(db)
    
    try:
        escalation = workflow_service.resolve_escalation(
            escalation_id=escalation_id,
            resolved_by=resolved_by
        )
        return escalation
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/applications/stage/{job_id}/{stage_name}")
async def get_applications_by_stage(
    job_id: UUID,
    stage_name: str,
    db: Session = Depends(get_db)
):
    """Get all applications currently in a specific stage"""
    workflow_service = WorkflowService(db)
    applications = workflow_service.get_applications_by_stage(job_id, stage_name)
    
    return {
        "job_id": job_id,
        "stage_name": stage_name,
        "applications": [
            {
                "id": app.id,
                "candidate_id": app.candidate_id,
                "candidate_name": f"{app.candidate.first_name} {app.candidate.last_name}",
                "match_score": app.match_score,
                "applied_at": app.applied_at
            }
            for app in applications
        ]
    }