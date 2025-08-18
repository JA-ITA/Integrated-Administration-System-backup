"""
SQLAlchemy models for ITADIAS Certificate Microservice
"""
import uuid
import json
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any
from sqlalchemy import Column, String, DateTime, Boolean, Text, JSON, Integer
from sqlalchemy.dialects.postgresql import UUID
from pydantic import BaseModel, Field, validator
import enum
from database import Base
from config import config

# Enums

class CertificateType(str, enum.Enum):
    DRIVER_LICENCE = "driver_licence"
    ENDORSEMENT = "endorsement"
    COMPLETION = "completion"

class CertificateStatus(str, enum.Enum):
    ACTIVE = "active"
    EXPIRED = "expired" 
    REVOKED = "revoked"
    SUSPENDED = "suspended"

# SQLAlchemy Models

class Certificate(Base):
    """Certificate model for certificate schema"""
    __tablename__ = "certificates"
    __table_args__ = {"schema": config.db.schema}
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    driver_record_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    certificate_type = Column(String(50), nullable=False)
    licence_endorsement = Column(String(100), nullable=False)
    candidate_name = Column(String(200), nullable=False)
    service_hub = Column(String(100), nullable=False)
    issue_date = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    expiry_date = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(20), default=CertificateStatus.ACTIVE, nullable=False)
    
    # Storage information
    file_url = Column(Text, nullable=False)  # S3/MinIO URL
    file_size = Column(Integer, nullable=True)
    file_hash = Column(String(64), nullable=True)  # SHA-256 hash
    
    # QR Code verification
    qr_code = Column(String(500), nullable=True)  # QR code URL for verification
    verification_token = Column(String(100), nullable=True, unique=True)
    
    # Metadata
    metadata = Column(JSON, nullable=True)  # Additional certificate data
    template_used = Column(String(50), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    def is_valid(self) -> bool:
        """Check if certificate is currently valid"""
        if self.status != CertificateStatus.ACTIVE:
            return False
        
        if self.expiry_date and self.expiry_date < datetime.now(timezone.utc):
            return False
        
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert certificate to dictionary"""
        return {
            "id": str(self.id),
            "driver_record_id": str(self.driver_record_id),
            "certificate_type": self.certificate_type,
            "licence_endorsement": self.licence_endorsement,
            "candidate_name": self.candidate_name,
            "service_hub": self.service_hub,
            "issue_date": self.issue_date.isoformat() if self.issue_date else None,
            "expiry_date": self.expiry_date.isoformat() if self.expiry_date else None,
            "status": self.status,
            "file_url": self.file_url,
            "qr_code": self.qr_code,
            "verification_token": self.verification_token,
            "metadata": self.metadata,
            "is_valid": self.is_valid(),
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

# Pydantic Models for API

class CertificateGenerateRequest(BaseModel):
    """Schema for certificate generation request"""
    driver_record_id: uuid.UUID = Field(..., description="Driver record ID from registration/test completion")
    
    class Config:
        from_attributes = True

class CertificateGenerateResponse(BaseModel):
    """Schema for certificate generation response"""
    certificate_id: uuid.UUID
    download_url: str
    verification_token: str
    qr_code: Optional[str]
    issue_date: datetime
    expiry_date: Optional[datetime]
    metadata: Dict[str, Any]

class CertificateVerificationResponse(BaseModel):
    """Schema for certificate verification response"""
    valid: bool
    certificate_id: Optional[uuid.UUID]
    candidate_name: Optional[str]
    licence_endorsement: Optional[str]
    issue_date: Optional[datetime]
    expiry_date: Optional[datetime]
    status: Optional[str]
    service_hub: Optional[str]
    message: str

class CertificateMetadata(BaseModel):
    """Certificate metadata structure"""
    candidate_full_name: str
    driver_record_number: str
    licence_endorsement: str
    issue_date: str
    expiry_date: Optional[str] = None
    certificate_id: str
    service_hub_name: str
    test_score: Optional[float] = None
    test_date: Optional[str] = None
    issuing_authority: str = "Island Traffic Authority"
    
    class Config:
        from_attributes = True

class ErrorResponse(BaseModel):
    """Standard error response schema"""
    error: str
    detail: Optional[str] = None
    code: Optional[str] = None

# Utility functions

def generate_verification_token() -> str:
    """Generate a unique verification token for QR codes"""
    import secrets
    return secrets.token_urlsafe(16)

def calculate_expiry_date(certificate_type: str, issue_date: datetime) -> Optional[datetime]:
    """Calculate expiry date based on certificate type"""
    if certificate_type == CertificateType.DRIVER_LICENCE:
        # Driver's license expires after 5 years
        return issue_date + timedelta(days=5*365)
    elif certificate_type == CertificateType.ENDORSEMENT:
        # Endorsements expire after 3 years
        return issue_date + timedelta(days=3*365)
    else:
        # Completion certificates don't expire
        return None

def generate_qr_code_url(verification_token: str, base_url: str) -> str:
    """Generate QR code URL for certificate verification"""
    return f"{base_url}/{verification_token}"