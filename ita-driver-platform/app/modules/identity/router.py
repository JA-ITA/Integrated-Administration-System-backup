"""
Identity Module Router - Authentication and User Management
Handles user registration, authentication, profile management, and role-based access control.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.exceptions import AuthenticationError, AuthorizationError
from .schemas import (
    UserCreate,
    UserResponse,
    UserUpdate,
    LoginRequest,
    LoginResponse,
    TokenRefreshRequest,
)
from .service import IdentityService
from .dependencies import get_current_user, require_permissions

router = APIRouter()
security = HTTPBearer()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Register a new user in the system.
    
    - **email**: Valid email address (will be username)
    - **password**: Strong password meeting requirements
    - **first_name**: User's first name
    - **last_name**: User's last name
    - **phone**: Contact phone number
    - **user_type**: Type of user (driver, examiner, admin)
    """
    service = IdentityService(db)
    
    try:
        user = await service.create_user(user_data)
        return UserResponse.from_orm(user)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/login", response_model=LoginResponse)
async def login(
    login_data: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Authenticate user and return access and refresh tokens.
    
    - **email**: User's email address
    - **password**: User's password
    """
    service = IdentityService(db)
    
    try:
        result = await service.authenticate_user(
            email=login_data.email,
            password=login_data.password
        )
        return result
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )


@router.post("/refresh", response_model=LoginResponse)
async def refresh_token(
    refresh_data: TokenRefreshRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Refresh access token using valid refresh token.
    
    - **refresh_token**: Valid refresh token
    """
    service = IdentityService(db)
    
    try:
        result = await service.refresh_access_token(refresh_data.refresh_token)
        return result
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )


@router.post("/logout")
async def logout(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Logout user and invalidate tokens.
    """
    service = IdentityService(db)
    
    token = credentials.credentials
    await service.logout_user(token)
    
    return {"message": "Successfully logged out"}


@router.get("/profile", response_model=UserResponse)
async def get_profile(
    current_user = Depends(get_current_user)
):
    """
    Get current user's profile information.
    """
    return UserResponse.from_orm(current_user)


@router.put("/profile", response_model=UserResponse)
async def update_profile(
    profile_data: UserUpdate,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update current user's profile information.
    
    - **first_name**: Updated first name
    - **last_name**: Updated last name
    - **phone**: Updated phone number
    """
    service = IdentityService(db)
    
    updated_user = await service.update_user(current_user.id, profile_data)
    return UserResponse.from_orm(updated_user)


@router.get("/users", response_model=List[UserResponse])
async def list_users(
    page: int = 1,
    limit: int = 20,
    user_type: Optional[str] = None,
    current_user = Depends(require_permissions(["view_users"])),
    db: AsyncSession = Depends(get_db)
):
    """
    List users with pagination and filtering.
    Requires 'view_users' permission.
    
    - **page**: Page number (default: 1)
    - **limit**: Items per page (default: 20, max: 100)
    - **user_type**: Filter by user type (optional)
    """
    if limit > 100:
        limit = 100
    
    service = IdentityService(db)
    users = await service.list_users(
        page=page,
        limit=limit,
        user_type=user_type
    )
    
    return [UserResponse.from_orm(user) for user in users]


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    current_user = Depends(require_permissions(["view_users"])),
    db: AsyncSession = Depends(get_db)
):
    """
    Get specific user by ID.
    Requires 'view_users' permission.
    """
    service = IdentityService(db)
    
    user = await service.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return UserResponse.from_orm(user)


@router.put("/users/{user_id}/status")
async def update_user_status(
    user_id: str,
    is_active: bool,
    current_user = Depends(require_permissions(["manage_users"])),
    db: AsyncSession = Depends(get_db)
):
    """
    Activate or deactivate a user account.
    Requires 'manage_users' permission.
    
    - **is_active**: True to activate, False to deactivate
    """
    service = IdentityService(db)
    
    user = await service.update_user_status(user_id, is_active)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return {
        "message": f"User {'activated' if is_active else 'deactivated'} successfully",
        "user_id": user_id,
        "is_active": is_active
    }


@router.post("/users/{user_id}/roles/{role_name}")
async def assign_role(
    user_id: str,
    role_name: str,
    current_user = Depends(require_permissions(["manage_roles"])),
    db: AsyncSession = Depends(get_db)
):
    """
    Assign role to user.
    Requires 'manage_roles' permission.
    """
    service = IdentityService(db)
    
    try:
        await service.assign_role_to_user(user_id, role_name)
        return {
            "message": f"Role '{role_name}' assigned to user successfully",
            "user_id": user_id,
            "role": role_name
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/users/{user_id}/roles/{role_name}")
async def remove_role(
    user_id: str,
    role_name: str,
    current_user = Depends(require_permissions(["manage_roles"])),
    db: AsyncSession = Depends(get_db)
):
    """
    Remove role from user.
    Requires 'manage_roles' permission.
    """
    service = IdentityService(db)
    
    try:
        await service.remove_role_from_user(user_id, role_name)
        return {
            "message": f"Role '{role_name}' removed from user successfully",
            "user_id": user_id,
            "role": role_name
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/change-password")
async def change_password(
    current_password: str,
    new_password: str,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Change user's password.
    
    - **current_password**: Current password for verification
    - **new_password**: New password meeting security requirements
    """
    service = IdentityService(db)
    
    try:
        await service.change_password(
            user_id=current_user.id,
            current_password=current_password,
            new_password=new_password
        )
        return {"message": "Password changed successfully"}
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/reset-password-request")
async def request_password_reset(
    email: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Request password reset for user.
    
    - **email**: User's email address
    """
    service = IdentityService(db)
    
    # Always return success to prevent email enumeration
    await service.request_password_reset(email)
    return {
        "message": "If the email exists, password reset instructions have been sent"
    }


@router.post("/reset-password")
async def reset_password(
    reset_token: str,
    new_password: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Reset password using reset token.
    
    - **reset_token**: Password reset token from email
    - **new_password**: New password meeting security requirements
    """
    service = IdentityService(db)
    
    try:
        await service.reset_password(reset_token, new_password)
        return {"message": "Password reset successfully"}
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )