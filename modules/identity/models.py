"""
SQLAlchemy models for ITADIAS Identity Microservice
"""
import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import Column, String, DateTime, Boolean, Integer, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from pydantic import BaseModel, EmailStr, Field
from database import Base
from config import config

# SQLAlchemy Models

class Candidate(Base):
    """Candidate model for identity schema"""
    __tablename__ = "candidates"
    __table_args__ = {"schema": config.db.schema}
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    phone = Column(String(20), unique=True, nullable=True, index=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    metadata = Column(Text, nullable=True)  # JSON string for additional data
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    otp_verifications = relationship("OTPVerification", back_populates="candidate", cascade="all, delete-orphan")

class OTPVerification(Base):
    """OTP verification model"""
    __tablename__ = "otp_verifications"
    __table_args__ = {"schema": config.db.schema}
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    candidate_id = Column(UUID(as_uuid=True), ForeignKey(f"{config.db.schema}.candidates.id"), nullable=False)
    otp_code = Column(String(10), nullable=False)
    channel = Column(String(20), nullable=False)  # 'email' or 'sms'
    contact_info = Column(String(255), nullable=False)  # email or phone number
    attempts = Column(Integer, default=0, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    verified_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    candidate = relationship("Candidate", back_populates="otp_verifications")

class EventLog(Base):
    """Event log model for tracking published events"""
    __tablename__ = "event_logs"
    __table_args__ = {"schema": config.db.schema}
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_type = Column(String(100), nullable=False)
    event_data = Column(Text, nullable=False)  # JSON string
    entity_id = Column(UUID(as_uuid=True), nullable=True)
    entity_type = Column(String(50), nullable=True)
    status = Column(String(20), default="pending", nullable=False)  # pending, published, failed
    attempts = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    published_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)

# Pydantic Models for API

class CandidateBase(BaseModel):
    """Base candidate schema"""
    email: EmailStr
    phone: Optional[str] = Field(None, pattern=r'^\+?[\d\s\-\(\)]+$')
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)

class CandidateCreate(CandidateBase):
    """Schema for creating a candidate"""
    send_otp: bool = Field(default=True, description="Whether to send OTP for verification")
    otp_channel: str = Field(default="email", pattern="^(email|sms|both)$", description="OTP delivery channel")

class CandidateResponse(CandidateBase):
    """Schema for candidate response"""
    id: uuid.UUID
    is_verified: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class CandidateCreateResponse(BaseModel):
    """Response schema for candidate creation"""
    candidate: CandidateResponse
    otp_sent: bool
    otp_channels: list[str]
    message: str

class OTPVerificationRequest(BaseModel):
    """Schema for OTP verification request"""
    candidate_id: uuid.UUID
    otp_code: str = Field(..., min_length=4, max_length=10)
    channel: str = Field(..., pattern="^(email|sms)$")

class OTPVerificationResponse(BaseModel):
    """Schema for OTP verification response"""
    success: bool
    message: str
    candidate_verified: bool

class ErrorResponse(BaseModel):
    """Standard error response schema"""
    error: str
    detail: Optional[str] = None
    code: Optional[str] = None