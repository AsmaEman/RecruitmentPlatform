"""
Unit tests for workflow system functionality.

Tests stage transitions, SLA escalation triggers, and bulk operation functionality.
Requirements: 1.2, 1.5, 1.7
"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4
from sqlalchemy.orm import Session

from app.models import (
    User, Candidate, JobPosting, Application, WorkflowStage, 
    StageTransition, SLAEscalation, ApplicationStatusHistory
)
from app.services.workflow_service import WorkflowService
from tests.conftest import TestingSessionLocal, engine


class TestWorkflowService:
    """Test cases for WorkflowService"""
    
    def setup_method(self):
        """Set up test data for each test method"""
        from app.models import Base
        Base.metadata.create_all(bind=engine)
        self.db = TestingSessionLocal()
        
        # Create test user
        self.user = User(
            email="workflow.test@example.com",
            password_hash="hashed_password",
            first_name="Workflow",
            last_name="Tester",
            role="recruiter"
        )
        self.db.add(self.user)
        self.db.commit()
        self.db.refresh(self.user)
        
        # Create test candidate
        self.candidate = Candidate(
            email="candidate.workflow@example.com",
            first_name="Test",
            last_name="Candidate"
        )
        self.db.add(self.candidate)
        self.db.commit()
        self.db.refresh(self.candidate)
        
        # Create test job
        self.job = JobPosting(
            title="Workflow Test Job",
            description="Test job for workflow testing",
            requirements={"skills": ["testing"]},
            department="Engineering",
            employment_type="full-time",
            created_by=self.user.id
        )
        self.db.add(self.job)
        self.db.commit()
        self.db.refresh(self.job)
        
        # Create test application
        self.application = Application(
            candidate_id=self.candidate.id,
            job_id=self.job.id,
            status="applied"
        )
        self.db.add(self.application)
        self.db.commit()
        self.db.refresh(self.application)
        
        self.workflow_service = WorkflowService(self.db)
    
    def teardown_method(self):
        """Clean up after each test method"""
        self.db.close()
        from app.models import Base
        Base.metadata.drop_all(bind=engine)
    
    def test_create_default_workflow_stages(self):
        """Test creating default workflow stages for a job"""
        # Requirements: 1.2 - Custom recruitment pipeline stages
        
        stages = self.workflow_service.create_default_workflow_stages(self.job.id)
        
        # Verify correct number of stages created
        assert len(stages) == 6
        
        # Verify stage names and order
        expected_stages = [
            "Applied", "Initial Screening", "Technical Assessment", 
            "Interview", "Final Review", "Decision"
        ]
        
        for i, stage in enumerate(stages):
            assert stage.name == expected_stages[i]
            assert stage.order_index == i + 1
            assert stage.job_id == self.job.id
            assert stage.is_active == True
            assert stage.sla_hours > 0
        
        # Verify stages are persisted in database
        db_stages = self.workflow_service.get_workflow_stages(self.job.id)
        assert len(db_stages) == 6
        assert all(stage.job_id == self.job.id for stage in db_stages)
    
    def test_advance_application_to_stage(self):
        """Test advancing an application to a specific workflow stage"""
        # Requirements: 1.2 - Stage transitions and status management
        
        # Create workflow stages
        stages = self.workflow_service.create_default_workflow_stages(self.job.id)
        screening_stage = stages[1]  # "Initial Screening"
        
        # Advance application to screening stage
        transition = self.workflow_service.advance_application_to_stage(
            application_id=self.application.id,
            stage_id=screening_stage.id,
            user_id=self.user.id,
            notes="Moving to screening"
        )
        
        # Verify transition was created
        assert transition.application_id == self.application.id
        assert transition.stage_id == screening_stage.id
        assert transition.notes == "Moving to screening"
        assert transition.entered_at is not None
        assert transition.exited_at is None
        assert transition.sla_deadline is not None
        
        # Verify SLA deadline is calculated correctly
        expected_deadline = transition.entered_at + timedelta(hours=screening_stage.sla_hours)
        time_diff = abs((transition.sla_deadline - expected_deadline).total_seconds())
        assert time_diff < 60  # Within 1 minute tolerance
        
        # Verify application status was updated
        self.db.refresh(self.application)
        assert self.application.status == "initial_screening"
        
        # Verify status history was created
        history = self.db.query(ApplicationStatusHistory).filter(
            ApplicationStatusHistory.application_id == self.application.id
        ).first()
        
        assert history is not None
        assert history.previous_status == "applied"
        assert history.new_status == "initial_screening"
        assert history.changed_by == self.user.id
        assert "Advanced to stage: Initial Screening" in history.change_reason
    
    def test_get_current_stage_transition(self):
        """Test retrieving current active stage transition"""
        # Requirements: 1.2 - Application tracking functionality
        
        # Create workflow stages and advance application
        stages = self.workflow_service.create_default_workflow_stages(self.job.id)
        screening_stage = stages[1]
        
        transition = self.workflow_service.advance_application_to_stage(
            application_id=self.application.id,
            stage_id=screening_stage.id,
            user_id=self.user.id
        )
        
        # Get current transition
        current_transition = self.workflow_service.get_current_stage_transition(
            self.application.id
        )
        
        assert current_transition is not None
        assert current_transition.id == transition.id
        assert current_transition.exited_at is None
        
        # Advance to next stage
        interview_stage = stages[3]
        self.workflow_service.advance_application_to_stage(
            application_id=self.application.id,
            stage_id=interview_stage.id,
            user_id=self.user.id
        )
        
        # Verify current transition changed
        new_current_transition = self.workflow_service.get_current_stage_transition(
            self.application.id
        )
        
        assert new_current_transition.id != transition.id
        assert new_current_transition.stage_id == interview_stage.id
        
        # Verify previous transition was closed
        self.db.refresh(transition)
        assert transition.exited_at is not None
    
    def test_sla_violation_detection(self):
        """Test SLA violation detection and escalation"""
        # Requirements: 1.7 - SLA tracking and escalation rules
        
        # Create workflow stages
        stages = self.workflow_service.create_default_workflow_stages(self.job.id)
        screening_stage = stages[1]
        
        # Advance application to screening stage
        transition = self.workflow_service.advance_application_to_stage(
            application_id=self.application.id,
            stage_id=screening_stage.id,
            user_id=self.user.id
        )
        
        # Manually set SLA deadline to past to simulate violation
        past_deadline = datetime.utcnow() - timedelta(hours=1)
        transition.sla_deadline = past_deadline
        self.db.commit()
        
        # Check for SLA violations
        violations = self.workflow_service.check_sla_violations()
        
        assert len(violations) == 1
        assert violations[0].id == transition.id
        assert violations[0].is_escalated == False
        
        # Escalate the violation
        escalation = self.workflow_service.escalate_sla_violation(
            stage_transition=transition,
            escalation_type="overdue"
        )
        
        # Verify escalation was created
        assert escalation.application_id == self.application.id
        assert escalation.stage_transition_id == transition.id
        assert escalation.escalation_type == "overdue"
        assert escalation.escalated_to == self.job.created_by
        assert escalation.is_resolved == False
        
        # Verify transition was marked as escalated
        self.db.refresh(transition)
        assert transition.is_escalated == True
        assert transition.escalated_at is not None
        assert transition.escalated_to == self.job.created_by
        
        # Verify no more violations detected for escalated transition
        new_violations = self.workflow_service.check_sla_violations()
        assert len(new_violations) == 0
    
    def test_get_escalated_applications(self):
        """Test retrieving applications escalated to a user"""
        # Requirements: 1.7 - SLA escalation and management
        
        # Create workflow stages and advance application
        stages = self.workflow_service.create_default_workflow_stages(self.job.id)
        screening_stage = stages[1]
        
        transition = self.workflow_service.advance_application_to_stage(
            application_id=self.application.id,
            stage_id=screening_stage.id,
            user_id=self.user.id
        )
        
        # Set past deadline and escalate
        transition.sla_deadline = datetime.utcnow() - timedelta(hours=2)
        self.db.commit()
        
        escalation = self.workflow_service.escalate_sla_violation(
            stage_transition=transition,
            escalation_type="critical"
        )
        
        # Get escalated applications for the hiring manager
        escalated_apps = self.workflow_service.get_escalated_applications(self.job.created_by)
        
        assert len(escalated_apps) == 1
        
        escalated_app = escalated_apps[0]
        assert escalated_app["application_id"] == self.application.id
        assert escalated_app["escalation_id"] == escalation.id
        assert escalated_app["escalation_type"] == "critical"
        assert escalated_app["stage_name"] == "Initial Screening"
        assert escalated_app["overdue_hours"] > 0
        assert "Test Candidate" in escalated_app["candidate_name"]
        assert escalated_app["job_title"] == "Workflow Test Job"
    
    def test_resolve_escalation(self):
        """Test resolving an SLA escalation"""
        # Requirements: 1.7 - SLA escalation resolution
        
        # Create escalation scenario
        stages = self.workflow_service.create_default_workflow_stages(self.job.id)
        transition = self.workflow_service.advance_application_to_stage(
            application_id=self.application.id,
            stage_id=stages[1].id,
            user_id=self.user.id
        )
        
        transition.sla_deadline = datetime.utcnow() - timedelta(hours=1)
        self.db.commit()
        
        escalation = self.workflow_service.escalate_sla_violation(
            stage_transition=transition,
            escalation_type="overdue"
        )
        
        # Resolve the escalation
        resolved_escalation = self.workflow_service.resolve_escalation(
            escalation_id=escalation.id,
            resolved_by=self.user.id
        )
        
        # Verify escalation was resolved
        assert resolved_escalation.is_resolved == True
        assert resolved_escalation.resolved_at is not None
        assert resolved_escalation.resolved_by == self.user.id
        
        # Verify no longer appears in escalated applications
        escalated_apps = self.workflow_service.get_escalated_applications(self.job.created_by)
        assert len(escalated_apps) == 0
    
    def test_get_applications_by_stage(self):
        """Test retrieving applications in a specific stage"""
        # Requirements: 1.2 - Application tracking by stage
        
        # Create additional test data
        candidate2 = Candidate(
            email="candidate2.workflow@example.com",
            first_name="Test2",
            last_name="Candidate2"
        )
        self.db.add(candidate2)
        self.db.commit()
        self.db.refresh(candidate2)
        
        application2 = Application(
            candidate_id=candidate2.id,
            job_id=self.job.id,
            status="applied"
        )
        self.db.add(application2)
        self.db.commit()
        self.db.refresh(application2)
        
        # Create workflow stages
        stages = self.workflow_service.create_default_workflow_stages(self.job.id)
        screening_stage = stages[1]
        
        # Advance both applications to screening
        self.workflow_service.advance_application_to_stage(
            application_id=self.application.id,
            stage_id=screening_stage.id,
            user_id=self.user.id
        )
        
        self.workflow_service.advance_application_to_stage(
            application_id=application2.id,
            stage_id=screening_stage.id,
            user_id=self.user.id
        )
        
        # Get applications in screening stage
        screening_apps = self.workflow_service.get_applications_by_stage(
            job_id=self.job.id,
            stage_name="Initial Screening"
        )
        
        assert len(screening_apps) == 2
        app_ids = {app.id for app in screening_apps}
        assert self.application.id in app_ids
        assert application2.id in app_ids
        
        # Advance one application to next stage
        interview_stage = stages[3]
        self.workflow_service.advance_application_to_stage(
            application_id=self.application.id,
            stage_id=interview_stage.id,
            user_id=self.user.id
        )
        
        # Verify only one application remains in screening
        screening_apps = self.workflow_service.get_applications_by_stage(
            job_id=self.job.id,
            stage_name="Initial Screening"
        )
        
        assert len(screening_apps) == 1
        assert screening_apps[0].id == application2.id
        
        # Verify one application is now in interview stage
        interview_apps = self.workflow_service.get_applications_by_stage(
            job_id=self.job.id,
            stage_name="Interview"
        )
        
        assert len(interview_apps) == 1
        assert interview_apps[0].id == self.application.id
    
    def test_get_application_timeline(self):
        """Test retrieving complete application timeline"""
        # Requirements: 1.2 - Application tracking and history
        
        # Create workflow stages
        stages = self.workflow_service.create_default_workflow_stages(self.job.id)
        
        # Advance through multiple stages
        stage_progression = [
            (stages[1], "Moving to screening"),
            (stages[2], "Technical assessment required"),
            (stages[3], "Interview scheduled")
        ]
        
        for stage, notes in stage_progression:
            self.workflow_service.advance_application_to_stage(
                application_id=self.application.id,
                stage_id=stage.id,
                user_id=self.user.id,
                notes=notes
            )
        
        # Get application timeline
        timeline = self.workflow_service.get_application_timeline(self.application.id)
        
        assert len(timeline) == 3
        
        # Verify timeline order and content
        expected_stages = ["Initial Screening", "Technical Assessment", "Interview"]
        expected_notes = ["Moving to screening", "Technical assessment required", "Interview scheduled"]
        
        for i, entry in enumerate(timeline):
            assert entry["stage_name"] == expected_stages[i]
            assert entry["notes"] == expected_notes[i]
            assert entry["entered_at"] is not None
            assert entry["sla_deadline"] is not None
            
            # Only the last entry should have no exit time
            if i < len(timeline) - 1:
                assert entry["exited_at"] is not None
                assert entry["duration_hours"] is not None
                assert entry["duration_hours"] > 0
            else:
                assert entry["exited_at"] is None
                assert entry["duration_hours"] is None
        
        # Verify chronological order
        for i in range(1, len(timeline)):
            assert timeline[i]["entered_at"] >= timeline[i-1]["entered_at"]
    
    def test_workflow_stage_validation(self):
        """Test validation of workflow stage operations"""
        # Requirements: 1.2 - Error handling for invalid operations
        
        # Test advancing to non-existent stage
        with pytest.raises(ValueError, match="Workflow stage .* not found"):
            self.workflow_service.advance_application_to_stage(
                application_id=self.application.id,
                stage_id=uuid4(),  # Non-existent stage ID
                user_id=self.user.id
            )
        
        # Test advancing non-existent application
        stages = self.workflow_service.create_default_workflow_stages(self.job.id)
        
        with pytest.raises(ValueError, match="Application .* not found"):
            self.workflow_service.advance_application_to_stage(
                application_id=uuid4(),  # Non-existent application ID
                stage_id=stages[0].id,
                user_id=self.user.id
            )
    
    def test_multiple_stage_transitions_same_application(self):
        """Test handling multiple rapid stage transitions"""
        # Requirements: 1.2 - Concurrent stage transition handling
        
        stages = self.workflow_service.create_default_workflow_stages(self.job.id)
        
        # Rapidly advance through multiple stages
        for i in range(1, 4):  # Skip first stage (Applied)
            self.workflow_service.advance_application_to_stage(
                application_id=self.application.id,
                stage_id=stages[i].id,
                user_id=self.user.id,
                notes=f"Stage {i} transition"
            )
        
        # Verify only one active transition exists
        current_transition = self.workflow_service.get_current_stage_transition(
            self.application.id
        )
        
        assert current_transition is not None
        assert current_transition.stage_id == stages[3].id  # Interview stage
        
        # Verify all previous transitions were properly closed
        all_transitions = self.db.query(StageTransition).filter(
            StageTransition.application_id == self.application.id
        ).order_by(StageTransition.entered_at).all()
        
        assert len(all_transitions) == 3
        
        # All but the last should be closed
        for i in range(len(all_transitions) - 1):
            assert all_transitions[i].exited_at is not None
        
        # Last should be open
        assert all_transitions[-1].exited_at is None
        assert all_transitions[-1].id == current_transition.id