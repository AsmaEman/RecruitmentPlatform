"""
Property-based tests for candidate data persistence.

Feature: recruitment-testing-platform, Property 1: Application Storage Consistency
Validates: Requirements 1.1
"""

import pytest
from hypothesis import given, strategies as st, settings
from sqlalchemy.orm import Session
from uuid import uuid4
from datetime import datetime

from app.models import Candidate, Application, JobPosting, User
from app.schemas import CandidateCreate, ApplicationCreate, JobCreate


# Hypothesis strategies for generating test data
@st.composite
def candidate_data(draw):
    """Generate valid candidate data"""
    first_name = draw(st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll'))))
    last_name = draw(st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll'))))
    email = f"{first_name.lower()}.{last_name.lower()}@{draw(st.sampled_from(['example.com', 'test.org', 'demo.net']))}"
    
    return CandidateCreate(
        email=email,
        first_name=first_name,
        last_name=last_name,
        phone=draw(st.one_of(st.none(), st.text(min_size=10, max_size=15, alphabet=st.characters(whitelist_categories=('Nd',))))),
        location=draw(st.one_of(st.none(), st.text(min_size=5, max_size=100))),
        resume_url=draw(st.one_of(st.none(), st.text(min_size=10, max_size=200))),
        parsed_resume=draw(st.one_of(st.none(), st.dictionaries(st.text(min_size=1, max_size=20), st.text(min_size=1, max_size=100))))
    )


@st.composite
def job_data(draw, user_id):
    """Generate valid job posting data"""
    return JobCreate(
        title=draw(st.text(min_size=5, max_size=100)),
        description=draw(st.text(min_size=10, max_size=500)),
        requirements={"skills": draw(st.lists(st.text(min_size=2, max_size=30), min_size=1, max_size=10))},
        department=draw(st.sampled_from(['Engineering', 'Marketing', 'Sales', 'HR', 'Finance'])),
        location=draw(st.one_of(st.none(), st.text(min_size=5, max_size=100))),
        employment_type=draw(st.sampled_from(['full-time', 'part-time', 'contract', 'internship'])),
        salary_range=draw(st.one_of(st.none(), st.dictionaries(st.text(min_size=1, max_size=20), st.integers(min_value=30000, max_value=200000)))),
        created_by=user_id
    )


@given(candidate_data())
@settings(max_examples=100)
def test_application_storage_consistency(candidate_data_input):
    """
    Property 1: Application Storage Consistency
    For any candidate application submission, the system should store the application 
    with a unique identifier and timestamp that can be retrieved later.
    
    Validates: Requirements 1.1
    """
    # Get a fresh database session for this test
    from tests.conftest import TestingSessionLocal, engine
    from app.models import Base
    
    Base.metadata.create_all(bind=engine)
    db_session = TestingSessionLocal()
    
    try:
        # Create a test user first
        test_user = User(
            email="test@example.com",
            password_hash="hashed_password",
            first_name="Test",
            last_name="User",
            role="recruiter"
        )
        db_session.add(test_user)
        db_session.commit()
        db_session.refresh(test_user)
        
        # Create a candidate
        candidate = Candidate(**candidate_data_input.dict())
        db_session.add(candidate)
        db_session.commit()
        db_session.refresh(candidate)
        
        # Verify candidate was stored with unique identifier and timestamp
        assert candidate.id is not None
        assert candidate.created_at is not None
        assert isinstance(candidate.created_at, datetime)
        
        # Create a job posting
        job_data_input = job_data(user_id=test_user.id).example()
        job = JobPosting(**job_data_input.dict())
        db_session.add(job)
        db_session.commit()
        db_session.refresh(job)
        
        # Create an application
        application_data = ApplicationCreate(
            candidate_id=candidate.id,
            job_id=job.id
        )
        application = Application(**application_data.dict())
        db_session.add(application)
        db_session.commit()
        db_session.refresh(application)
        
        # Verify application was stored with unique identifier and timestamp
        assert application.id is not None
        assert application.applied_at is not None
        assert isinstance(application.applied_at, datetime)
        
        # Verify the application can be retrieved later
        retrieved_application = db_session.query(Application).filter(
            Application.id == application.id
        ).first()
        
        assert retrieved_application is not None
        assert retrieved_application.id == application.id
        assert retrieved_application.candidate_id == candidate.id
        assert retrieved_application.job_id == job.id
        assert retrieved_application.applied_at == application.applied_at
        
        # Verify the candidate can be retrieved through the application
        retrieved_candidate = db_session.query(Candidate).filter(
            Candidate.id == retrieved_application.candidate_id
        ).first()
        
        assert retrieved_candidate is not None
        assert retrieved_candidate.id == candidate.id
        assert retrieved_candidate.email == candidate.email
        assert retrieved_candidate.first_name == candidate.first_name
        assert retrieved_candidate.last_name == candidate.last_name
        
        # Verify data consistency - all original data should be preserved
        assert retrieved_candidate.phone == candidate.phone
        assert retrieved_candidate.location == candidate.location
        assert retrieved_candidate.resume_url == candidate.resume_url
        assert retrieved_candidate.parsed_resume == candidate.parsed_resume
        assert retrieved_candidate.status == candidate.status
        assert retrieved_candidate.created_at == candidate.created_at
        
    finally:
        db_session.close()
        Base.metadata.drop_all(bind=engine)


@given(st.lists(candidate_data(), min_size=2, max_size=10))
@settings(max_examples=50)
def test_multiple_applications_unique_identifiers(candidates_data):
    """
    Property: Multiple applications should each have unique identifiers
    For any set of candidate applications, each should have a unique identifier.
    """
    # Get a fresh database session for this test
    from tests.conftest import TestingSessionLocal, engine
    from app.models import Base
    
    Base.metadata.create_all(bind=engine)
    db_session = TestingSessionLocal()
    
    try:
        # Create a test user
        test_user = User(
            email="test@example.com",
            password_hash="hashed_password",
            first_name="Test",
            last_name="User",
            role="recruiter"
        )
        db_session.add(test_user)
        db_session.commit()
        db_session.refresh(test_user)
        
        # Create a job posting
        job_data_input = job_data(user_id=test_user.id).example()
        job = JobPosting(**job_data_input.dict())
        db_session.add(job)
        db_session.commit()
        db_session.refresh(job)
        
        created_applications = []
        
        # Create multiple candidates and applications
        for i, candidate_data_input in enumerate(candidates_data):
            # Make email unique to avoid conflicts
            candidate_data_input.email = f"candidate{i}@example.com"
            
            candidate = Candidate(**candidate_data_input.dict())
            db_session.add(candidate)
            db_session.commit()
            db_session.refresh(candidate)
            
            application = Application(
                candidate_id=candidate.id,
                job_id=job.id
            )
            db_session.add(application)
            db_session.commit()
            db_session.refresh(application)
            
            created_applications.append(application)
        
        # Verify all applications have unique identifiers
        application_ids = [app.id for app in created_applications]
        assert len(application_ids) == len(set(application_ids)), "All application IDs should be unique"
        
        # Verify all applications can be retrieved
        for application in created_applications:
            retrieved = db_session.query(Application).filter(
                Application.id == application.id
            ).first()
            assert retrieved is not None
            assert retrieved.id == application.id
            
    finally:
        db_session.close()
        Base.metadata.drop_all(bind=engine)