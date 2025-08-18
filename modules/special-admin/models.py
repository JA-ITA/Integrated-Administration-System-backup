"""
SQLAlchemy models for ITADIAS Special Admin Microservice
PostgreSQL schema: config
"""
import uuid
import json
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy import Column, String, DateTime, Boolean, Integer, Text, Numeric, JSON
from sqlalchemy.dialects.postgresql import UUID
from pydantic import BaseModel, Field, validator
import enum
from database import Base
from config import config

# Enums

class TestTypeStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    DRAFT = "draft"

class TemplateStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    DRAFT = "draft"

class ModuleStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"

# SQLAlchemy Models

class SpecialTestType(Base):
    """Special test types table in config schema"""
    __tablename__ = "special_test_types"
    __table_args__ = {"schema": config.db.schema}
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    fee = Column(Numeric(10, 2), nullable=False)  # Fee in currency units
    validity_months = Column(Integer, nullable=False)  # Certificate validity period
    required_docs = Column(JSON, nullable=False, default=list)  # JSONB array of required document types
    status = Column(String(20), default=TestTypeStatus.ACTIVE, nullable=False)
    pass_percentage = Column(Integer, default=75, nullable=False)  # Pass percentage
    time_limit_minutes = Column(Integer, default=25, nullable=False)  # Test time limit
    questions_count = Column(Integer, default=20, nullable=False)  # Number of questions
    created_by = Column(String(255), nullable=False)  # Admin user who created it
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

class QuestionModule(Base):
    """Question modules table in config schema"""
    __tablename__ = "question_modules"
    __table_args__ = {"schema": config.db.schema}
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String(50), nullable=False, unique=True)  # e.g., SPECIAL-TEST, HAZMAT, DANGEROUS-GOODS
    description = Column(Text, nullable=False)
    category = Column(String(100), nullable=True)  # Category grouping
    status = Column(String(20), default=ModuleStatus.ACTIVE, nullable=False)
    question_count = Column(Integer, default=0, nullable=False)  # Current question count in this module
    created_by = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

class CertificateTemplate(Base):
    """Certificate templates table in config schema"""
    __tablename__ = "certificate_templates"
    __table_args__ = {"schema": config.db.schema}
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    type = Column(String(100), nullable=False)  # Template type/category
    description = Column(Text, nullable=True)
    hbs_content = Column(Text, nullable=False)  # Handlebars template content
    css_content = Column(Text, nullable=True)  # CSS styles
    json_config = Column(JSON, nullable=False, default=dict)  # Designer configuration
    preview_html = Column(Text, nullable=True)  # Generated preview HTML
    status = Column(String(20), default=TemplateStatus.DRAFT, nullable=False)
    is_default = Column(Boolean, default=False, nullable=False)  # Is this the default template for its type
    created_by = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

# Pydantic Models for API

class SpecialTestTypeBase(BaseModel):
    """Base special test type schema"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    fee: float = Field(..., ge=0, description="Fee amount")
    validity_months: int = Field(..., ge=1, le=120, description="Certificate validity in months")
    required_docs: List[str] = Field(default=[], description="Required document types")
    pass_percentage: int = Field(default=75, ge=50, le=100, description="Pass percentage")
    time_limit_minutes: int = Field(default=25, ge=5, le=180, description="Test time limit")
    questions_count: int = Field(default=20, ge=5, le=100, description="Number of questions")
    status: TestTypeStatus = TestTypeStatus.ACTIVE

class SpecialTestTypeCreate(SpecialTestTypeBase):
    """Schema for creating a special test type"""
    created_by: str = Field(..., min_length=1, max_length=255)

class SpecialTestTypeUpdate(BaseModel):
    """Schema for updating a special test type"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    fee: Optional[float] = Field(None, ge=0)
    validity_months: Optional[int] = Field(None, ge=1, le=120)
    required_docs: Optional[List[str]] = None
    pass_percentage: Optional[int] = Field(None, ge=50, le=100)
    time_limit_minutes: Optional[int] = Field(None, ge=5, le=180)
    questions_count: Optional[int] = Field(None, ge=5, le=100)
    status: Optional[TestTypeStatus] = None

class SpecialTestTypeResponse(SpecialTestTypeBase):
    """Schema for special test type response"""
    id: uuid.UUID
    created_by: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class QuestionModuleBase(BaseModel):
    """Base question module schema"""
    code: str = Field(..., min_length=1, max_length=50, description="Module code (e.g., SPECIAL-TEST)")
    description: str = Field(..., min_length=1, description="Module description")
    category: Optional[str] = Field(None, max_length=100, description="Category grouping")
    status: ModuleStatus = ModuleStatus.ACTIVE

class QuestionModuleCreate(QuestionModuleBase):
    """Schema for creating a question module"""
    created_by: str = Field(..., min_length=1, max_length=255)

class QuestionModuleUpdate(BaseModel):
    """Schema for updating a question module"""
    description: Optional[str] = Field(None, min_length=1)
    category: Optional[str] = Field(None, max_length=100)
    status: Optional[ModuleStatus] = None

class QuestionModuleResponse(QuestionModuleBase):
    """Schema for question module response"""
    id: uuid.UUID
    question_count: int
    created_by: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class CertificateTemplateBase(BaseModel):
    """Base certificate template schema"""
    name: str = Field(..., min_length=1, max_length=255)
    type: str = Field(..., min_length=1, max_length=100, description="Template type")
    description: Optional[str] = None
    hbs_content: str = Field(..., min_length=1, description="Handlebars template content")
    css_content: Optional[str] = Field(None, description="CSS styles")
    json_config: Dict[str, Any] = Field(default={}, description="Designer configuration")
    status: TemplateStatus = TemplateStatus.DRAFT
    is_default: bool = False

class CertificateTemplateCreate(CertificateTemplateBase):
    """Schema for creating a certificate template"""
    created_by: str = Field(..., min_length=1, max_length=255)

class CertificateTemplateUpdate(BaseModel):
    """Schema for updating a certificate template"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    hbs_content: Optional[str] = Field(None, min_length=1)
    css_content: Optional[str] = None
    json_config: Optional[Dict[str, Any]] = None
    status: Optional[TemplateStatus] = None
    is_default: Optional[bool] = None

class CertificateTemplateResponse(CertificateTemplateBase):
    """Schema for certificate template response"""
    id: uuid.UUID
    preview_html: Optional[str]
    created_by: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class TemplatePreviewRequest(BaseModel):
    """Schema for template preview request"""
    hbs_content: str = Field(..., min_length=1)
    css_content: Optional[str] = None
    json_config: Dict[str, Any] = Field(default={})
    sample_data: Optional[Dict[str, Any]] = Field(default={}, description="Sample data for preview")

class TemplatePreviewResponse(BaseModel):
    """Schema for template preview response"""
    preview_html: str
    compiled_template: str
    status: str = "success"

class QuestionUploadRequest(BaseModel):
    """Schema for question upload request"""
    module_code: str = Field(..., min_length=1, max_length=50)
    csv_data: str = Field(..., min_length=1, description="Base64 encoded CSV data or CSV text")
    created_by: str = Field(..., min_length=1, max_length=255)

class QuestionUploadResponse(BaseModel):
    """Schema for question upload response"""
    success: bool
    module_code: str
    questions_processed: int
    questions_created: int
    questions_updated: int
    errors: List[str] = []
    message: str

class ErrorResponse(BaseModel):
    """Standard error response schema"""
    error: str
    detail: Optional[str] = None
    code: Optional[str] = None