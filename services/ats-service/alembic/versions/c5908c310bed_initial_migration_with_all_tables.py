"""Initial migration with all tables

Revision ID: c5908c310bed
Revises: 
Create Date: 2026-01-21 13:33:12.776109

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid


# revision identifiers, used by Alembic.
revision: str = 'c5908c310bed'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create users table
    op.create_table('users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('email', sa.String(255), nullable=False, unique=True, index=True),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('first_name', sa.String(100), nullable=False),
        sa.Column('last_name', sa.String(100), nullable=False),
        sa.Column('role', sa.String(50), nullable=False, default='recruiter'),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now())
    )
    
    # Create skills table
    op.create_table('skills',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('name', sa.String(100), nullable=False, unique=True),
        sa.Column('category', sa.String(50)),
        sa.Column('synonyms', postgresql.ARRAY(sa.Text())),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now())
    )
    
    # Create candidates table
    op.create_table('candidates',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('email', sa.String(255), nullable=False, unique=True, index=True),
        sa.Column('first_name', sa.String(100), nullable=False),
        sa.Column('last_name', sa.String(100), nullable=False),
        sa.Column('phone', sa.String(20)),
        sa.Column('location', sa.Text()),  # Will store geography as text for now
        sa.Column('resume_url', sa.Text()),
        sa.Column('parsed_resume', postgresql.JSONB()),
        sa.Column('status', sa.String(50), default='active', index=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), index=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now())
    )
    
    # Create job_postings table
    op.create_table('job_postings',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('requirements', postgresql.JSONB(), nullable=False),
        sa.Column('department', sa.String(100), nullable=False, index=True),
        sa.Column('location', sa.Text()),  # Will store geography as text for now
        sa.Column('employment_type', sa.String(50), nullable=False),
        sa.Column('salary_range', postgresql.JSONB()),
        sa.Column('status', sa.String(50), default='active', index=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), index=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now())
    )
    
    # Create applications table
    op.create_table('applications',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('candidate_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('candidates.id'), nullable=False, index=True),
        sa.Column('job_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('job_postings.id'), nullable=False, index=True),
        sa.Column('status', sa.String(50), default='applied', index=True),
        sa.Column('match_score', sa.DECIMAL(5,2), index=True),
        sa.Column('applied_at', sa.DateTime(timezone=True), server_default=sa.func.now(), index=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.UniqueConstraint('candidate_id', 'job_id', name='unique_candidate_job_application')
    )
    
    # Create application_status_history table
    op.create_table('application_status_history',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('application_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('applications.id'), nullable=False, index=True),
        sa.Column('previous_status', sa.String(50)),
        sa.Column('new_status', sa.String(50), nullable=False),
        sa.Column('changed_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id')),
        sa.Column('change_reason', sa.Text()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), index=True)
    )
    
    # Create candidate_skills table
    op.create_table('candidate_skills',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('candidate_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('candidates.id'), nullable=False, index=True),
        sa.Column('skill_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('skills.id'), nullable=False, index=True),
        sa.Column('proficiency_level', sa.String(20), default='intermediate'),
        sa.Column('years_experience', sa.Integer(), default=0),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now())
    )
    
    # Create job_required_skills table
    op.create_table('job_required_skills',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('job_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('job_postings.id'), nullable=False, index=True),
        sa.Column('skill_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('skills.id'), nullable=False, index=True),
        sa.Column('required_level', sa.String(20), default='intermediate'),
        sa.Column('min_years_experience', sa.Integer(), default=0),
        sa.Column('is_mandatory', sa.Boolean(), default=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now())
    )
    
    # Create test_definitions table
    op.create_table('test_definitions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('duration_minutes', sa.Integer(), nullable=False),
        sa.Column('passing_score', sa.Integer(), default=70),
        sa.Column('question_count', sa.Integer(), nullable=False),
        sa.Column('is_adaptive', sa.Boolean(), default=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now())
    )
    
    # Create api_keys table
    op.create_table('api_keys',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('key_name', sa.String(100), nullable=False),
        sa.Column('api_key', sa.String(255), nullable=False, unique=True),
        sa.Column('permissions', postgresql.JSONB(), nullable=False),
        sa.Column('rate_limit', sa.Integer(), default=1000),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('last_used_at', sa.DateTime(timezone=True))
    )
    
    # Create audit_logs table
    op.create_table('audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), index=True),
        sa.Column('action', sa.String(100), nullable=False, index=True),
        sa.Column('resource_type', sa.String(50), nullable=False),
        sa.Column('resource_id', postgresql.UUID(as_uuid=True)),
        sa.Column('details', postgresql.JSONB()),
        sa.Column('ip_address', sa.String(45)),
        sa.Column('user_agent', sa.Text()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), index=True)
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('audit_logs')
    op.drop_table('api_keys')
    op.drop_table('test_definitions')
    op.drop_table('job_required_skills')
    op.drop_table('candidate_skills')
    op.drop_table('application_status_history')
    op.drop_table('applications')
    op.drop_table('job_postings')
    op.drop_table('candidates')
    op.drop_table('skills')
    op.drop_table('users')
