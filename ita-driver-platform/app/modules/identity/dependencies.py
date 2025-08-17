"""
Identity Module Dependencies
FastAPI dependencies for authentication and authorization.
"""

from typing import List, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from jose import JWTError, jwt

from core.config import settings
from core.database import get_db
from core.exceptions import AuthenticationError, AuthorizationError
from .service import IdentityService
from .models import User

security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Get current authenticated user from JWT token.
    
    Args:
        credentials: HTTP Bearer credentials
        db: Database session
        
    Returns:
        Current authenticated user
        
    Raises:
        HTTPException: If authentication fails
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        # Decode JWT token
        payload = jwt.decode(
            credentials.credentials,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        
        # Validate token type
        if payload.get("type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Get user ID from token
        user_id = payload.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Fetch user from database
        service = IdentityService(db)
        user = await service.get_user_by_id(user_id)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account is deactivated",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if user.status == "suspended":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account is suspended",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return user
        
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Get current active user (additional check for active status).
    
    Args:
        current_user: Current user from get_current_user
        
    Returns:
        Current active user
        
    Raises:
        HTTPException: If user is not active
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user account"
        )
    
    return current_user


def require_user_type(allowed_types: List[str]):
    """
    Dependency factory to require specific user types.
    
    Args:
        allowed_types: List of allowed user types
        
    Returns:
        FastAPI dependency function
    """
    def user_type_dependency(
        current_user: User = Depends(get_current_active_user)
    ) -> User:
        if current_user.user_type not in allowed_types:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required user types: {', '.join(allowed_types)}"
            )
        return current_user
    
    return user_type_dependency


def require_permissions(required_permissions: List[str]):
    """
    Dependency factory to require specific permissions.
    
    Args:
        required_permissions: List of required permission names
        
    Returns:
        FastAPI dependency function
    """
    async def permission_dependency(
        current_user: User = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db)
    ) -> User:
        # Get user permissions
        service = IdentityService(db)
        user_permissions = await service._get_user_permissions(current_user)
        
        # Check if user has all required permissions
        missing_permissions = set(required_permissions) - set(user_permissions)
        
        if missing_permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Missing permissions: {', '.join(missing_permissions)}"
            )
        
        return current_user
    
    return permission_dependency


def require_roles(required_roles: List[str]):
    """
    Dependency factory to require specific roles.
    
    Args:
        required_roles: List of required role names
        
    Returns:
        FastAPI dependency function
    """
    def role_dependency(
        current_user: User = Depends(get_current_active_user)
    ) -> User:
        user_roles = [ur.role.name for ur in current_user.roles]
        
        # Check if user has any of the required roles
        if not any(role in user_roles for role in required_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {', '.join(required_roles)}"
            )
        
        return current_user
    
    return role_dependency


# Predefined dependencies for common user types
require_driver = require_user_type(["driver"])
require_examiner = require_user_type(["examiner", "admin", "super_admin"])
require_admin = require_user_type(["admin", "super_admin"])
require_super_admin = require_user_type(["super_admin"])


# Predefined dependencies for common permission checks
require_user_management = require_permissions(["manage_users", "view_users"])
require_role_management = require_permissions(["manage_roles"])
require_system_admin = require_permissions(["system_admin"])


async def get_optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """
    Get current user if authentication is provided, otherwise return None.
    Useful for endpoints that work with or without authentication.
    
    Args:
        credentials: HTTP Bearer credentials (optional)
        db: Database session
        
    Returns:
        Current user if authenticated, None otherwise
    """
    if not credentials:
        return None
    
    try:
        return await get_current_user(credentials, db)
    except HTTPException:
        return None


def require_self_or_permission(permission: str):
    """
    Dependency factory that allows access if user is accessing their own data
    or has specific permission.
    
    Args:
        permission: Required permission name for accessing other users' data
        
    Returns:
        FastAPI dependency function
    """
    async def self_or_permission_dependency(
        user_id: str,
        current_user: User = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db)
    ) -> User:
        # Allow access to own data
        if current_user.id == user_id:
            return current_user
        
        # Check for required permission to access other users' data
        service = IdentityService(db)
        user_permissions = await service._get_user_permissions(current_user)
        
        if permission not in user_permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. You can only access your own data or need specific permission."
            )
        
        return current_user
    
    return self_or_permission_dependency


class RateLimiter:
    """Simple rate limiter for authentication endpoints."""
    
    def __init__(self, max_requests: int = 5, window_seconds: int = 300):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.attempts = {}  # In production, use Redis
    
    async def __call__(self, request):
        """Rate limiting logic."""
        import time
        
        client_ip = request.client.host if request.client else "unknown"
        current_time = time.time()
        
        # Clean old entries
        cutoff_time = current_time - self.window_seconds
        self.attempts = {
            ip: timestamps for ip, timestamps in self.attempts.items()
            if any(ts > cutoff_time for ts in timestamps)
        }
        
        # Check current client
        if client_ip not in self.attempts:
            self.attempts[client_ip] = []
        
        # Filter recent attempts
        self.attempts[client_ip] = [
            ts for ts in self.attempts[client_ip] 
            if ts > cutoff_time
        ]
        
        # Check rate limit
        if len(self.attempts[client_ip]) >= self.max_requests:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Too many authentication attempts. Try again in {self.window_seconds // 60} minutes."
            )
        
        # Record current attempt
        self.attempts[client_ip].append(current_time)
        
        return True


# Create rate limiter instance
auth_rate_limiter = RateLimiter(max_requests=5, window_seconds=300)  # 5 attempts per 5 minutes