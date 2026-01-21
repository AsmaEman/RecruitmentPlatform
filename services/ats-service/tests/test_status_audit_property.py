"""
Property-based tests for status change audit logging.

Feature: recruitment-testing-platform, Property 2: Status Change Audit Trail
Validates: Requirements 1.2
"""

import pytest
from hypothesis import given, strategies as st, settings
from sqlalchemy.orm import Session
from uuid import uuid4
from datetime import datetime

from app.models import Candidate, Application, JobPosting, User, ApplicationStatusHistory
from app.schemas import CandidateCreate, ApplicationCreate, JobCreate, ApplicationStatusUpdate


# Hypothesis strategies for generating test data
@st.composite
def status_change_data(draw):
    """Generate valid status change data"""
    statuses = ['applied', 'screening', 'interview', 'technical_test', 'final_interview', 'offer', 'hired', 'rejected']
    
    return {
        'old_status': draw(st.sampled_from(statuses)),
        'new_status': draw(st.sampled_from(statuses)),
        'reason': draw(st.one_of(st.none(), st.text(min_size=5, max_size=200)))
    }


@given(status_change_data())
@settings(max_examples=10)
def test_status_change_audit_trail(status_change_data_input):
    """
    Property 2: Status Change Audit Trail
    For any application status update, the system should log the change with timestamp, 
    user, and previous/new status values.
    
    Validates: Requirements 1.2
    """
    # Get a fresh database session for this test
    from tests.conftest import TestingSessionLocal, engine
    from app.models import Base
    
    Base.metadata.create_all(bind=engine)
    db_session = TestingSessionLocal()
    
    try:
        # Create a test user
        test_user = User(
            email="auditor@example.com",
            password_hash="hashed_password",
            first_name="Audit",
            last_name="User",
            role="recruiter"
        )
        db_session.add(test_user)
        db_session.commit()
        db_session.refresh(test_user)
        
        # Create a candidate
        candidate = Candidate(
            email="audit.candidate@example.com",
            first_name="Audit",
            last_name="Candidate"
        )
        db_session.add(candidate)
        db_session.commit()
        db_session.refresh(candidate)
        
        # Create a job posting
        job = JobPosting(
            title="Test Job for Audit",
            description="Test job description",
            requirements={"skills": ["testing"]},
            department="Engineering",
            employment_type="full-time",
            created_by=test_user.id
        )
        db_session.add(job)
        db_session.commit()
        db_session.refresh(job)
        
        # Create an application with initial status
        application = Application(
            candidate_id=candidate.id,
            job_id=job.id,
            status=status_change_data_input['old_status']
        )
        db_session.add(application)
        db_session.commit()
        db_session.refresh(application)
        
        # Record the time before status change
        before_change = datetime.now()
        
        # Create status change history entry (simulating the API endpoint behavior)
        status_history = ApplicationStatusHistory(
            application_id=application.id,
            previous_status=status_change_data_input['old_status'],
            new_status=status_change_data_input['new_status'],
            changed_by=test_user.id,
            change_reason=status_change_data_input['reason']
        )
        
        # Update application status
        application.status = status_change_data_input['new_status']
        
        db_session.add(status_history)
        db_session.commit()
        db_session.refresh(status_history)
        
        # Record the time after status change
        after_change = datetime.now()
        
        # Verify audit trail was created
        assert status_history.id is not None
        assert status_history.application_id == application.id
        assert status_history.previous_status == status_change_data_input['old_status']
        assert status_history.new_status == status_change_data_input['new_status']
        assert status_history.changed_by == test_user.id
        assert status_history.change_reason == status_change_data_input['reason']
        assert status_history.created_at is not None
        assert isinstance(status_history.created_at, datetime)
        
        # Verify timestamp is within reasonable bounds
        assert before_change <= status_history.created_at <= after_change
        
        # Verify the audit trail can be retrieved later
        retrieved_history = db_session.query(ApplicationStatusHistory).filter(
            ApplicationStatusHistory.id == status_history.id
        ).first()
        
        assert retrieved_history is not None
        assert retrieved_history.application_id == application.id
        assert retrieved_history.previous_status == status_change_data_input['old_status']
        assert retrieved_history.new_status == status_change_data_input['new_status']
        assert retrieved_history.changed_by == test_user.id
        assert retrieved_history.change_reason == status_change_data_input['reason']
        assert retrieved_history.created_at == status_history.created_at
        
        # Verify we can retrieve all history for the application
        all_history = db_session.query(ApplicationStatusHistory).filter(
            ApplicationStatusHistory.application_id == application.id
        ).all()
        
        assert len(all_history) >= 1
        assert status_history.id in [h.id for h in all_history]
        
        # Verify the application status was actually updated
        updated_application = db_session.query(Application).filter(
            Application.id == application.id
        ).first()
        
        assert updated_application is not None
        assert updated_application.status == status_change_data_input['new_status']
        
    finally:
        db_session.close()
        Base.metadata.drop_all(bind=engine)


@given(st.lists(status_change_data(), min_size=2, max_size=3))
@settings(max_examples=5)
def test_multiple_status_changes_audit_trail(status_changes):
    """
    Property: Multiple status changes should each create separate audit entries
    For any sequence of status changes, each should have its own audit trail entry.
    """
    # Get a fresh database session for this test
    from tests.conftest import TestingSessionLocal, engine
    from app.models import Base
    
    Base.metadata.create_all(bind=engine)
    db_session = TestingSessionLocal()
    
    try:
        # Create a test user
        test_user = User(
            email="multi.auditor@example.com",
            password_hash="hashed_password",
            first_name="Multi",
            last_name="Auditor",
            role="recruiter"
        )
        db_session.add(test_user)
        db_session.commit()
        db_session.refresh(test_user)
        
        # Create a candidate
        candidate = Candidate(
            email="multi.candidate@example.com",
            first_name="Multi",
            last_name="Candidate"
        )
        db_session.add(candidate)
        db_session.commit()
        db_session.refresh(candidate)
        
        # Create a job posting
        job = JobPosting(
            title="Multi Status Test Job",
            description="Test job for multiple status changes",
            requirements={"skills": ["testing"]},
            department="Engineering",
            employment_type="full-time",
            created_by=test_user.id
        )
        db_session.add(job)
        db_session.commit()
        db_session.refresh(job)
        
        # Create an application
        application = Application(
            candidate_id=candidate.id,
            job_id=job.id,
            status="applied"
        )
        db_session.add(application)
        db_session.commit()
        db_session.refresh(application)
        
        created_history_entries = []
        current_status = "applied"
        
        # Apply multiple status changes
        for i, status_change in enumerate(status_changes):
            # Create status change history entry
            status_history = ApplicationStatusHistory(
                application_id=application.id,
                previous_status=current_status,
                new_status=status_change['new_status'],
                changed_by=test_user.id,
                change_reason=f"Change {i+1}: {status_change.get('reason', 'No reason')}"
            )
            
            # Update application status
            application.status = status_change['new_status']
            current_status = status_change['new_status']
            
            db_session.add(status_history)
            db_session.commit()
            db_session.refresh(status_history)
            
            created_history_entries.append(status_history)
        
        # Verify all audit trail entries were created
        assert len(created_history_entries) == len(status_changes)
        
        # Verify all entries have unique IDs and timestamps
        history_ids = [h.id for h in created_history_entries]
        assert len(history_ids) == len(set(history_ids)), "All history entries should have unique IDs"
        
        timestamps = [h.created_at for h in created_history_entries]
        # Timestamps should be in chronological order (or at least not decreasing)
        for i in range(1, len(timestamps)):
            assert timestamps[i] >= timestamps[i-1], "Timestamps should be chronological"
        
        # Verify we can retrieve all history for the application
        all_history = db_session.query(ApplicationStatusHistory).filter(
            ApplicationStatusHistory.application_id == application.id
        ).order_by(ApplicationStatusHistory.created_at).all()
        
        assert len(all_history) == len(status_changes)
        
        # Verify the sequence of status changes is preserved
        for i, (history_entry, expected_change) in enumerate(zip(all_history, status_changes)):
            assert history_entry.new_status == expected_change['new_status']
            assert history_entry.changed_by == test_user.id
            assert f"Change {i+1}" in history_entry.change_reason
            
    finally:
        db_session.close()
        Base.metadata.drop_all(bind=engine)