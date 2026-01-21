from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from uuid import UUID
import logging

from ..models import (
    Application, WorkflowStage, StageTransition, SLAEscalation, 
    ApplicationStatusHistory, JobPosting, User
)
from ..schemas import StageTransitionCreate

logger = logging.getLogger(__name__)

class WorkflowService:
    """Service for managing application workflow stages and SLA tracking"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_default_workflow_stages(self, job_id: UUID) -> List[WorkflowStage]:
        """Create default workflow stages for a job posting"""
        default_stages = [
            {"name": "Applied", "order_index": 1, "sla_hours": 24},
            {"name": "Initial Screening", "order_index": 2, "sla_hours": 48},
            {"name": "Technical Assessment", "order_index": 3, "sla_hours": 72},
            {"name": "Interview", "order_index": 4, "sla_hours": 96},
            {"name": "Final Review", "order_index": 5, "sla_hours": 48},
            {"name": "Decision", "order_index": 6, "sla_hours": 24},
        ]
        
        stages = []
        for stage_data in default_stages:
            stage = WorkflowStage(
                job_id=job_id,
                name=stage_data["name"],
                order_index=stage_data["order_index"],
                sla_hours=stage_data["sla_hours"]
            )
            self.db.add(stage)
            stages.append(stage)
        
        self.db.commit()
        return stages
    
    def get_workflow_stages(self, job_id: UUID) -> List[WorkflowStage]:
        """Get all workflow stages for a job, ordered by index"""
        return self.db.query(WorkflowStage).filter(
            and_(
                WorkflowStage.job_id == job_id,
                WorkflowStage.is_active == True
            )
        ).order_by(WorkflowStage.order_index).all()
    
    def advance_application_to_stage(
        self, 
        application_id: UUID, 
        stage_id: UUID, 
        user_id: UUID,
        notes: Optional[str] = None
    ) -> StageTransition:
        """Advance an application to a specific workflow stage"""
        
        # Get the application
        application = self.db.query(Application).filter(
            Application.id == application_id
        ).first()
        
        if not application:
            raise ValueError(f"Application {application_id} not found")
        
        # Get the target stage
        target_stage = self.db.query(WorkflowStage).filter(
            WorkflowStage.id == stage_id
        ).first()
        
        if not target_stage:
            raise ValueError(f"Workflow stage {stage_id} not found")
        
        # Close any current stage transition
        current_transition = self.db.query(StageTransition).filter(
            and_(
                StageTransition.application_id == application_id,
                StageTransition.exited_at.is_(None)
            )
        ).first()
        
        if current_transition:
            current_transition.exited_at = datetime.utcnow()
        
        # Calculate SLA deadline
        sla_deadline = datetime.utcnow() + timedelta(hours=target_stage.sla_hours)
        
        # Create new stage transition
        new_transition = StageTransition(
            application_id=application_id,
            stage_id=stage_id,
            sla_deadline=sla_deadline,
            notes=notes
        )
        
        self.db.add(new_transition)
        
        # Update application status to match stage name
        old_status = application.status
        application.status = target_stage.name.lower().replace(" ", "_")
        
        # Record status change in history
        status_history = ApplicationStatusHistory(
            application_id=application_id,
            previous_status=old_status,
            new_status=application.status,
            changed_by=user_id,
            change_reason=f"Advanced to stage: {target_stage.name}"
        )
        
        self.db.add(status_history)
        self.db.commit()
        self.db.refresh(new_transition)
        
        logger.info(f"Application {application_id} advanced to stage {target_stage.name}")
        return new_transition
    
    def get_current_stage_transition(self, application_id: UUID) -> Optional[StageTransition]:
        """Get the current active stage transition for an application"""
        return self.db.query(StageTransition).filter(
            and_(
                StageTransition.application_id == application_id,
                StageTransition.exited_at.is_(None)
            )
        ).first()
    
    def check_sla_violations(self) -> List[StageTransition]:
        """Check for applications that have exceeded their SLA deadlines"""
        now = datetime.utcnow()
        
        overdue_transitions = self.db.query(StageTransition).filter(
            and_(
                StageTransition.exited_at.is_(None),
                StageTransition.sla_deadline < now,
                StageTransition.is_escalated == False
            )
        ).all()
        
        return overdue_transitions
    
    def escalate_sla_violation(
        self, 
        stage_transition: StageTransition, 
        escalation_type: str = "overdue"
    ) -> SLAEscalation:
        """Escalate an SLA violation to the hiring manager"""
        
        # Get the job's hiring manager (creator)
        application = stage_transition.application
        job = self.db.query(JobPosting).filter(
            JobPosting.id == application.job_id
        ).first()
        
        if not job:
            raise ValueError(f"Job posting not found for application {application.id}")
        
        # Create escalation record
        escalation = SLAEscalation(
            application_id=application.id,
            stage_transition_id=stage_transition.id,
            escalation_type=escalation_type,
            escalated_to=job.created_by,
            escalation_reason=f"Application has exceeded SLA deadline by {datetime.utcnow() - stage_transition.sla_deadline}"
        )
        
        # Mark stage transition as escalated
        stage_transition.is_escalated = True
        stage_transition.escalated_at = datetime.utcnow()
        stage_transition.escalated_to = job.created_by
        
        self.db.add(escalation)
        self.db.commit()
        self.db.refresh(escalation)
        
        logger.warning(f"SLA violation escalated for application {application.id}")
        return escalation
    
    def get_applications_by_stage(self, job_id: UUID, stage_name: str) -> List[Application]:
        """Get all applications currently in a specific stage"""
        
        # Get the stage
        stage = self.db.query(WorkflowStage).filter(
            and_(
                WorkflowStage.job_id == job_id,
                WorkflowStage.name == stage_name,
                WorkflowStage.is_active == True
            )
        ).first()
        
        if not stage:
            return []
        
        # Get applications in this stage
        current_transitions = self.db.query(StageTransition).filter(
            and_(
                StageTransition.stage_id == stage.id,
                StageTransition.exited_at.is_(None)
            )
        ).all()
        
        application_ids = [t.application_id for t in current_transitions]
        
        return self.db.query(Application).filter(
            Application.id.in_(application_ids)
        ).all()
    
    def get_escalated_applications(self, user_id: UUID) -> List[Dict[str, Any]]:
        """Get all applications escalated to a specific user"""
        
        escalations = self.db.query(SLAEscalation).filter(
            and_(
                SLAEscalation.escalated_to == user_id,
                SLAEscalation.is_resolved == False
            )
        ).all()
        
        result = []
        for escalation in escalations:
            application = escalation.application
            stage_transition = escalation.stage_transition
            stage = stage_transition.stage
            
            result.append({
                "escalation_id": escalation.id,
                "application_id": application.id,
                "candidate_name": f"{application.candidate.first_name} {application.candidate.last_name}",
                "job_title": application.job.title,
                "stage_name": stage.name,
                "escalation_type": escalation.escalation_type,
                "overdue_hours": (datetime.utcnow() - stage_transition.sla_deadline).total_seconds() / 3600,
                "escalated_at": escalation.created_at
            })
        
        return result
    
    def resolve_escalation(
        self, 
        escalation_id: UUID, 
        resolved_by: UUID
    ) -> SLAEscalation:
        """Mark an escalation as resolved"""
        
        escalation = self.db.query(SLAEscalation).filter(
            SLAEscalation.id == escalation_id
        ).first()
        
        if not escalation:
            raise ValueError(f"Escalation {escalation_id} not found")
        
        escalation.is_resolved = True
        escalation.resolved_at = datetime.utcnow()
        escalation.resolved_by = resolved_by
        
        self.db.commit()
        self.db.refresh(escalation)
        
        logger.info(f"Escalation {escalation_id} resolved by user {resolved_by}")
        return escalation
    
    def get_application_timeline(self, application_id: UUID) -> List[Dict[str, Any]]:
        """Get the complete timeline of stage transitions for an application"""
        
        transitions = self.db.query(StageTransition).filter(
            StageTransition.application_id == application_id
        ).order_by(StageTransition.entered_at).all()
        
        timeline = []
        for transition in transitions:
            stage = transition.stage
            duration = None
            
            if transition.exited_at:
                duration = (transition.exited_at - transition.entered_at).total_seconds() / 3600
            
            timeline.append({
                "stage_name": stage.name,
                "entered_at": transition.entered_at,
                "exited_at": transition.exited_at,
                "duration_hours": duration,
                "sla_deadline": transition.sla_deadline,
                "is_escalated": transition.is_escalated,
                "notes": transition.notes
            })
        
        return timeline