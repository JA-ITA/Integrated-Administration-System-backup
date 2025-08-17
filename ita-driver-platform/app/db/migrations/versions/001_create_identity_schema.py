"""Create identity schema and candidate tables

Revision ID: 001
Revises: 
Create Date: 2025-01-27 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create identity schema
    op.execute('CREATE SCHEMA IF NOT EXISTS identity')
    
    # Create candidates table
    op.create_table('candidates',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=True),
        sa.Column('first_name', sa.String(length=50), nullable=False),
        sa.Column('last_name', sa.String(length=50), nullable=False),
        sa.Column('phone', sa.String(length=20), nullable=False),
        sa.Column('date_of_birth', sa.DateTime(), nullable=True),
        sa.Column('national_id', sa.String(length=50), nullable=True),
        sa.Column('passport_number', sa.String(length=20), nullable=True),
        sa.Column('street_address', sa.String(length=200), nullable=True),
        sa.Column('city', sa.String(length=50), nullable=True),
        sa.Column('postal_code', sa.String(length=10), nullable=True),
        sa.Column('country', sa.String(length=50), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('is_phone_verified', sa.Boolean(), nullable=True),
        sa.Column('is_email_verified', sa.Boolean(), nullable=True),
        sa.Column('is_identity_verified', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('last_login', sa.DateTime(), nullable=True),
        sa.Column('verified_at', sa.DateTime(), nullable=True),
        sa.Column('email_otp', sa.String(length=6), nullable=True),
        sa.Column('email_otp_expires', sa.DateTime(), nullable=True),
        sa.Column('phone_otp', sa.String(length=6), nullable=True),
        sa.Column('phone_otp_expires', sa.DateTime(), nullable=True),
        sa.Column('password_reset_token', sa.String(length=64), nullable=True),
        sa.Column('password_reset_expires', sa.DateTime(), nullable=True),
        sa.Column('failed_login_attempts', sa.Integer(), nullable=True),
        sa.Column('locked_until', sa.DateTime(), nullable=True),
        sa.Column('profile_completion_percentage', sa.Integer(), nullable=True),
        sa.Column('preferred_language', sa.String(length=5), nullable=True),
        sa.Column('timezone', sa.String(length=50), nullable=True),
        sa.Column('notification_preferences', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        schema='identity'
    )
    
    # Create indexes for candidates table
    op.create_index(op.f('ix_identity_candidates_email'), 'candidates', ['email'], unique=True, schema='identity')
    op.create_index(op.f('ix_identity_candidates_phone'), 'candidates', ['phone'], unique=False, schema='identity')
    op.create_index(op.f('ix_identity_candidates_national_id'), 'candidates', ['national_id'], unique=True, schema='identity')
    
    # Create otp_attempts table
    op.create_table('otp_attempts',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('candidate_id', sa.String(length=36), nullable=False),
        sa.Column('otp_type', sa.String(length=20), nullable=False),
        sa.Column('otp_code', sa.String(length=6), nullable=False),
        sa.Column('recipient', sa.String(length=255), nullable=False),
        sa.Column('is_verified', sa.Boolean(), nullable=True),
        sa.Column('verified_at', sa.DateTime(), nullable=True),
        sa.Column('attempts_count', sa.Integer(), nullable=True),
        sa.Column('max_attempts', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['candidate_id'], ['identity.candidates.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        schema='identity'
    )
    
    # Create candidate_documents table
    op.create_table('candidate_documents',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('candidate_id', sa.String(length=36), nullable=False),
        sa.Column('document_type', sa.String(length=50), nullable=False),
        sa.Column('document_number', sa.String(length=100), nullable=True),
        sa.Column('document_name', sa.String(length=200), nullable=False),
        sa.Column('file_path', sa.String(length=500), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=False),
        sa.Column('mime_type', sa.String(length=100), nullable=False),
        sa.Column('is_verified', sa.Boolean(), nullable=True),
        sa.Column('verified_by', sa.String(length=36), nullable=True),
        sa.Column('verified_at', sa.DateTime(), nullable=True),
        sa.Column('verification_notes', sa.Text(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('uploaded_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['candidate_id'], ['identity.candidates.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        schema='identity'
    )
    
    # Create candidate_events table
    op.create_table('candidate_events',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('candidate_id', sa.String(length=36), nullable=False),
        sa.Column('event_type', sa.String(length=100), nullable=False),
        sa.Column('event_data', sa.Text(), nullable=True),
        sa.Column('event_source', sa.String(length=100), nullable=False),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('correlation_id', sa.String(length=36), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['candidate_id'], ['identity.candidates.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        schema='identity'
    )
    
    # Create candidate_sessions table
    op.create_table('candidate_sessions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('candidate_id', sa.String(length=36), nullable=False),
        sa.Column('access_token_hash', sa.String(length=64), nullable=False),
        sa.Column('refresh_token_hash', sa.String(length=64), nullable=False),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('device_fingerprint', sa.String(length=64), nullable=True),
        sa.Column('location', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('last_accessed', sa.DateTime(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('revoked_at', sa.DateTime(), nullable=True),
        sa.Column('revoked_reason', sa.String(length=100), nullable=True),
        sa.ForeignKeyConstraint(['candidate_id'], ['identity.candidates.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        schema='identity'
    )
    
    # Create additional indexes for performance
    op.create_index(op.f('ix_identity_otp_attempts_candidate_id'), 'otp_attempts', ['candidate_id'], unique=False, schema='identity')
    op.create_index(op.f('ix_identity_otp_attempts_expires_at'), 'otp_attempts', ['expires_at'], unique=False, schema='identity')
    op.create_index(op.f('ix_identity_candidate_events_candidate_id'), 'candidate_events', ['candidate_id'], unique=False, schema='identity')
    op.create_index(op.f('ix_identity_candidate_events_event_type'), 'candidate_events', ['event_type'], unique=False, schema='identity')
    op.create_index(op.f('ix_identity_candidate_sessions_candidate_id'), 'candidate_sessions', ['candidate_id'], unique=False, schema='identity')
    op.create_index(op.f('ix_identity_candidate_sessions_expires_at'), 'candidate_sessions', ['expires_at'], unique=False, schema='identity')


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table('candidate_sessions', schema='identity')
    op.drop_table('candidate_events', schema='identity') 
    op.drop_table('candidate_documents', schema='identity')
    op.drop_table('otp_attempts', schema='identity')
    op.drop_table('candidates', schema='identity')
    
    # Drop schema
    op.execute('DROP SCHEMA IF EXISTS identity CASCADE')