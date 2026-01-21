"""Add workflow stages and SLA tracking tables

Revision ID: workflow_sla_001
Revises: c5908c310bed
Create Date: 2024-01-21 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'workflow_sla_001'
down_revision = 'c5908c310bed'
branch_labels = None
depends_on = None


def upgrade():
    # Create workflow_stages table
    op.create_table('workflow_stages',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('job_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('order_index', sa.Integer(), nullable=False),
        sa.Column('sla_hours', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('auto_advance_rules', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['job_id'], ['job_postings.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_workflow_stages_job_id'), 'workflow_stages', ['job_id'], unique=False)

    # Create stage_transitions table
    op.create_table('stage_transitions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('application_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('stage_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('entered_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('exited_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('sla_deadline', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_escalated', sa.Boolean(), nullable=True),
        sa.Column('escalated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('escalated_to', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['application_id'], ['applications.id'], ),
        sa.ForeignKeyConstraint(['escalated_to'], ['users.id'], ),
        sa.ForeignKeyConstraint(['stage_id'], ['workflow_stages.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_stage_transitions_application_id'), 'stage_transitions', ['application_id'], unique=False)
    op.create_index(op.f('ix_stage_transitions_entered_at'), 'stage_transitions', ['entered_at'], unique=False)
    op.create_index(op.f('ix_stage_transitions_sla_deadline'), 'stage_transitions', ['sla_deadline'], unique=False)
    op.create_index(op.f('ix_stage_transitions_stage_id'), 'stage_transitions', ['stage_id'], unique=False)

    # Create sla_escalations table
    op.create_table('sla_escalations',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('application_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('stage_transition_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('escalation_type', sa.String(length=50), nullable=False),
        sa.Column('escalated_to', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('escalation_reason', sa.Text(), nullable=True),
        sa.Column('is_resolved', sa.Boolean(), nullable=True),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('resolved_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['application_id'], ['applications.id'], ),
        sa.ForeignKeyConstraint(['escalated_to'], ['users.id'], ),
        sa.ForeignKeyConstraint(['resolved_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['stage_transition_id'], ['stage_transitions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_sla_escalations_created_at'), 'sla_escalations', ['created_at'], unique=False)


def downgrade():
    # Drop tables in reverse order
    op.drop_index(op.f('ix_sla_escalations_created_at'), table_name='sla_escalations')
    op.drop_table('sla_escalations')
    
    op.drop_index(op.f('ix_stage_transitions_stage_id'), table_name='stage_transitions')
    op.drop_index(op.f('ix_stage_transitions_sla_deadline'), table_name='stage_transitions')
    op.drop_index(op.f('ix_stage_transitions_entered_at'), table_name='stage_transitions')
    op.drop_index(op.f('ix_stage_transitions_application_id'), table_name='stage_transitions')
    op.drop_table('stage_transitions')
    
    op.drop_index(op.f('ix_workflow_stages_job_id'), table_name='workflow_stages')
    op.drop_table('workflow_stages')