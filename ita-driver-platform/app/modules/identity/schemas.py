"""
Identity Module Pydantic Schemas
Data models for request/response validation and serialization.
"""

from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, validator
from enum import Enum


class UserType(str, Enum):
    """User type enumeration."""
    DRIVER = "driver"
    EXAMINER = "examiner"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"


class UserStatus(str, Enum):
    """User status enumeration."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING_VERIFICATION = "pending_verification"


# Request Schemas
class UserCreate(BaseModel):
    """Schema for user creation."""
    email: EmailStr = Field(..., description="User's email address")
    password: str = Field(..., min_length=8, description="User's password")
    first_name: str = Field(..., min_length=1, max_length=50, description="User's first name")
    last_name: str = Field(..., min_length=1, max_length=50, description="User's last name")
    phone: str = Field(..., description="User's phone number")
    user_type: UserType = Field(default=UserType.DRIVER, description="Type of user")
    
    @validator("password")
    def validate_password(cls, v):
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        
        if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in v):
            raise ValueError("Password must contain at least one special character")
        
        return v
    
    @validator("phone")
    def validate_phone(cls, v):
        """Validate phone number format."""
        import re
        phone_pattern = r'^[\+]?[1-9][\d]{0,15}$'
        if not re.match(phone_pattern, v.replace(" ", "").replace("-", "")):
            raise ValueError("Invalid phone number format")
        return v


class UserUpdate(BaseModel):
    """Schema for user profile updates."""
    first_name: Optional[str] = Field(None, min_length=1, max_length=50)
    last_name: Optional[str] = Field(None, min_length=1, max_length=50)
    phone: Optional[str] = None
    
    @validator("phone")
    def validate_phone(cls, v):
        """Validate phone number format."""
        if v is None:
            return v
        import re
        phone_pattern = r'^[\+]?[1-9][\d]{0,15}$'
        if not re.match(phone_pattern, v.replace(" ", "").replace("-", "")):
            raise ValueError("Invalid phone number format")
        return v


class LoginRequest(BaseModel):
    """Schema for user login."""
    email: EmailStr = Field(..., description="User's email address")
    password: str = Field(..., description="User's password")


class TokenRefreshRequest(BaseModel):
    """Schema for token refresh."""
    refresh_token: str = Field(..., description="Valid refresh token")


class PasswordChangeRequest(BaseModel):
    """Schema for password change."""
    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=8, description="New password")
    
    @validator("new_password")
    def validate_password(cls, v):
        """Validate password strength."""
        return UserCreate.validate_password(v)


class PasswordResetRequest(BaseModel):
    """Schema for password reset request."""
    email: EmailStr = Field(..., description="User's email address")


class PasswordResetConfirm(BaseModel):
    """Schema for password reset confirmation."""
    reset_token: str = Field(..., description="Password reset token")
    new_password: str = Field(..., min_length=8, description="New password")
    
    @validator("new_password")
    def validate_password(cls, v):
        """Validate password strength."""
        return UserCreate.validate_password(v)


# Response Schemas
class UserResponse(BaseModel):
    """Schema for user response."""
    id: str = Field(..., description="User's unique identifier")
    email: str = Field(..., description="User's email address")
    first_name: str = Field(..., description="User's first name")
    last_name: str = Field(..., description="User's last name")
    phone: str = Field(..., description="User's phone number")
    user_type: UserType = Field(..., description="Type of user")
    status: UserStatus = Field(..., description="User's account status")
    is_active: bool = Field(..., description="Whether user account is active")
    created_at: datetime = Field(..., description="Account creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    last_login: Optional[datetime] = Field(None, description="Last login timestamp")
    roles: List[str] = Field(default=[], description="User's assigned roles")
    permissions: List[str] = Field(default=[], description="User's effective permissions")
    
    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    """Schema for token information."""
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration time in seconds")


class LoginResponse(BaseModel):
    """Schema for login response."""
    user: UserResponse = Field(..., description="User information")
    tokens: TokenResponse = Field(..., description="Authentication tokens")
    message: str = Field(default="Login successful", description="Response message")


class RoleResponse(BaseModel):
    """Schema for role information."""
    id: str = Field(..., description="Role's unique identifier")
    name: str = Field(..., description="Role name")
    description: str = Field(..., description="Role description")
    permissions: List[str] = Field(..., description="Role permissions")
    created_at: datetime = Field(..., description="Role creation timestamp")
    
    class Config:
        from_attributes = True


class PermissionResponse(BaseModel):
    """Schema for permission information."""
    id: str = Field(..., description="Permission's unique identifier")
    name: str = Field(..., description="Permission name")
    description: str = Field(..., description="Permission description")
    resource: str = Field(..., description="Resource this permission applies to")
    action: str = Field(..., description="Action this permission allows")
    
    class Config:
        from_attributes = True


# Internal Schemas
class TokenPayload(BaseModel):
    """Schema for JWT token payload."""
    user_id: str = Field(..., description="User's unique identifier")
    email: str = Field(..., description="User's email address")
    user_type: UserType = Field(..., description="Type of user")
    roles: List[str] = Field(default=[], description="User's roles")
    permissions: List[str] = Field(default=[], description="User's permissions")
    exp: int = Field(..., description="Token expiration timestamp")
    iat: int = Field(..., description="Token issued at timestamp")
    type: str = Field(..., description="Token type (access or refresh)")


class UserInDB(BaseModel):
    """Schema for user as stored in database."""
    id: str
    email: str
    hashed_password: str
    first_name: str
    last_name: str
    phone: str
    user_type: UserType
    status: UserStatus
    is_active: bool
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime] = None
    password_reset_token: Optional[str] = None
    password_reset_expires: Optional[datetime] = None
    email_verification_token: Optional[str] = None
    email_verified: bool = False
    failed_login_attempts: int = 0
    locked_until: Optional[datetime] = None
    
    class Config:
        from_attributes = True