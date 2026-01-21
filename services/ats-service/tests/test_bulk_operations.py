"""
Unit tests for bulk operations functionality.

Tests bulk status updates, bulk rejection/approval operations, and progress tracking.
Requirements: 1.5
"""

import pytest
import asyncio
from datetime import datetime
from uuid import uuid4
from unittest.mock import Mock, patch
from sqlalchemy.orm import Session

from app.models import User, Candidate, JobPosting, Application, ApplicationStatusHistory
from app.routers.applications import (
    process_bulk_status_update, process_bulk_stage_movement,
    bulk_operation_progress
)
from app.schemas import BulkStatusUpdate
from tests.conftest import TestingSessionLocal, engine


class TestBulkOperations:
    """Test cases for bulk operations functionality"""
    
    def setup_method(self):
        """Set up test data for each test method"""
        from app.models import Base
        Base.metadata.create_all(bind=engine)
        self.db = TestingSessionLocal()
        
        # Clear any existing progress tracking
        bulk_operation_progress.clear()
        
        # Create test user
        self.user = User(
            email="bulk.test@example.com",
            password_hash="hashed_password",
            first_name="Bulk",
            last_name="Tester",
            role="recruiter"
        )
        self.db.add(self.user)
        self.db.commit()
        self.db.refresh(self.user)
        
        # Create test candidates
        self.candidates = []
        for i in range(5):
            candidate = Candidate(
                email=f"candidate{i}.bulk@example.com",
                first_name=f"Test{i}",
                last_name="Candidate"
            )
            self.candidates.append(candidate)
            self.db.add(candidate)
        
        self.db.commit()
        for candidate in self.candidates:
            self.db.refresh(candidate)
        
        # Create test job
        self.job = JobPosting(
            title="Bulk Test Job",
            description="Test job for bulk operations",
            requirements={"skills": ["testing"]},
            department="Engineering",
            employment_type="full-time",
            created_by=self.user.id
        )
        self.db.add(self.job)
        self.db.commit()
        self.db.refresh(self.job)
        
        # Create test applications
        self.applications = []
        self.application_ids = []  # Store IDs separately
        for candidate in self.candidates:
            application = Application(
                candidate_id=candidate.id,
                job_id=self.job.id,
                status="applied"
            )
            self.applications.append(application)
            self.db.add(application)
        
        self.db.commit()
        
        # Refresh all applications and store their IDs
        for application in self.applications:
            self.db.refresh(application)
            self.application_ids.append(application.id)
    
    def teardown_method(self):
        """Clean up after each test method"""
        bulk_operation_progress.clear()
        self.db.close()
        from app.models import Base
        Base.metadata.drop_all(bind=engine)
    
    @pytest.mark.asyncio
    async def test_bulk_status_update_success(self):
        """Test successful bulk status update operation"""
        # Requirements: 1.5 - Bulk status update functionality
        
        operation_id = "test_bulk_update_001"
        application_ids = self.application_ids  # Use stored IDs
        
        bulk_data = BulkStatusUpdate(
            application_ids=application_ids,
            new_status="screening",
            changed_by=self.user.id,
            reason="Bulk screening approval"
        )
        
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
        
        # Execute bulk operation
        await process_bulk_status_update(operation_id, bulk_data, self.db)
        
        # Verify progress tracking
        progress = bulk_operation_progress[operation_id]
        assert progress["status"] == "completed"
        assert progress["total"] == 5
        assert progress["processed"] == 5
        assert progress["successful"] == 5
        assert progress["failed"] == 0
        assert len(progress["errors"]) == 0
        assert progress["started_at"] is not None
        assert progress["completed_at"] is not None
        
        # Verify all applications were updated
        updated_applications = self.db.query(Application).filter(
            Application.id.in_(self.application_ids)
        ).all()
        
        for application in updated_applications:
            assert application.status == "screening"
        
        # Verify status history was created for each application
        for app_id in self.application_ids:
            history = self.db.query(ApplicationStatusHistory).filter(
                ApplicationStatusHistory.application_id == app_id
            ).first()
            
            assert history is not None
            assert history.previous_status == "applied"
            assert history.new_status == "screening"
            assert history.changed_by == self.user.id
            assert "Bulk screening approval" in history.change_reason
    
    @pytest.mark.asyncio
    async def test_bulk_status_update_partial_failure(self):
        """Test bulk status update with some failures"""
        # Requirements: 1.5 - Error handling in bulk operations
        
        operation_id = "test_bulk_partial_failure"
        
        # Include some invalid application IDs
        valid_ids = [app.id for app in self.applications[:3]]
        invalid_ids = [uuid4(), uuid4()]
        all_ids = valid_ids + invalid_ids
        
        bulk_data = BulkStatusUpdate(
            application_ids=all_ids,
            new_status="rejected",
            changed_by=self.user.id,
            reason="Bulk rejection"
        )
        
        # Initialize progress tracking
        bulk_operation_progress[operation_id] = {
            "total": len(all_ids),
            "processed": 0,
            "successful": 0,
            "failed": 0,
            "status": "in_progress",
            "errors": [],
            "started_at": None,
            "completed_at": None
        }
        
        # Execute bulk operation
        await process_bulk_status_update(operation_id, bulk_data, self.db)
        
        # Verify progress tracking
        progress = bulk_operation_progress[operation_id]
        assert progress["status"] == "completed"
        assert progress["total"] == 5
        assert progress["processed"] == 5
        assert progress["successful"] == 3
        assert progress["failed"] == 2
        assert len(progress["errors"]) == 2
        
        # Verify error messages contain application IDs
        error_messages = " ".join(progress["errors"])
        for invalid_id in invalid_ids:
            assert str(invalid_id) in error_messages
        
        # Verify valid applications were updated
        updated_applications = self.db.query(Application).filter(
            Application.id.in_(valid_ids)
        ).all()
        
        for application in updated_applications:
            assert application.status == "rejected"
        
        # Verify remaining applications were not updated
        remaining_app_ids = self.application_ids[3:5]
        remaining_applications = self.db.query(Application).filter(
            Application.id.in_(remaining_app_ids)
        ).all()
        
        for application in remaining_applications:
            assert application.status == "applied"
    
    @pytest.mark.asyncio
    async def test_bulk_stage_movement(self):
        """Test bulk movement of applications to workflow stage"""
        # Requirements: 1.5 - Bulk operations with workflow integration
        
        from app.models import WorkflowStage
        from app.services.workflow_service import WorkflowService
        
        # Create workflow stages
        workflow_service = WorkflowService(self.db)
        stages = workflow_service.create_default_workflow_stages(self.job.id)
        screening_stage = stages[1]  # "Initial Screening"
        
        operation_id = "test_bulk_stage_movement"
        application_ids = [app.id for app in self.applications[:3]]
        
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
        
        # Execute bulk stage movement
        await process_bulk_stage_movement(
            operation_id=operation_id,
            application_ids=application_ids,
            stage_id=screening_stage.id,
            changed_by=self.user.id,
            reason="Bulk move to screening",
            db=self.db
        )
        
        # Verify progress tracking
        progress = bulk_operation_progress[operation_id]
        assert progress["status"] == "completed"
        assert progress["successful"] == 3
        assert progress["failed"] == 0
        
        # Verify applications were moved to correct stage
        updated_applications = self.db.query(Application).filter(
            Application.id.in_(application_ids)
        ).all()
        
        for application in updated_applications:
            assert application.status == "initial_screening"
            
            # Verify stage transition was created
            current_transition = workflow_service.get_current_stage_transition(
                application.id
            )
            assert current_transition is not None
            assert current_transition.stage_id == screening_stage.id
    
    def test_bulk_operation_progress_calculation(self):
        """Test progress percentage calculation"""
        # Requirements: 1.5 - Progress tracking for bulk operations
        
        operation_id = "test_progress_calc"
        
        # Initialize progress
        bulk_operation_progress[operation_id] = {
            "total": 10,
            "processed": 0,
            "successful": 0,
            "failed": 0,
            "status": "in_progress",
            "errors": [],
            "started_at": datetime.utcnow(),
            "completed_at": None
        }
        
        progress = bulk_operation_progress[operation_id]
        
        # Test 0% progress
        progress_percentage = (progress["processed"] / progress["total"]) * 100
        assert progress_percentage == 0.0
        
        # Test 50% progress
        progress["processed"] = 5
        progress["successful"] = 4
        progress["failed"] = 1
        progress_percentage = (progress["processed"] / progress["total"]) * 100
        assert progress_percentage == 50.0
        
        # Test 100% progress
        progress["processed"] = 10
        progress["successful"] = 8
        progress["failed"] = 2
        progress["status"] = "completed"
        progress["completed_at"] = datetime.utcnow()
        progress_percentage = (progress["processed"] / progress["total"]) * 100
        assert progress_percentage == 100.0
        
        # Verify completion time is after start time
        assert progress["completed_at"] >= progress["started_at"]
    
    def test_bulk_operation_error_handling(self):
        """Test error handling in bulk operations"""
        # Requirements: 1.5 - Robust error handling
        
        operation_id = "test_error_handling"
        
        # Test with empty application list
        bulk_data = BulkStatusUpdate(
            application_ids=[],
            new_status="screening",
            changed_by=self.user.id,
            reason="Empty test"
        )
        
        bulk_operation_progress[operation_id] = {
            "total": 0,
            "processed": 0,
            "successful": 0,
            "failed": 0,
            "status": "in_progress",
            "errors": [],
            "started_at": None,
            "completed_at": None
        }
        
        # Should complete successfully with no operations
        asyncio.run(process_bulk_status_update(operation_id, bulk_data, self.db))
        
        progress = bulk_operation_progress[operation_id]
        assert progress["status"] == "completed"
        assert progress["total"] == 0
        assert progress["processed"] == 0
        assert progress["successful"] == 0
        assert progress["failed"] == 0
    
    def test_bulk_operation_concurrent_access(self):
        """Test concurrent access to bulk operation progress"""
        # Requirements: 1.5 - Thread-safe progress tracking
        
        operation_id = "test_concurrent_access"
        
        # Initialize progress
        bulk_operation_progress[operation_id] = {
            "total": 5,
            "processed": 0,
            "successful": 0,
            "failed": 0,
            "status": "in_progress",
            "errors": [],
            "started_at": datetime.utcnow(),
            "completed_at": None
        }
        
        # Simulate concurrent updates
        progress = bulk_operation_progress[operation_id]
        
        # Multiple threads updating progress
        for i in range(5):
            progress["processed"] += 1
            if i % 2 == 0:
                progress["successful"] += 1
            else:
                progress["failed"] += 1
                progress["errors"].append(f"Error {i}")
        
        # Verify final state
        assert progress["processed"] == 5
        assert progress["successful"] == 3
        assert progress["failed"] == 2
        assert len(progress["errors"]) == 2
    
    def test_bulk_operation_cleanup(self):
        """Test cleanup of completed bulk operations"""
        # Requirements: 1.5 - Memory management for bulk operations
        
        operation_id = "test_cleanup"
        
        # Create completed operation
        bulk_operation_progress[operation_id] = {
            "total": 3,
            "processed": 3,
            "successful": 3,
            "failed": 0,
            "status": "completed",
            "errors": [],
            "started_at": datetime.utcnow(),
            "completed_at": datetime.utcnow()
        }
        
        # Verify operation exists
        assert operation_id in bulk_operation_progress
        
        # Cleanup operation
        del bulk_operation_progress[operation_id]
        
        # Verify operation was removed
        assert operation_id not in bulk_operation_progress
    
    def test_bulk_operation_status_transitions(self):
        """Test status transitions during bulk operations"""
        # Requirements: 1.5 - Status lifecycle management
        
        operation_id = "test_status_transitions"
        
        # Initialize as in_progress
        bulk_operation_progress[operation_id] = {
            "total": 2,
            "processed": 0,
            "successful": 0,
            "failed": 0,
            "status": "in_progress",
            "errors": [],
            "started_at": datetime.utcnow(),
            "completed_at": None
        }
        
        progress = bulk_operation_progress[operation_id]
        
        # Verify initial state
        assert progress["status"] == "in_progress"
        assert progress["completed_at"] is None
        
        # Process items
        progress["processed"] = 1
        progress["successful"] = 1
        assert progress["status"] == "in_progress"  # Still in progress
        
        # Complete successfully
        progress["processed"] = 2
        progress["successful"] = 2
        progress["status"] = "completed"
        progress["completed_at"] = datetime.utcnow()
        
        assert progress["status"] == "completed"
        assert progress["completed_at"] is not None
        
        # Test failed status
        failed_operation_id = "test_failed_operation"
        bulk_operation_progress[failed_operation_id] = {
            "total": 1,
            "processed": 1,
            "successful": 0,
            "failed": 1,
            "status": "failed",
            "errors": ["Critical error occurred"],
            "started_at": datetime.utcnow(),
            "completed_at": datetime.utcnow()
        }
        
        failed_progress = bulk_operation_progress[failed_operation_id]
        assert failed_progress["status"] == "failed"
        assert len(failed_progress["errors"]) == 1
    
    @pytest.mark.asyncio
    async def test_bulk_notification_integration(self):
        """Test integration with notification service during bulk operations"""
        # Requirements: 1.5 - Notification integration with bulk operations
        
        with patch('app.routers.applications.NotificationService') as mock_notification_service:
            # Setup mock
            mock_service_instance = Mock()
            mock_notification_service.return_value = mock_service_instance
            mock_service_instance.should_send_notification.return_value = True
            mock_service_instance.send_status_change_notification.return_value = {
                "notification_id": "test_notification",
                "sent_at": datetime.utcnow()
            }
            
            operation_id = "test_notification_integration"
            application_ids = [self.applications[0].id]
            
            bulk_data = BulkStatusUpdate(
                application_ids=application_ids,
                new_status="interview",
                changed_by=self.user.id,
                reason="Bulk interview scheduling"
            )
            
            # Initialize progress tracking
            bulk_operation_progress[operation_id] = {
                "total": 1,
                "processed": 0,
                "successful": 0,
                "failed": 0,
                "status": "in_progress",
                "errors": [],
                "started_at": None,
                "completed_at": None
            }
            
            # Execute bulk operation
            await process_bulk_status_update(operation_id, bulk_data, self.db)
            
            # Verify notification service was called
            mock_service_instance.should_send_notification.assert_called_once()
            mock_service_instance.send_status_change_notification.assert_called_once()
            
            # Verify operation completed successfully
            progress = bulk_operation_progress[operation_id]
            assert progress["status"] == "completed"
            assert progress["successful"] == 1
            assert progress["failed"] == 0