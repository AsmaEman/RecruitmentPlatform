from pydantic import BaseModel, EmailStr, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID
from decimal import Decimal

# Authentication schemas
class Token(BaseModel):
    access_token: str
    token_type: str
    expires_in: int

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    first_name: str
    last_name: str
    role: str = "recruiter"

class UserResponse(BaseModel):
    id: UUID
    email: str
    first_name: str
    last_name: str
    role: str
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

# Candidate schemas
class CandidateCreate(BaseModel):
    email: EmailStr
    first_name: str
    last_name: str
    phone: Optional[str] = None
    location: Optional[str] = None
    resume_url: Optional[str] = None
    parsed_resume: Optional[Dict[str, Any]] = None

class CandidateUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    resume_url: Optional[str] = None
    parsed_resume: Optional[Dict[str, Any]] = None
    status: Optional[str] = None

class CandidateResponse(BaseModel):
    id: UUID
    email: str
    first_name: str
    last_name: str
    phone: Optional[str]
    location: Optional[str]
    resume_url: Optional[str]
    parsed_resume: Optional[Dict[str, Any]]
    status: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# Job posting schemas
class JobCreate(BaseModel):
    title: str
    description: str
    requirements: Dict[str, Any]
    department: str
    location: Optional[str] = None
    employment_type: str
    salary_range: Optional[Dict[str, Any]] = None
    created_by: UUID

class JobUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    requirements: Optional[Dict[str, Any]] = None
    department: Optional[str] = None
    location: Optional[str] = None
    employment_type: Optional[str] = None
    salary_range: Optional[Dict[str, Any]] = None
    status: Optional[str] = None

class JobResponse(BaseModel):
    id: UUID
    title: str
    description: str
    requirements: Dict[str, Any]
    department: str
    location: Optional[str]
    employment_type: str
    salary_range: Optional[Dict[str, Any]]
    status: str
    created_by: UUID
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# Application schemas
class ApplicationCreate(BaseModel):
    candidate_id: UUID
    job_id: UUID
    match_score: Optional[Decimal] = None

class ApplicationStatusUpdate(BaseModel):
    status: str
    changed_by: UUID
    reason: Optional[str] = None

class BulkStatusUpdate(BaseModel):
    application_ids: List[UUID]
    new_status: str
    changed_by: UUID
    reason: Optional[str] = None

class BulkOperationProgress(BaseModel):
    operation_id: str
    status: str  # "in_progress", "completed", "failed"
    total: int
    processed: int
    successful: int
    failed: int
    progress_percentage: float
    errors: List[str]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]

class BulkRejectRequest(BaseModel):
    application_ids: List[UUID]
    rejection_reason: str
    changed_by: UUID

class BulkApproveRequest(BaseModel):
    application_ids: List[UUID]
    approval_reason: str
    changed_by: UUID
    next_stage: str = "interview"

class BulkStageMovementRequest(BaseModel):
    application_ids: List[UUID]
    stage_id: UUID
    changed_by: UUID
    reason: Optional[str] = None

class ApplicationResponse(BaseModel):
    id: UUID
    candidate_id: UUID
    job_id: UUID
    status: str
    match_score: Optional[Decimal]
    applied_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# Workflow schemas
class WorkflowStageCreate(BaseModel):
    job_id: UUID
    name: str
    description: Optional[str] = None
    order_index: int
    sla_hours: int = 72
    auto_advance_rules: Optional[Dict[str, Any]] = None

class WorkflowStageResponse(BaseModel):
    id: UUID
    job_id: UUID
    name: str
    description: Optional[str]
    order_index: int
    sla_hours: int
    is_active: bool
    auto_advance_rules: Optional[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class StageTransitionCreate(BaseModel):
    application_id: UUID
    stage_id: UUID
    notes: Optional[str] = None

class StageTransitionResponse(BaseModel):
    id: UUID
    application_id: UUID
    stage_id: UUID
    entered_at: datetime
    exited_at: Optional[datetime]
    sla_deadline: Optional[datetime]
    is_escalated: bool
    escalated_at: Optional[datetime]
    escalated_to: Optional[UUID]
    notes: Optional[str]
    
    class Config:
        from_attributes = True

class SLAEscalationResponse(BaseModel):
    id: UUID
    application_id: UUID
    stage_transition_id: UUID
    escalation_type: str
    escalated_to: UUID
    escalation_reason: Optional[str]
    is_resolved: bool
    resolved_at: Optional[datetime]
    resolved_by: Optional[UUID]
    created_at: datetime
    
    class Config:
        from_attributes = True

# Skill schemas
class SkillCreate(BaseModel):
    name: str
    category: Optional[str] = None
    synonyms: Optional[List[str]] = None

class SkillResponse(BaseModel):
    id: UUID
    name: str
    category: Optional[str]
    synonyms: Optional[List[str]]
    created_at: datetime
    
    class Config:
        from_attributes = True