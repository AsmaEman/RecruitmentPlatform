from sqlalchemy import Column, String, DateTime, Boolean, Integer, Text, DECIMAL, ForeignKey, ARRAY
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    role = Column(String(50), nullable=False, default="recruiter")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class Candidate(Base):
    __tablename__ = "candidates"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    phone = Column(String(20))
    location = Column(String)  # Will be handled as geography in PostgreSQL
    resume_url = Column(Text)
    parsed_resume = Column(JSONB)
    status = Column(String(50), default="active", index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    applications = relationship("Application", back_populates="candidate")
    skills = relationship("CandidateSkill", back_populates="candidate")

class JobPosting(Base):
    __tablename__ = "job_postings"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    requirements = Column(JSONB, nullable=False)
    department = Column(String(100), nullable=False, index=True)
    location = Column(String)  # Will be handled as geography in PostgreSQL
    employment_type = Column(String(50), nullable=False)
    salary_range = Column(JSONB)
    status = Column(String(50), default="active", index=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    applications = relationship("Application", back_populates="job")
    required_skills = relationship("JobRequiredSkill", back_populates="job")
    creator = relationship("User")

class Application(Base):
    __tablename__ = "applications"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    candidate_id = Column(UUID(as_uuid=True), ForeignKey("candidates.id"), nullable=False, index=True)
    job_id = Column(UUID(as_uuid=True), ForeignKey("job_postings.id"), nullable=False, index=True)
    status = Column(String(50), default="applied", index=True)
    match_score = Column(DECIMAL(5,2), index=True)
    applied_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    candidate = relationship("Candidate", back_populates="applications")
    job = relationship("JobPosting", back_populates="applications")
    status_history = relationship("ApplicationStatusHistory", back_populates="application")

class ApplicationStatusHistory(Base):
    __tablename__ = "application_status_history"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    application_id = Column(UUID(as_uuid=True), ForeignKey("applications.id"), nullable=False, index=True)
    previous_status = Column(String(50))
    new_status = Column(String(50), nullable=False)
    changed_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    change_reason = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Relationships
    application = relationship("Application", back_populates="status_history")
    changed_by_user = relationship("User")

class Skill(Base):
    __tablename__ = "skills"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), unique=True, nullable=False)
    category = Column(String(50))
    synonyms = Column(ARRAY(Text))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    candidate_skills = relationship("CandidateSkill", back_populates="skill")
    job_requirements = relationship("JobRequiredSkill", back_populates="skill")

class CandidateSkill(Base):
    __tablename__ = "candidate_skills"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    candidate_id = Column(UUID(as_uuid=True), ForeignKey("candidates.id"), nullable=False, index=True)
    skill_id = Column(UUID(as_uuid=True), ForeignKey("skills.id"), nullable=False, index=True)
    proficiency_level = Column(String(20), default="intermediate")
    years_experience = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    candidate = relationship("Candidate", back_populates="skills")
    skill = relationship("Skill", back_populates="candidate_skills")

class JobRequiredSkill(Base):
    __tablename__ = "job_required_skills"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(UUID(as_uuid=True), ForeignKey("job_postings.id"), nullable=False, index=True)
    skill_id = Column(UUID(as_uuid=True), ForeignKey("skills.id"), nullable=False, index=True)
    required_level = Column(String(20), default="intermediate")
    min_years_experience = Column(Integer, default=0)
    is_mandatory = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    job = relationship("JobPosting", back_populates="required_skills")
    skill = relationship("Skill", back_populates="job_requirements")

class TestDefinition(Base):
    __tablename__ = "test_definitions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    duration_minutes = Column(Integer, nullable=False)
    passing_score = Column(Integer, default=70)
    question_count = Column(Integer, nullable=False)
    is_adaptive = Column(Boolean, default=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    creator = relationship("User")

class APIKey(Base):
    __tablename__ = "api_keys"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key_name = Column(String(100), nullable=False)
    api_key = Column(String(255), unique=True, nullable=False)
    permissions = Column(JSONB, nullable=False)
    rate_limit = Column(Integer, default=1000)
    is_active = Column(Boolean, default=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_used_at = Column(DateTime(timezone=True))
    
    # Relationships
    creator = relationship("User")

class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    action = Column(String(100), nullable=False, index=True)
    resource_type = Column(String(50), nullable=False)
    resource_id = Column(UUID(as_uuid=True))
    details = Column(JSONB)
    ip_address = Column(String(45))
    user_agent = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Relationships
    user = relationship("User")