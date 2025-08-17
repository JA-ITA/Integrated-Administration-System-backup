"""
SQLAlchemy models for ITADIAS Receipt Microservice
"""
import uuid
import re
from datetime import datetime, timezone, timedelta
from typing import Optional
from sqlalchemy import Column, String, DateTime, Boolean, Numeric, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from pydantic import BaseModel, Field, validator
import enum
from database import Base
from config import config

# SQLAlchemy Models

class Receipt(Base):
    """Receipt model for receipt schema"""
    __tablename__ = "receipts"
    __table_args__ = (
        # Unique constraint: one receipt can only be used once
        UniqueConstraint('receipt_no', name='unique_receipt_no'),
        {"schema": config.db.schema}
    )
    
    receipt_no = Column(String(20), primary_key=True)  # Alphanumeric 8-20 chars
    issue_date = Column(DateTime(timezone=True), nullable=False)
    location = Column(String(100), nullable=False)  # TAJ office or "TAJ Online"
    amount = Column(Numeric(10, 2), nullable=False)  # Informational only
    used_flag = Column(Boolean, default=False, nullable=False, index=True)
    
    # Audit fields
    validated_at = Column(DateTime(timezone=True), nullable=True)  # When validation occurred
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    @property
    def is_valid_for_use(self) -> bool:
        """Check if receipt is valid for use"""
        # Must not be already used
        if self.used_flag:
            return False
            
        # Must be within valid date range (≤ 365 days old)
        now = datetime.now(timezone.utc)
        max_age = timedelta(days=config.receipt.max_age_days)
        
        if self.issue_date < (now - max_age):
            return False
            
        return True
    
    def mark_as_used(self):
        """Mark receipt as used"""
        self.used_flag = True
        self.validated_at = datetime.now(timezone.utc)

# Pydantic Models for API

class ReceiptValidationRequest(BaseModel):
    """Schema for receipt validation request"""
    receipt_no: str = Field(..., min_length=8, max_length=20, description="Receipt number (8-20 alphanumeric characters)")
    issue_date: datetime = Field(..., description="Date when receipt was issued")
    location: str = Field(..., min_length=1, max_length=100, description="TAJ office location or 'TAJ Online'")
    amount: float = Field(..., ge=0, description="Receipt amount (informational)")
    
    @validator('receipt_no')
    def validate_receipt_no(cls, v):
        """Validate receipt number format"""
        pattern = config.receipt.receipt_no_pattern
        if not re.match(pattern, v):
            raise ValueError(f"Receipt number must match pattern: {pattern}")
        return v.upper()  # Normalize to uppercase
    
    @validator('issue_date')
    def validate_issue_date(cls, v):
        """Validate issue date is not too old"""
        now = datetime.now(timezone.utc)
        max_age = timedelta(days=config.receipt.max_age_days)
        
        if v < (now - max_age):
            raise ValueError(f"Receipt is too old. Maximum age is {config.receipt.max_age_days} days")
        
        if v > now:
            raise ValueError("Receipt issue date cannot be in the future")
            
        return v
    
    @validator('location')
    def validate_location(cls, v):
        """Validate location is in allowed list"""
        if v not in config.receipt.valid_locations:
            raise ValueError(f"Invalid location. Must be one of: {', '.join(config.receipt.valid_locations)}")
        return v
    
    @validator('amount')
    def validate_amount(cls, v):
        """Validate amount is reasonable"""
        if v < 0:
            raise ValueError("Amount cannot be negative")
        if v > 1000000:  # Reasonable upper limit
            raise ValueError("Amount exceeds maximum limit")
        return round(v, 2)  # Round to 2 decimal places

class ReceiptResponse(BaseModel):
    """Schema for receipt response"""
    receipt_no: str
    issue_date: datetime
    location: str
    amount: float
    used_flag: bool
    validated_at: Optional[datetime] = None
    created_at: datetime
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }

class ReceiptValidationResponse(BaseModel):
    """Response schema for receipt validation"""
    success: bool
    receipt_no: str
    message: str
    receipt: Optional[ReceiptResponse] = None
    validation_timestamp: datetime
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }

class ErrorResponse(BaseModel):
    """Standard error response schema"""
    success: bool = False
    error: str
    detail: Optional[str] = None
    code: Optional[str] = None

# Utility functions
def generate_validation_message(receipt: Receipt) -> str:
    """Generate appropriate validation message"""
    return f"Receipt {receipt.receipt_no} validated successfully for amount {receipt.amount} from {receipt.location}"