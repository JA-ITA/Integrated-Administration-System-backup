"""
Identity Module - User Authentication and Authorization

This module handles all aspects of user identity management including:
- User registration and profile management
- Authentication and session management
- Role-based access control (RBAC)
- Permission management
- Password security and reset functionality
- Multi-factor authentication support
- Audit logging for security events

The module follows a clean architecture pattern with:
- Models: SQLAlchemy database models
- Schemas: Pydantic models for API validation
- Service: Business logic layer
- Router: FastAPI route handlers
- Dependencies: Authentication and authorization dependencies
"""

from .models import User, Role, Permission, UserRole, UserSession, AuditLog
from .schemas import (
    UserCreate,
    UserUpdate,
    UserResponse,
    LoginRequest,
    LoginResponse,
    TokenResponse,
    UserType,
    UserStatus
)
from .service import IdentityService
from .dependencies import (
    get_current_user,
    get_current_active_user,
    require_user_type,
    require_permissions,
    require_roles,
    require_driver,
    require_examiner,
    require_admin,
    require_super_admin
)

__all__ = [
    # Models
    "User",
    "Role", 
    "Permission",
    "UserRole",
    "UserSession",
    "AuditLog",
    
    # Schemas
    "UserCreate",
    "UserUpdate", 
    "UserResponse",
    "LoginRequest",
    "LoginResponse",
    "TokenResponse",
    "UserType",
    "UserStatus",
    
    # Service
    "IdentityService",
    
    # Dependencies
    "get_current_user",
    "get_current_active_user",
    "require_user_type",
    "require_permissions",
    "require_roles",
    "require_driver",
    "require_examiner", 
    "require_admin",
    "require_super_admin",
]