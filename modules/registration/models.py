"""
SQLAlchemy models for ITADIAS Registration Microservice
"""
import uuid
import json
from datetime import datetime, timezone, date
from typing import Optional, List, Dict, Any
from sqlalchemy import Column, String, DateTime, Boolean, Integer, Text, DECIMAL, JSON
from sqlalchemy.dialects.postgresql import UUID, JSONB
from pydantic import BaseModel, Field, validator
from dateutil.relativedelta import relativedelta
import enum
from database import Base
from config import config

# Enums

class VehicleCategory(str, enum.Enum):
    B = "B"
    C = "C"
    PPV = "PPV"
    SPECIAL = "SPECIAL"

class RegistrationStatus(str, enum.Enum):
    REGISTERED = "REGISTERED"
    REJECTED = "REJECTED"
    RD_REVIEW = "RD_REVIEW"  # Regional Director Review

class DocumentType(str, enum.Enum):
    PHOTO = "photo"
    ID_PROOF = "id_proof"
    MC1 = "mc1"
    MC2 = "mc2"
    OTHER = "other"

# SQLAlchemy Models

class Registration(Base):
    """Registration model for registration schema"""
    __tablename__ = "registrations"
    # Only use schema for PostgreSQL, not SQLite
    __table_args__ = {"schema": config.db.schema} if config.db.db_type != "sqlite" else {}
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign keys to other services
    candidate_id = Column(UUID(as_uuid=True), nullable=False, index=True)  # FK to Identity
    booking_id = Column(UUID(as_uuid=True), nullable=False, index=True)    # FK to Calendar
    receipt_no = Column(String(20), nullable=False, index=True)            # FK to Receipt
    
    # Candidate information from JWT claims
    full_name = Column(String(255), nullable=False)
    dob = Column(DateTime(timezone=True), nullable=False)  # Date of birth for age validation
    address = Column(Text, nullable=False)
    phone = Column(String(20), nullable=False)
    
    # Registration-specific fields
    vehicle_weight_kg = Column(Integer, nullable=False)
    vehicle_category = Column(String(10), nullable=False)  # Store as string for flexibility
    
    # Document storage (JSONB array)
    docs = Column(JSONB, nullable=False, default=list)
    
    # Registration status
    status = Column(String(20), nullable=False, default=RegistrationStatus.REGISTERED.value)
    
    # Override flags for special cases
    manager_override = Column(Boolean, default=False, nullable=False)
    override_reason = Column(Text, nullable=True)
    override_by = Column(String(255), nullable=True)  # Who authorized the override
    
    # Audit fields
    registered_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    @property
    def age_in_years(self) -> float:
        """Calculate current age in years (with decimals)"""
        now = datetime.now(timezone.utc)
        birth_date = self.dob.replace(tzinfo=timezone.utc) if self.dob.tzinfo is None else self.dob
        
        # Calculate age using relativedelta for accuracy
        age_delta = relativedelta(now, birth_date)
        return age_delta.years + (age_delta.months / 12.0) + (age_delta.days / 365.0)
    
    @property
    def required_medical_certificate(self) -> Optional[str]:
        """Determine required medical certificate based on vehicle category"""
        if self.vehicle_category == VehicleCategory.B.value:
            return None  # No medical certificate required for Class B
        elif self.vehicle_category in [VehicleCategory.C.value, VehicleCategory.PPV.value]:
            return DocumentType.MC2.value
        elif self.vehicle_category == VehicleCategory.SPECIAL.value:
            # For provisional (special case), MC1 is required
            return DocumentType.MC1.value
        return None
    
    def validate_age_requirements(self) -> tuple[bool, str]:
        """Validate age requirements for the selected vehicle category"""
        age = self.age_in_years
        
        if self.vehicle_category == VehicleCategory.B.value:
            if age < config.registration.min_age_class_b:
                return False, f"Minimum age for Class B is {config.registration.min_age_class_b} years. Current age: {age:.1f} years"
        
        elif self.vehicle_category in [VehicleCategory.C.value, VehicleCategory.PPV.value]:
            # For Class C and PPV, check weight and age
            if self.vehicle_weight_kg > config.registration.weight_threshold_class_c:
                if age < config.registration.min_age_class_c_ppv and not self.manager_override:
                    return False, f"Minimum age for Class C/PPV (>7000kg) is {config.registration.min_age_class_c_ppv} years. Current age: {age:.1f} years"
        
        elif self.vehicle_category == VehicleCategory.SPECIAL.value:
            # Provisional license
            if age < config.registration.min_age_provisional:
                return False, f"Minimum age for Provisional is {config.registration.min_age_provisional} years. Current age: {age:.1f} years"
        
        return True, "Age requirements satisfied"
    
    def validate_medical_certificates(self) -> tuple[bool, str]:
        """Validate medical certificate requirements"""
        required_mc = self.required_medical_certificate
        
        if not required_mc:
            return True, "No medical certificate required"
        
        # Check if required medical certificate is present in docs
        docs_list = self.docs if isinstance(self.docs, list) else []
        mc_docs = [doc for doc in docs_list if doc.get("type") == required_mc]
        
        if not mc_docs:
            return False, f"Missing required medical certificate: {required_mc.upper()}"
        
        # Additional validation could include expiration date checking
        return True, "Medical certificate requirements satisfied"

class Document(Base):
    """Document metadata model for registration schema"""
    __tablename__ = "documents"
    # Only use schema for PostgreSQL, not SQLite
    __table_args__ = {"schema": config.db.schema} if config.db.db_type != "sqlite" else {}
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    registration_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Document metadata
    document_type = Column(String(20), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_size_bytes = Column(Integer, nullable=False)
    mime_type = Column(String(100), nullable=False)
    
    # Storage information
    storage_url = Column(String(500), nullable=False)  # S3 URL or file path
    storage_provider = Column(String(50), default="local", nullable=False)
    
    # Processing status
    is_processed = Column(Boolean, default=False, nullable=False)
    processing_notes = Column(Text, nullable=True)
    
    # Audit fields
    uploaded_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

# Pydantic Models for API

class DocumentUpload(BaseModel):
    """Schema for document upload in registration request"""
    type: DocumentType = Field(..., description="Type of document")
    filename: str = Field(..., min_length=1, max_length=255, description="Original filename")
    content: str = Field(..., description="Base64 encoded file content")
    mime_type: str = Field(..., description="MIME type of the file")

class RegistrationRequest(BaseModel):
    """Schema for registration creation request"""
    booking_id: uuid.UUID = Field(..., description="Booking ID from Calendar service")
    receipt_no: str = Field(..., min_length=8, max_length=20, description="Receipt number from Receipt service")
    vehicle_weight_kg: int = Field(..., gt=0, le=50000, description="Vehicle weight in kg")
    vehicle_category: VehicleCategory = Field(..., description="Vehicle category")
    docs: List[DocumentUpload] = Field(..., min_items=2, description="Document uploads (minimum: photo + id_proof)")
    
    # Manager override fields (optional)
    manager_override: Optional[bool] = Field(default=False, description="Manager override for age requirements")
    override_reason: Optional[str] = Field(None, max_length=500, description="Reason for override")
    override_by: Optional[str] = Field(None, max_length=255, description="Manager authorizing override")
    
    @validator('docs')
    def validate_documents(cls, v):
        """Validate document requirements"""
        if not v:
            raise ValueError("At least 2 documents are required (photo and id_proof)")
        
        doc_types = [doc.type for doc in v]
        
        # Check for required documents
        if DocumentType.PHOTO not in doc_types:
            raise ValueError("Photo document is required")
        if DocumentType.ID_PROOF not in doc_types:
            raise ValueError("ID proof document is required")
        
        # Validate file sizes and formats
        for doc in v:
            # Check file size (assuming base64 content)
            estimated_size = (len(doc.content) * 3) // 4  # Base64 to bytes approximation
            if estimated_size > config.registration.max_document_size:
                raise ValueError(f"Document {doc.filename} exceeds maximum size of {config.registration.max_document_size // (1024*1024)}MB")
            
            # Validate format based on document type
            allowed_formats = []
            if doc.type == DocumentType.PHOTO:
                allowed_formats = config.registration.allowed_photo_formats
            elif doc.type == DocumentType.ID_PROOF:
                allowed_formats = config.registration.allowed_id_proof_formats
            elif doc.type in [DocumentType.MC1, DocumentType.MC2]:
                allowed_formats = config.registration.allowed_medical_formats
            elif doc.type == DocumentType.OTHER:
                allowed_formats = config.registration.allowed_other_formats
            
            # Extract file extension from filename or mime_type
            file_ext = doc.filename.split('.')[-1].lower() if '.' in doc.filename else ""
            mime_ext = doc.mime_type.split('/')[-1].lower() if '/' in doc.mime_type else ""
            
            if file_ext not in allowed_formats and mime_ext not in allowed_formats:
                raise ValueError(f"Document type {doc.type.value} does not support format {file_ext or mime_ext}. Allowed: {allowed_formats}")
        
        return v

class RegistrationResponse(BaseModel):
    """Schema for registration response"""
    id: uuid.UUID
    candidate_id: uuid.UUID
    booking_id: uuid.UUID
    receipt_no: str
    full_name: str
    dob: datetime
    address: str
    phone: str
    vehicle_weight_kg: int
    vehicle_category: str
    status: str
    age_in_years: float
    required_medical_certificate: Optional[str]
    manager_override: bool
    override_reason: Optional[str]
    docs: List[Dict[str, Any]]
    registered_at: datetime
    created_at: datetime
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }

class RegistrationCreateResponse(BaseModel):
    """Response schema for registration creation"""
    success: bool
    registration: Optional[RegistrationResponse] = None
    message: str
    validation_errors: Optional[List[str]] = None
    driver_record_id: Optional[uuid.UUID] = None  # For event publishing

class ErrorResponse(BaseModel):
    """Standard error response schema"""
    success: bool = False
    error: str
    detail: Optional[str] = None
    code: Optional[str] = None
    validation_errors: Optional[List[str]] = None

# Event schemas for publishing

class RegistrationCompletedEvent(BaseModel):
    """Event schema for registration completion"""
    driver_record_id: uuid.UUID
    candidate_id: uuid.UUID
    booking_id: uuid.UUID
    status: str
    timestamp: datetime
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }