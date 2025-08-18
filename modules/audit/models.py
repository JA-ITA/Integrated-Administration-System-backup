"""
SQLAlchemy models for ITADIAS Audit Microservice
"""
import uuid
import enum
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from sqlalchemy import Column, String, DateTime, Text, JSON
from sqlalchemy.dialects.postgresql import UUID, JSONB
from pydantic import BaseModel, Field, validator
from database import Base
from config import config

# Enums

class ActorRole(str, enum.Enum):
    DAO = "dao"
    MANAGER = "manager"
    RD = "rd"  # Regional Director

class AuditAction(str, enum.Enum):
    OVERRIDE = "OVERRIDE"
    REJECT = "REJECT"
    APPROVE = "APPROVE"
    UPDATE_SLOT = "UPDATE_SLOT"
    CANCEL_BOOKING = "CANCEL_BOOKING"
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"

class ResourceType(str, enum.Enum):
    RECEIPT = "RECEIPT"
    REGISTRATION = "REGISTRATION"
    TEST = "TEST"
    CERTIFICATE = "CERTIFICATE"
    BOOKING = "BOOKING"
    SLOT = "SLOT"

# SQLAlchemy Models

class AuditLog(Base):
    """Audit log model for audit schema"""
    __tablename__ = "audit_log"
    __table_args__ = {"schema": config.db.schema}
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Actor information
    actor_id = Column(UUID(as_uuid=True), nullable=False, index=True)  # User ID from identity service
    actor_role = Column(String(20), nullable=False, index=True)  # ActorRole enum
    
    # Action information
    action = Column(String(30), nullable=False, index=True)  # AuditAction enum
    resource_type = Column(String(30), nullable=False, index=True)  # ResourceType enum
    resource_id = Column(UUID(as_uuid=True), nullable=False, index=True)  # UUID/FK of the resource
    
    # Value changes
    old_val = Column(JSONB, nullable=True)  # Previous value
    new_val = Column(JSONB, nullable=True)  # New value
    
    # Reason and metadata
    reason = Column(Text, nullable=False)  # Mandatory reason for all actions
    
    # Audit fields
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

# Pydantic Models for API

class OverrideRequest(BaseModel):
    """Schema for override request"""
    resource_type: ResourceType = Field(..., description="Type of resource being overridden")
    resource_id: uuid.UUID = Field(..., description="ID of the resource being overridden")
    new_status: str = Field(..., min_length=1, max_length=50, description="New status for the resource")
    reason: str = Field(..., min_length=10, max_length=1000, description="Mandatory reason for override")
    
    # Optional fields for context
    old_status: Optional[str] = Field(None, description="Previous status (for audit trail)")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")

class AuditLogCreate(BaseModel):
    """Schema for creating audit log entries"""
    actor_id: uuid.UUID = Field(..., description="Actor user ID")
    actor_role: ActorRole = Field(..., description="Actor role")
    action: AuditAction = Field(..., description="Action performed")
    resource_type: ResourceType = Field(..., description="Resource type")
    resource_id: uuid.UUID = Field(..., description="Resource ID")
    old_val: Optional[Dict[str, Any]] = Field(None, description="Previous value")
    new_val: Optional[Dict[str, Any]] = Field(None, description="New value")
    reason: str = Field(..., min_length=1, max_length=1000, description="Reason for action")

class AuditLogResponse(BaseModel):
    """Schema for audit log response"""
    id: uuid.UUID
    actor_id: uuid.UUID
    actor_role: str
    action: str
    resource_type: str
    resource_id: uuid.UUID
    old_val: Optional[Dict[str, Any]]
    new_val: Optional[Dict[str, Any]]
    reason: str
    created_at: datetime
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }

class OverrideResponse(BaseModel):
    """Response schema for override request"""
    success: bool
    audit_id: Optional[uuid.UUID] = None
    message: str
    resource_type: str
    resource_id: uuid.UUID
    new_status: str

class ErrorResponse(BaseModel):
    """Standard error response schema"""
    success: bool = False
    error: str
    detail: Optional[str] = None
    code: Optional[str] = None

# Event schemas for publishing

class OverrideIssuedEvent(BaseModel):
    """Event schema for override issued"""
    audit_id: uuid.UUID
    actor_id: uuid.UUID
    actor_role: str
    resource_type: str
    resource_id: uuid.UUID
    old_status: Optional[str]
    new_status: str
    reason: str
    timestamp: datetime
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }

class JWTPayload(BaseModel):
    """JWT payload schema for validation"""
    user_id: uuid.UUID
    role: str
    exp: int
    iat: int
    
class RDAuthUser(BaseModel):
    """Authenticated RD user info"""
    user_id: uuid.UUID
    role: str