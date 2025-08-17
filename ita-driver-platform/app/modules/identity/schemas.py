"""
Identity Module Pydantic Schemas - Enhanced for Candidate Management
Data models for candidate registration, OTP verification, and API responses.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, date
from pydantic import BaseModel, EmailStr, Field, validator, root_validator
from enum import Enum
import re


class CandidateStatus(str, Enum):
    """Candidate status enumeration."""
    PENDING_VERIFICATION = "pending_verification"
    EMAIL_VERIFIED = "email_verified"
    PHONE_VERIFIED = "phone_verified"
    FULLY_VERIFIED = "fully_verified"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    INACTIVE = "inactive"


class OTPType(str, Enum):
    """OTP type enumeration."""
    EMAIL = "email"
    PHONE = "phone"


class DocumentType(str, Enum):
    """Document type enumeration."""
    NATIONAL_ID = "national_id"
    PASSPORT = "passport"
    BIRTH_CERTIFICATE = "birth_certificate"
    PROOF_OF_ADDRESS = "proof_of_address"
    MEDICAL_CERTIFICATE = "medical_certificate"


# Request Schemas
class CandidateCreateRequest(BaseModel):
    """Schema for candidate creation request."""
    
    # Basic information
    email: EmailStr = Field(..., description="Candidate's email address")
    first_name: str = Field(..., min_length=1, max_length=50, description="Candidate's first name")
    last_name: str = Field(..., min_length=1, max_length=50, description="Candidate's last name")
    phone: str = Field(..., description="Candidate's phone number")
    date_of_birth: Optional[date] = Field(None, description="Candidate's date of birth")
    
    # Government identification
    national_id: Optional[str] = Field(None, min_length=5, max_length=50, description="National ID number")
    passport_number: Optional[str] = Field(None, min_length=5, max_length=20, description="Passport number")
    
    # Address information
    street_address: Optional[str] = Field(None, max_length=200, description="Street address")
    city: Optional[str] = Field(None, max_length=50, description="City")
    postal_code: Optional[str] = Field(None, max_length=10, description="Postal code")
    country: str = Field(default="Bermuda", description="Country")
    
    # Preferences
    preferred_language: str = Field(default="en", description="Preferred language code")
    timezone: str = Field(default="Atlantic/Bermuda", description="Preferred timezone")
    
    @validator("phone")
    def validate_phone(cls, v):
        """Validate phone number format for Bermuda."""
        # Remove spaces and dashes
        phone_clean = re.sub(r'[\s\-\(\)]', '', v)
        
        # Bermuda phone format: +1-441-XXX-XXXX or 441-XXX-XXXX or XXX-XXXX
        bermuda_patterns = [
            r'^\+1441\d{7}$',      # +1441XXXXXXX
            r'^1441\d{7}$',        # 1441XXXXXXX  
            r'^441\d{7}$',         # 441XXXXXXX
            r'^\d{7}$',            # XXXXXXX (local)
        ]
        
        if not any(re.match(pattern, phone_clean) for pattern in bermuda_patterns):
            raise ValueError("Invalid Bermuda phone number format")
        
        return v
    
    @validator("date_of_birth")
    def validate_date_of_birth(cls, v):
        """Validate date of birth (must be at least 16 years old)."""
        if v:
            today = date.today()
            age = today.year - v.year - ((today.month, today.day) < (v.month, v.day))
            if age < 16:
                raise ValueError("Candidate must be at least 16 years old")
            if age > 100:
                raise ValueError("Invalid date of birth")
        return v
    
    @validator("national_id")
    def validate_national_id(cls, v):
        """Validate Bermuda national ID format."""
        if v:
            # Remove spaces and dashes
            id_clean = re.sub(r'[\s\-]', '', v)
            # Basic format validation (customize based on actual Bermuda ID format)
            if not re.match(r'^[A-Z0-9]{8,12}$', id_clean.upper()):
                raise ValueError("Invalid national ID format")
        return v


class OTPVerificationRequest(BaseModel):
    """Schema for OTP verification request."""
    
    candidate_id: str = Field(..., description="Candidate ID")
    otp_type: OTPType = Field(..., description="Type of OTP (email or phone)")
    otp_code: str = Field(..., min_length=4, max_length=6, description="OTP code")
    
    @validator("otp_code")
    def validate_otp_code(cls, v):
        """Validate OTP code format."""
        if not v.isdigit():
            raise ValueError("OTP code must contain only digits")
        return v


class OTPResendRequest(BaseModel):
    """Schema for OTP resend request."""
    
    candidate_id: str = Field(..., description="Candidate ID")
    otp_type: OTPType = Field(..., description="Type of OTP to resend")


class PasswordSetRequest(BaseModel):
    """Schema for setting password after verification."""
    
    candidate_id: str = Field(..., description="Candidate ID")
    password: str = Field(..., min_length=8, description="New password")
    confirm_password: str = Field(..., description="Password confirmation")
    
    @root_validator
    def validate_passwords_match(cls, values):
        """Validate that passwords match."""
        password = values.get('password')
        confirm_password = values.get('confirm_password')
        
        if password != confirm_password:
            raise ValueError('Passwords do not match')
        return values
    
    @validator("password")
    def validate_password_strength(cls, v):
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        
        if not re.search(r'[A-Z]', v):
            raise ValueError("Password must contain at least one uppercase letter")
        
        if not re.search(r'[a-z]', v):
            raise ValueError("Password must contain at least one lowercase letter")
        
        if not re.search(r'\d', v):
            raise ValueError("Password must contain at least one digit")
        
        if not re.search(r'[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]', v):
            raise ValueError("Password must contain at least one special character")
        
        return v


# Response Schemas
class CandidateResponse(BaseModel):
    """Schema for candidate response."""
    
    id: str = Field(..., description="Candidate's unique identifier")
    email: str = Field(..., description="Candidate's email address")
    first_name: str = Field(..., description="Candidate's first name")
    last_name: str = Field(..., description="Candidate's last name")
    full_name: str = Field(..., description="Candidate's full name")
    phone: str = Field(..., description="Candidate's phone number")
    date_of_birth: Optional[date] = Field(None, description="Candidate's date of birth")
    
    # Government identification
    national_id: Optional[str] = Field(None, description="National ID number (masked)")
    passport_number: Optional[str] = Field(None, description="Passport number (masked)")
    
    # Address information
    street_address: Optional[str] = Field(None, description="Street address")
    city: Optional[str] = Field(None, description="City")
    postal_code: Optional[str] = Field(None, description="Postal code")
    country: str = Field(..., description="Country")
    
    # Status and verification
    status: CandidateStatus = Field(..., description="Candidate's current status")
    is_active: bool = Field(..., description="Whether candidate account is active")
    is_phone_verified: bool = Field(..., description="Whether phone is verified")
    is_email_verified: bool = Field(..., description="Whether email is verified")
    is_identity_verified: bool = Field(..., description="Whether identity is verified")
    is_fully_verified: bool = Field(..., description="Whether candidate is fully verified")
    
    # Profile completion
    profile_completion_percentage: int = Field(..., description="Profile completion percentage")
    
    # Timestamps
    created_at: datetime = Field(..., description="Account creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    verified_at: Optional[datetime] = Field(None, description="Verification completion timestamp")
    
    # Preferences
    preferred_language: str = Field(..., description="Preferred language code")
    timezone: str = Field(..., description="Preferred timezone")
    
    class Config:
        from_attributes = True


class CandidateCreateResponse(BaseModel):
    """Schema for candidate creation response."""
    
    candidate: CandidateResponse = Field(..., description="Created candidate information")
    otp_sent: Dict[str, bool] = Field(..., description="OTP sending status")
    message: str = Field(..., description="Response message")
    next_steps: List[str] = Field(..., description="Next steps for candidate")


class OTPVerificationResponse(BaseModel):
    """Schema for OTP verification response."""
    
    success: bool = Field(..., description="Whether verification was successful")
    message: str = Field(..., description="Verification result message")
    candidate_id: str = Field(..., description="Candidate ID")
    verification_type: OTPType = Field(..., description="Type of verification completed")
    next_step: Optional[str] = Field(None, description="Next step if verification successful")


class OTPStatusResponse(BaseModel):
    """Schema for OTP status response."""
    
    candidate_id: str = Field(..., description="Candidate ID")
    email_otp_status: str = Field(..., description="Email OTP status")
    phone_otp_status: str = Field(..., description="Phone OTP status")
    email_verified: bool = Field(..., description="Whether email is verified")
    phone_verified: bool = Field(..., description="Whether phone is verified")
    can_set_password: bool = Field(..., description="Whether candidate can set password")


class CandidateEventResponse(BaseModel):
    """Schema for candidate event response (for event publishing)."""
    
    event_id: str = Field(..., description="Event unique identifier")
    event_type: str = Field(..., description="Event type")
    candidate_id: str = Field(..., description="Candidate ID")
    event_data: Dict[str, Any] = Field(..., description="Event payload")
    timestamp: datetime = Field(..., description="Event timestamp")
    correlation_id: Optional[str] = Field(None, description="Correlation ID for tracing")


class DocumentUploadResponse(BaseModel):
    """Schema for document upload response."""
    
    document_id: str = Field(..., description="Document unique identifier")
    document_type: DocumentType = Field(..., description="Document type")
    file_name: str = Field(..., description="Original file name")
    upload_status: str = Field(..., description="Upload status")
    verification_required: bool = Field(..., description="Whether verification is required")


class ApiErrorResponse(BaseModel):
    """Schema for API error responses."""
    
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")
    correlation_id: Optional[str] = Field(None, description="Request correlation ID")


# Internal/Service Schemas
class CandidateEvent(BaseModel):
    """Schema for candidate events (internal use)."""
    
    event_type: str = Field(..., description="Event type")
    candidate_id: str = Field(..., description="Candidate ID")
    event_data: Dict[str, Any] = Field(..., description="Event payload")
    correlation_id: Optional[str] = Field(None, description="Correlation ID")
    source: str = Field(default="identity_service", description="Event source")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Event timestamp")


class OTPAttemptInfo(BaseModel):
    """Schema for OTP attempt information."""
    
    otp_type: OTPType
    recipient: str
    attempts_remaining: int
    expires_at: datetime
    can_resend: bool
    cooldown_expires: Optional[datetime] = None


class CandidateSearchFilters(BaseModel):
    """Schema for candidate search filters (admin use)."""
    
    status: Optional[CandidateStatus] = None
    is_verified: Optional[bool] = None
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    phone_verified: Optional[bool] = None
    email_verified: Optional[bool] = None
    city: Optional[str] = None
    country: Optional[str] = None


class CandidateListResponse(BaseModel):
    """Schema for candidate list response (admin use)."""
    
    candidates: List[CandidateResponse] = Field(..., description="List of candidates")
    total: int = Field(..., description="Total number of candidates")
    page: int = Field(..., description="Current page")
    limit: int = Field(..., description="Items per page")
    has_next: bool = Field(..., description="Whether there are more pages")