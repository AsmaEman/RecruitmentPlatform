from sqlalchemy import Column, String, DateTime, Boolean, Integer, Text, DECIMAL, ForeignKey, ARRAY
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy import TypeDecorator, String as SQLString
import uuid

Base = declarative_base()

# Custom UUID type that works with SQLite
class GUID(TypeDecorator):
    """Platform-independent GUID type.
    Uses PostgreSQL's UUID type, otherwise uses CHAR(36), storing as stringified hex values.
    """
    impl = SQLString
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(UUID())
        else:
            return dialect.type_descriptor(SQLString(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return str(value)
        else:
            if not isinstance(value, uuid.UUID):
                return str(uuid.UUID(value))
            else:
                return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        else:
            if not isinstance(value, uuid.UUID):
                return uuid.UUID(value)
            return value

# Custom JSONB type that works with SQLite
class JSON(TypeDecorator):
    """Platform-independent JSON type.
    Uses PostgreSQL's JSONB type, otherwise uses TEXT with JSON serialization.
    """
    impl = Text
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(JSONB())
        else:
            return dialect.type_descriptor(Text())

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return value
        else:
            import json
            return json.dumps(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return value
        else:
            import json
            return json.loads(value)

class User(Base):
    __tablename__ = "users"
    
    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
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
    
    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    phone = Column(String(20))
    location = Column(Text)  # Store location as text (can be enhanced with PostGIS later)
    resume_url = Column(Text)
    parsed_resume = Column(JSON)
    status = Column(String(50), default="active", index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    applications = relationship("Application", back_populates="candidate")
    skills = relationship("CandidateSkill", back_populates="candidate")

class JobPosting(Base):
    __tablename__ = "job_postings"
    
    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    requirements = Column(JSON, nullable=False)
    department = Column(String(100), nullable=False, index=True)
    location = Column(Text)  # Store location as text (can be enhanced with PostGIS later)
    employment_type = Column(String(50), nullable=False)
    salary_range = Column(JSON)
    status = Column(String(50), default="active", index=True)
    created_by = Column(GUID(), ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    applications = relationship("Application", back_populates="job")
    required_skills = relationship("JobRequiredSkill", back_populates="job")
    creator = relationship("User")

class Application(Base):
    __tablename__ = "applications"
    
    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    candidate_id = Column(GUID(), ForeignKey("candidates.id"), nullable=False, index=True)
    job_id = Column(GUID(), ForeignKey("job_postings.id"), nullable=False, index=True)
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
    
    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    application_id = Column(GUID(), ForeignKey("applications.id"), nullable=False, index=True)
    previous_status = Column(String(50))
    new_status = Column(String(50), nullable=False)
    changed_by = Column(GUID(), ForeignKey("users.id"))
    change_reason = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Relationships
    application = relationship("Application", back_populates="status_history")
    changed_by_user = relationship("User")

class Skill(Base):
    __tablename__ = "skills"
    
    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), unique=True, nullable=False)
    category = Column(String(50))
    synonyms = Column(Text)  # Store as JSON string for SQLite compatibility
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    candidate_skills = relationship("CandidateSkill", back_populates="skill")
    job_requirements = relationship("JobRequiredSkill", back_populates="skill")

class CandidateSkill(Base):
    __tablename__ = "candidate_skills"
    
    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    candidate_id = Column(GUID(), ForeignKey("candidates.id"), nullable=False, index=True)
    skill_id = Column(GUID(), ForeignKey("skills.id"), nullable=False, index=True)
    proficiency_level = Column(String(20), default="intermediate")
    years_experience = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    candidate = relationship("Candidate", back_populates="skills")
    skill = relationship("Skill", back_populates="candidate_skills")

class JobRequiredSkill(Base):
    __tablename__ = "job_required_skills"
    
    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    job_id = Column(GUID(), ForeignKey("job_postings.id"), nullable=False, index=True)
    skill_id = Column(GUID(), ForeignKey("skills.id"), nullable=False, index=True)
    required_level = Column(String(20), default="intermediate")
    min_years_experience = Column(Integer, default=0)
    is_mandatory = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    job = relationship("JobPosting", back_populates="required_skills")
    skill = relationship("Skill", back_populates="job_requirements")

class TestDefinition(Base):
    __tablename__ = "test_definitions"
    
    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    duration_minutes = Column(Integer, nullable=False)
    passing_score = Column(Integer, default=70)
    question_count = Column(Integer, nullable=False)
    is_adaptive = Column(Boolean, default=False)
    created_by = Column(GUID(), ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    creator = relationship("User")

class APIKey(Base):
    __tablename__ = "api_keys"
    
    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    key_name = Column(String(100), nullable=False)
    api_key = Column(String(255), unique=True, nullable=False)
    permissions = Column(JSON, nullable=False)
    rate_limit = Column(Integer, default=1000)
    is_active = Column(Boolean, default=True)
    created_by = Column(GUID(), ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_used_at = Column(DateTime(timezone=True))
    
    # Relationships
    creator = relationship("User")

class WorkflowStage(Base):
    __tablename__ = "workflow_stages"
    
    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    job_id = Column(GUID(), ForeignKey("job_postings.id"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    order_index = Column(Integer, nullable=False)
    sla_hours = Column(Integer, default=72)  # Default 72 hours SLA
    is_active = Column(Boolean, default=True)
    auto_advance_rules = Column(JSON)  # Rules for automatic stage advancement
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    job = relationship("JobPosting")
    stage_transitions = relationship("StageTransition", back_populates="stage")

class StageTransition(Base):
    __tablename__ = "stage_transitions"
    
    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    application_id = Column(GUID(), ForeignKey("applications.id"), nullable=False, index=True)
    stage_id = Column(GUID(), ForeignKey("workflow_stages.id"), nullable=False, index=True)
    entered_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    exited_at = Column(DateTime(timezone=True), index=True)
    sla_deadline = Column(DateTime(timezone=True), index=True)
    is_escalated = Column(Boolean, default=False)
    escalated_at = Column(DateTime(timezone=True))
    escalated_to = Column(GUID(), ForeignKey("users.id"))
    notes = Column(Text)
    
    # Relationships
    application = relationship("Application")
    stage = relationship("WorkflowStage", back_populates="stage_transitions")
    escalated_to_user = relationship("User")

class SLAEscalation(Base):
    __tablename__ = "sla_escalations"
    
    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    application_id = Column(GUID(), ForeignKey("applications.id"), nullable=False, index=True)
    stage_transition_id = Column(GUID(), ForeignKey("stage_transitions.id"), nullable=False, index=True)
    escalation_type = Column(String(50), nullable=False)  # 'warning', 'critical', 'overdue'
    escalated_to = Column(GUID(), ForeignKey("users.id"), nullable=False)
    escalation_reason = Column(Text)
    is_resolved = Column(Boolean, default=False)
    resolved_at = Column(DateTime(timezone=True))
    resolved_by = Column(GUID(), ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Relationships
    application = relationship("Application")
    stage_transition = relationship("StageTransition")
    escalated_to_user = relationship("User", foreign_keys=[escalated_to])
    resolved_by_user = relationship("User", foreign_keys=[resolved_by])

class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id = Column(GUID(), ForeignKey("users.id"), index=True)
    action = Column(String(100), nullable=False, index=True)
    resource_type = Column(String(50), nullable=False)
    resource_id = Column(GUID())
    details = Column(JSON)
    ip_address = Column(String(45))
    user_agent = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Relationships
    user = relationship("User")