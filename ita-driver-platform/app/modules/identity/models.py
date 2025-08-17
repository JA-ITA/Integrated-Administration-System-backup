"""
Identity Module SQLAlchemy Models - Enhanced for Candidate Management
Database models for candidates, OTP verification, and identity management.
"""

from datetime import datetime, timedelta
from typing import List, Optional
from sqlalchemy import String, Boolean, DateTime, Text, ForeignKey, Table, Column, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.schema import CreateSchema
from sqlalchemy.sql import text

from core.database import Base


class Candidate(Base):
    """Candidate model for driver license applicants with OTP verification."""
    
    __tablename__ = "candidates"
    __table_args__ = {"schema": "identity"}
    
    # Primary key and basic info
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=True)  # Initially null until verified
    
    # Profile information
    first_name: Mapped[str] = mapped_column(String(50), nullable=False)
    last_name: Mapped[str] = mapped_column(String(50), nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    date_of_birth: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    
    # Government identification
    national_id: Mapped[str] = mapped_column(String(50), nullable=True, unique=True, index=True)
    passport_number: Mapped[str] = mapped_column(String(20), nullable=True)
    
    # Address information
    street_address: Mapped[str] = mapped_column(String(200), nullable=True)
    city: Mapped[str] = mapped_column(String(50), nullable=True)
    postal_code: Mapped[str] = mapped_column(String(10), nullable=True)
    country: Mapped[str] = mapped_column(String(50), default="Bermuda")
    
    # Candidate status and verification
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending_verification")
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    is_phone_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    is_email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    is_identity_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    verified_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    
    # OTP and verification tokens
    email_otp: Mapped[str] = mapped_column(String(6), nullable=True)
    email_otp_expires: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    phone_otp: Mapped[str] = mapped_column(String(6), nullable=True)
    phone_otp_expires: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    
    # Password reset functionality
    password_reset_token: Mapped[str] = mapped_column(String(64), nullable=True)
    password_reset_expires: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    
    # Security features
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    
    # Profile completion tracking
    profile_completion_percentage: Mapped[int] = mapped_column(Integer, default=0)
    
    # Preferences
    preferred_language: Mapped[str] = mapped_column(String(5), default="en")
    timezone: Mapped[str] = mapped_column(String(50), default="Atlantic/Bermuda")
    notification_preferences: Mapped[str] = mapped_column(Text, nullable=True)  # JSON string
    
    # Relationships
    otp_attempts: Mapped[List["OTPAttempt"]] = relationship("OTPAttempt", back_populates="candidate", cascade="all, delete-orphan")
    profile_documents: Mapped[List["CandidateDocument"]] = relationship("CandidateDocument", back_populates="candidate", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Candidate(id={self.id}, email={self.email}, status={self.status})>"
    
    @property
    def full_name(self):
        """Get candidate's full name."""
        return f"{self.first_name} {self.last_name}"
    
    @property
    def is_fully_verified(self):
        """Check if candidate is fully verified."""
        return self.is_phone_verified and self.is_email_verified and self.is_identity_verified
    
    @property
    def can_login(self):
        """Check if candidate can login."""
        return (
            self.is_active and 
            self.is_fully_verified and 
            self.hashed_password is not None and
            (self.locked_until is None or self.locked_until < datetime.utcnow())
        )
    
    def calculate_profile_completion(self):
        """Calculate profile completion percentage."""
        total_fields = 12
        completed_fields = 0
        
        # Required fields
        if self.email: completed_fields += 1
        if self.first_name: completed_fields += 1
        if self.last_name: completed_fields += 1
        if self.phone: completed_fields += 1
        if self.date_of_birth: completed_fields += 1
        if self.national_id: completed_fields += 1
        if self.street_address: completed_fields += 1
        if self.city: completed_fields += 1
        
        # Verification fields
        if self.is_email_verified: completed_fields += 1
        if self.is_phone_verified: completed_fields += 1
        if self.is_identity_verified: completed_fields += 1
        if self.hashed_password: completed_fields += 1
        
        self.profile_completion_percentage = int((completed_fields / total_fields) * 100)
        return self.profile_completion_percentage


class OTPAttempt(Base):
    """Model for tracking OTP verification attempts and rate limiting."""
    
    __tablename__ = "otp_attempts"
    __table_args__ = {"schema": "identity"}
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    candidate_id: Mapped[str] = mapped_column(String(36), ForeignKey("identity.candidates.id", ondelete="CASCADE"), nullable=False)
    
    # OTP details
    otp_type: Mapped[str] = mapped_column(String(20), nullable=False)  # 'email' or 'phone'
    otp_code: Mapped[str] = mapped_column(String(6), nullable=False)
    recipient: Mapped[str] = mapped_column(String(255), nullable=False)  # email or phone number
    
    # Attempt tracking
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    verified_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    attempts_count: Mapped[int] = mapped_column(Integer, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    
    # IP and device tracking for security
    ip_address: Mapped[str] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str] = mapped_column(Text, nullable=True)
    
    # Relationships
    candidate: Mapped["Candidate"] = relationship("Candidate", back_populates="otp_attempts")
    
    def __repr__(self):
        return f"<OTPAttempt(id={self.id}, candidate_id={self.candidate_id}, type={self.otp_type})>"
    
    @property
    def is_expired(self):
        """Check if OTP is expired."""
        return datetime.utcnow() > self.expires_at
    
    @property
    def is_exhausted(self):
        """Check if maximum attempts reached."""
        return self.attempts_count >= self.max_attempts
    
    @property
    def can_attempt(self):
        """Check if OTP can still be attempted."""
        return not self.is_expired and not self.is_exhausted and not self.is_verified


class CandidateDocument(Base):
    """Model for storing candidate document information and verification status."""
    
    __tablename__ = "candidate_documents"
    __table_args__ = {"schema": "identity"}
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    candidate_id: Mapped[str] = mapped_column(String(36), ForeignKey("identity.candidates.id", ondelete="CASCADE"), nullable=False)
    
    # Document information
    document_type: Mapped[str] = mapped_column(String(50), nullable=False)  # 'passport', 'national_id', 'birth_certificate', etc.
    document_number: Mapped[str] = mapped_column(String(100), nullable=True)
    document_name: Mapped[str] = mapped_column(String(200), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    
    # Verification status
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    verified_by: Mapped[str] = mapped_column(String(36), nullable=True)  # admin/examiner who verified
    verified_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    verification_notes: Mapped[str] = mapped_column(Text, nullable=True)
    
    # Document expiration (for passports, etc.)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    
    # Timestamps
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    candidate: Mapped["Candidate"] = relationship("Candidate", back_populates="profile_documents")
    
    def __repr__(self):
        return f"<CandidateDocument(id={self.id}, candidate_id={self.candidate_id}, type={self.document_type})>"
    
    @property
    def is_expired(self):
        """Check if document is expired."""
        return self.expires_at and datetime.utcnow() > self.expires_at


class CandidateEvent(Base):
    """Model for storing candidate-related events for audit and event sourcing."""
    
    __tablename__ = "candidate_events"
    __table_args__ = {"schema": "identity"}
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    candidate_id: Mapped[str] = mapped_column(String(36), ForeignKey("identity.candidates.id", ondelete="CASCADE"), nullable=False)
    
    # Event information
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)  # 'CandidateCreated', 'EmailVerified', etc.
    event_data: Mapped[str] = mapped_column(Text, nullable=True)  # JSON payload
    event_source: Mapped[str] = mapped_column(String(100), nullable=False)  # 'api', 'admin_panel', etc.
    
    # Metadata
    ip_address: Mapped[str] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str] = mapped_column(Text, nullable=True)
    correlation_id: Mapped[str] = mapped_column(String(36), nullable=True)  # For tracing across services
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    candidate: Mapped["Candidate"] = relationship("Candidate")
    
    def __repr__(self):
        return f"<CandidateEvent(id={self.id}, candidate_id={self.candidate_id}, type={self.event_type})>"


class CandidateSession(Base):
    """Model for tracking candidate sessions and token management."""
    
    __tablename__ = "candidate_sessions"
    __table_args__ = {"schema": "identity"}
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    candidate_id: Mapped[str] = mapped_column(String(36), ForeignKey("identity.candidates.id", ondelete="CASCADE"), nullable=False)
    
    # Session information
    access_token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    refresh_token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    
    # Session metadata
    ip_address: Mapped[str] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str] = mapped_column(Text, nullable=True)
    device_fingerprint: Mapped[str] = mapped_column(String(64), nullable=True)
    location: Mapped[str] = mapped_column(String(100), nullable=True)  # Derived from IP
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_accessed: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    
    # Session status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    revoked_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    revoked_reason: Mapped[str] = mapped_column(String(100), nullable=True)
    
    # Relationships
    candidate: Mapped["Candidate"] = relationship("Candidate")
    
    def __repr__(self):
        return f"<CandidateSession(id={self.id}, candidate_id={self.candidate_id})>"
    
    @property
    def is_expired(self):
        """Check if session is expired."""
        return datetime.utcnow() > self.expires_at
    
    @property
    def is_valid(self):
        """Check if session is valid and can be used."""
        return self.is_active and not self.is_expired and self.revoked_at is None


# Create identity schema if it doesn't exist
def create_identity_schema():
    """Create the identity schema in the database."""
    from sqlalchemy import create_engine
    from core.config import get_database_url
    
    engine = create_engine(get_database_url().replace('+asyncpg', ''))
    with engine.connect() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS identity"))
        conn.commit()
    engine.dispose()