"""
Property-based tests for automated status change notifications.

Feature: recruitment-testing-platform, Property 21: Status Change Notifications
Validates: Requirements 8.1
"""

import pytest
from hypothesis import given, strategies as st, settings
from sqlalchemy.orm import Session
from uuid import uuid4
from datetime import datetime, timedelta

from app.models import Candidate, Application, JobPosting, User, ApplicationStatusHistory
from app.services.notification_service import NotificationService


# Hypothesis strategies for generating test data
@st.composite
def notification_status_change_data(draw):
    """Generate valid status change data that should trigger notifications"""
    notification_statuses = ['screening', 'interview', 'technical_test', 'final_interview', 'offer', 'hired', 'rejected']
    non_notification_statuses = ['applied', 'withdrawn']
    
    return {
        'old_status': draw(st.sampled_from(['applied', 'screening', 'interview'])),
        'new_status': draw(st.sampled_from(notification_statuses + non_notification_statuses)),
        'reason': draw(st.one_of(st.none(), st.text(min_size=5, max_size=200))),
        'should_notify': draw(st.sampled_from(notification_statuses))
    }


@given(notification_status_change_data())
@settings(max_examples=10, deadline=1000)  # Increase deadline to 1 second
def test_status_change_notifications_property(status_change_data):
    """
    Property 21: Status Change Notifications
    For any application status change, the system should send appropriate email 
    notifications to all relevant stakeholders within 5 minutes.
    
    Validates: Requirements 8.1
    """
    # Get a fresh database session for this test
    from tests.conftest import TestingSessionLocal, engine
    from app.models import Base
    
    Base.metadata.create_all(bind=engine)
    db_session = TestingSessionLocal()
    
    try:
        # Create a test hiring manager
        hiring_manager = User(
            email="hiring.manager@example.com",
            password_hash="hashed_password",
            first_name="Hiring",
            last_name="Manager",
            role="hiring_manager"
        )
        db_session.add(hiring_manager)
        db_session.commit()
        db_session.refresh(hiring_manager)
        
        # Create a test recruiter
        recruiter = User(
            email="recruiter@example.com",
            password_hash="hashed_password",
            first_name="Test",
            last_name="Recruiter",
            role="recruiter"
        )
        db_session.add(recruiter)
        db_session.commit()
        db_session.refresh(recruiter)
        
        # Create a candidate
        candidate = Candidate(
            email="candidate@example.com",
            first_name="Test",
            last_name="Candidate"
        )
        db_session.add(candidate)
        db_session.commit()
        db_session.refresh(candidate)
        
        # Create a job posting
        job = JobPosting(
            title="Software Engineer",
            description="Test job description",
            requirements={"skills": ["Python", "FastAPI"]},
            department="Engineering",
            employment_type="full-time",
            created_by=hiring_manager.id
        )
        db_session.add(job)
        db_session.commit()
        db_session.refresh(job)
        
        # Create an application with initial status
        application = Application(
            candidate_id=candidate.id,
            job_id=job.id,
            status=status_change_data['old_status']
        )
        db_session.add(application)
        db_session.commit()
        db_session.refresh(application)
        
        # Initialize notification service
        notification_service = NotificationService(db_session)
        notification_service.clear_notifications()
        
        # Record the time before status change
        before_change = datetime.utcnow()
        
        # Create status change history entry
        status_history = ApplicationStatusHistory(
            application_id=application.id,
            previous_status=status_change_data['old_status'],
            new_status=status_change_data['new_status'],
            changed_by=recruiter.id,
            change_reason=status_change_data['reason']
        )
        
        # Update application status
        application.status = status_change_data['new_status']
        
        db_session.add(status_history)
        db_session.commit()
        db_session.refresh(status_history)
        
        # Send notification (this simulates the automatic notification trigger)
        if notification_service.should_send_notification(status_history):
            notification_data = notification_service.send_status_change_notification(
                application.id, status_history
            )
            
            # Record the time after notification
            after_notification = datetime.utcnow()
            
            # Verify notification was sent within 5 minutes (property requirement)
            time_diff = (after_notification - before_change).total_seconds()
            assert time_diff <= 300, f"Notification should be sent within 5 minutes, took {time_diff} seconds"
            
            # Verify notification contains required information
            assert notification_data["application_id"] == application.id
            assert notification_data["candidate_email"] == candidate.email
            assert notification_data["candidate_name"] == f"{candidate.first_name} {candidate.last_name}"
            assert notification_data["job_title"] == job.title
            assert notification_data["previous_status"] == status_change_data['old_status']
            assert notification_data["new_status"] == status_change_data['new_status']
            assert notification_data["change_reason"] == status_change_data['reason']
            assert notification_data["timestamp"] == status_history.created_at
            assert notification_data["sent_at"] is not None
            
            # Verify recipients are included
            assert "recipients" in notification_data
            assert len(notification_data["recipients"]) >= 1
            
            # Verify candidate is always notified
            candidate_recipients = [r for r in notification_data["recipients"] if r["type"] == "candidate"]
            assert len(candidate_recipients) == 1
            assert candidate_recipients[0]["email"] == candidate.email
            assert candidate_recipients[0]["name"] == f"{candidate.first_name} {candidate.last_name}"
            
            # Verify hiring manager is notified for important status changes
            important_statuses = ['interview', 'offer', 'hired', 'rejected']
            if status_change_data['new_status'] in important_statuses:
                hm_recipients = [r for r in notification_data["recipients"] if r["type"] == "hiring_manager"]
                assert len(hm_recipients) == 1
                assert hm_recipients[0]["email"] == hiring_manager.email
                assert hm_recipients[0]["name"] == f"{hiring_manager.first_name} {hiring_manager.last_name}"
            
            # Verify notification can be retrieved later
            sent_notifications = notification_service.get_sent_notifications()
            assert len(sent_notifications) == 1
            assert sent_notifications[0]["notification_id"] == notification_data["notification_id"]
            
            # Verify application-specific notifications can be retrieved
            app_notifications = notification_service.get_notifications_for_application(application.id)
            assert len(app_notifications) == 1
            assert app_notifications[0]["application_id"] == application.id
            
        else:
            # If notification should not be sent, verify none was sent
            sent_notifications = notification_service.get_sent_notifications()
            assert len(sent_notifications) == 0
            
    finally:
        db_session.close()
        Base.metadata.drop_all(bind=engine)


@given(st.lists(notification_status_change_data(), min_size=2, max_size=4))
@settings(max_examples=5, deadline=2000)  # Increase deadline to 2 seconds
def test_multiple_status_changes_notifications_property(status_changes):
    """
    Property: Multiple status changes should each trigger appropriate notifications
    For any sequence of status changes, each change that requires notification 
    should generate exactly one notification.
    """
    # Get a fresh database session for this test
    from tests.conftest import TestingSessionLocal, engine
    from app.models import Base
    
    Base.metadata.create_all(bind=engine)
    db_session = TestingSessionLocal()
    
    try:
        # Create test users
        hiring_manager = User(
            email="multi.hiring.manager@example.com",
            password_hash="hashed_password",
            first_name="Multi",
            last_name="Manager",
            role="hiring_manager"
        )
        db_session.add(hiring_manager)
        
        recruiter = User(
            email="multi.recruiter@example.com",
            password_hash="hashed_password",
            first_name="Multi",
            last_name="Recruiter",
            role="recruiter"
        )
        db_session.add(recruiter)
        db_session.commit()
        db_session.refresh(hiring_manager)
        db_session.refresh(recruiter)
        
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
            created_by=hiring_manager.id
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
        
        # Initialize notification service
        notification_service = NotificationService(db_session)
        notification_service.clear_notifications()
        
        current_status = "applied"
        expected_notification_count = 0
        
        # Apply multiple status changes
        for i, status_change in enumerate(status_changes):
            # Create status change history entry
            status_history = ApplicationStatusHistory(
                application_id=application.id,
                previous_status=current_status,
                new_status=status_change['new_status'],
                changed_by=recruiter.id,
                change_reason=f"Multi change {i+1}: {status_change.get('reason', 'No reason')}"
            )
            
            # Update application status
            application.status = status_change['new_status']
            current_status = status_change['new_status']
            
            db_session.add(status_history)
            db_session.commit()
            db_session.refresh(status_history)
            
            # Send notification if required
            if notification_service.should_send_notification(status_history):
                notification_service.send_status_change_notification(
                    application.id, status_history
                )
                expected_notification_count += 1
        
        # Verify correct number of notifications were sent
        sent_notifications = notification_service.get_sent_notifications()
        assert len(sent_notifications) == expected_notification_count
        
        # Verify all notifications are for the same application
        for notification in sent_notifications:
            assert notification["application_id"] == application.id
            assert notification["candidate_email"] == candidate.email
            assert notification["job_title"] == job.title
        
        # Verify notifications have unique IDs
        notification_ids = [n["notification_id"] for n in sent_notifications]
        assert len(notification_ids) == len(set(notification_ids)), "All notifications should have unique IDs"
        
        # Verify notifications are sent in chronological order
        timestamps = [n["sent_at"] for n in sent_notifications]
        for i in range(1, len(timestamps)):
            assert timestamps[i] >= timestamps[i-1], "Notifications should be sent in chronological order"
        
        # Verify application-specific retrieval works
        app_notifications = notification_service.get_notifications_for_application(application.id)
        assert len(app_notifications) == expected_notification_count
        
    finally:
        db_session.close()
        Base.metadata.drop_all(bind=engine)


@given(st.text(min_size=1, max_size=50))
@settings(max_examples=5, deadline=1000)  # Increase deadline to 1 second
def test_notification_template_consistency_property(job_title):
    """
    Property: Notification templates should be consistent and contain required variables
    For any job title, notification templates should contain all required placeholder variables.
    """
    # Get a fresh database session for this test
    from tests.conftest import TestingSessionLocal, engine
    from app.models import Base
    
    Base.metadata.create_all(bind=engine)
    db_session = TestingSessionLocal()
    
    try:
        notification_service = NotificationService(db_session)
        
        # Test different status and recipient combinations
        test_cases = [
            ("screening", "candidate"),
            ("interview", "candidate"),
            ("interview", "hiring_manager"),
            ("offer", "candidate"),
            ("offer", "hiring_manager"),
            ("rejected", "candidate")
        ]
        
        for status, recipient_type in test_cases:
            template = notification_service.get_notification_template(status, recipient_type)
            
            # Verify template has required fields
            assert "subject" in template
            assert "body" in template
            assert isinstance(template["subject"], str)
            assert isinstance(template["body"], str)
            assert len(template["subject"]) > 0
            assert len(template["body"]) > 0
            
            # Verify templates contain expected placeholder variables
            expected_variables = ["{job_title}", "{candidate_name}"]
            
            for var in expected_variables:
                # At least one of subject or body should contain the variable
                assert (var in template["subject"] or var in template["body"]), \
                    f"Template for {status}/{recipient_type} should contain {var}"
        
    finally:
        db_session.close()
        Base.metadata.drop_all(bind=engine)