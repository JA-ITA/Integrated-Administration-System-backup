"""
Identity Module Service Layer
Business logic for user management, authentication, and authorization.
"""

import uuid
import secrets
from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload
from passlib.context import CryptContext
from jose import JWTError, jwt

from core.config import settings
from core.exceptions import AuthenticationError, AuthorizationError, ValidationError
from core.logging_config import get_logger
from .models import User, Role, Permission, UserRole
from .schemas import UserCreate, UserUpdate, TokenPayload, LoginResponse, TokenResponse

logger = get_logger("identity.service")


class IdentityService:
    """Service class for identity and authentication operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    
    # User Management
    async def create_user(self, user_data: UserCreate) -> User:
        """Create a new user account."""
        logger.info(f"Creating new user: {user_data.email}")
        
        # Check if user already exists
        existing_user = await self.get_user_by_email(user_data.email)
        if existing_user:
            raise ValidationError("User with this email already exists")
        
        # Hash password
        hashed_password = self.pwd_context.hash(user_data.password)
        
        # Create user
        user = User(
            id=str(uuid.uuid4()),
            email=user_data.email,
            hashed_password=hashed_password,
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            phone=user_data.phone,
            user_type=user_data.user_type,
            status="pending_verification",
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        
        # Assign default role based on user type
        await self._assign_default_role(user)
        
        logger.info(f"User created successfully: {user.email}")
        return user
    
    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID with roles and permissions."""
        query = select(User).where(User.id == user_id).options(
            selectinload(User.roles).selectinload(UserRole.role).selectinload(Role.permissions)
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email with roles and permissions."""
        query = select(User).where(User.email == email).options(
            selectinload(User.roles).selectinload(UserRole.role).selectinload(Role.permissions)
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def update_user(self, user_id: str, user_data: UserUpdate) -> User:
        """Update user profile information."""
        user = await self.get_user_by_id(user_id)
        if not user:
            raise ValidationError("User not found")
        
        update_data = user_data.dict(exclude_unset=True)
        if update_data:
            update_data["updated_at"] = datetime.utcnow()
            
            query = update(User).where(User.id == user_id).values(**update_data)
            await self.db.execute(query)
            await self.db.commit()
            
            # Refresh user object
            await self.db.refresh(user)
        
        logger.info(f"User profile updated: {user.email}")
        return user
    
    async def list_users(
        self, 
        page: int = 1, 
        limit: int = 20, 
        user_type: Optional[str] = None
    ) -> List[User]:
        """List users with pagination and filtering."""
        offset = (page - 1) * limit
        
        query = select(User).offset(offset).limit(limit).options(
            selectinload(User.roles).selectinload(UserRole.role)
        )
        
        if user_type:
            query = query.where(User.user_type == user_type)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def update_user_status(self, user_id: str, is_active: bool) -> Optional[User]:
        """Update user active status."""
        user = await self.get_user_by_id(user_id)
        if not user:
            return None
        
        query = update(User).where(User.id == user_id).values(
            is_active=is_active,
            updated_at=datetime.utcnow()
        )
        await self.db.execute(query)
        await self.db.commit()
        
        await self.db.refresh(user)
        logger.info(f"User status updated: {user.email} - Active: {is_active}")
        return user
    
    # Authentication
    async def authenticate_user(self, email: str, password: str) -> LoginResponse:
        """Authenticate user and return tokens."""
        user = await self.get_user_by_email(email)
        
        if not user or not self.verify_password(password, user.hashed_password):
            logger.warning(f"Failed login attempt for email: {email}")
            await self._handle_failed_login(email)
            raise AuthenticationError("Invalid email or password")
        
        if not user.is_active:
            raise AuthenticationError("Account is deactivated")
        
        if user.status == "suspended":
            raise AuthenticationError("Account is suspended")
        
        # Check if account is locked
        if user.locked_until and user.locked_until > datetime.utcnow():
            raise AuthenticationError("Account is temporarily locked")
        
        # Reset failed login attempts and update last login
        await self._reset_failed_login_attempts(user.id)
        await self._update_last_login(user.id)
        
        # Generate tokens
        tokens = await self._generate_tokens(user)
        
        logger.info(f"Successful login: {user.email}")
        return LoginResponse(
            user=user,
            tokens=tokens,
            message="Login successful"
        )
    
    async def refresh_access_token(self, refresh_token: str) -> LoginResponse:
        """Refresh access token using refresh token."""
        try:
            payload = jwt.decode(
                refresh_token, 
                settings.SECRET_KEY, 
                algorithms=[settings.ALGORITHM]
            )
            
            if payload.get("type") != "refresh":
                raise AuthenticationError("Invalid token type")
            
            user_id = payload.get("user_id")
            if not user_id:
                raise AuthenticationError("Invalid token")
            
            user = await self.get_user_by_id(user_id)
            if not user or not user.is_active:
                raise AuthenticationError("User not found or inactive")
            
            # Generate new tokens
            tokens = await self._generate_tokens(user)
            
            return LoginResponse(
                user=user,
                tokens=tokens,
                message="Token refreshed successfully"
            )
            
        except JWTError as e:
            logger.warning(f"Invalid refresh token: {str(e)}")
            raise AuthenticationError("Invalid or expired refresh token")
    
    async def logout_user(self, access_token: str):
        """Logout user and invalidate token."""
        # In a production system, you would add the token to a blacklist
        # For now, we'll just log the logout
        try:
            payload = jwt.decode(
                access_token,
                settings.SECRET_KEY,
                algorithms=[settings.ALGORITHM]
            )
            user_id = payload.get("user_id")
            logger.info(f"User logged out: {user_id}")
        except JWTError:
            pass  # Invalid token, but logout should still succeed
    
    # Password Management
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash."""
        return self.pwd_context.verify(plain_password, hashed_password)
    
    async def change_password(
        self, 
        user_id: str, 
        current_password: str, 
        new_password: str
    ):
        """Change user password."""
        user = await self.get_user_by_id(user_id)
        if not user:
            raise ValidationError("User not found")
        
        if not self.verify_password(current_password, user.hashed_password):
            raise AuthenticationError("Current password is incorrect")
        
        hashed_password = self.pwd_context.hash(new_password)
        
        query = update(User).where(User.id == user_id).values(
            hashed_password=hashed_password,
            updated_at=datetime.utcnow()
        )
        await self.db.execute(query)
        await self.db.commit()
        
        logger.info(f"Password changed for user: {user.email}")
    
    async def request_password_reset(self, email: str):
        """Request password reset token."""
        user = await self.get_user_by_email(email)
        if not user:
            return  # Don't reveal if email exists
        
        reset_token = secrets.token_urlsafe(32)
        reset_expires = datetime.utcnow() + timedelta(hours=1)
        
        query = update(User).where(User.id == user.id).values(
            password_reset_token=reset_token,
            password_reset_expires=reset_expires,
            updated_at=datetime.utcnow()
        )
        await self.db.execute(query)
        await self.db.commit()
        
        # TODO: Send password reset email
        logger.info(f"Password reset requested for: {email}")
    
    async def reset_password(self, reset_token: str, new_password: str):
        """Reset password using reset token."""
        query = select(User).where(
            User.password_reset_token == reset_token,
            User.password_reset_expires > datetime.utcnow()
        )
        result = await self.db.execute(query)
        user = result.scalar_one_or_none()
        
        if not user:
            raise AuthenticationError("Invalid or expired reset token")
        
        hashed_password = self.pwd_context.hash(new_password)
        
        update_query = update(User).where(User.id == user.id).values(
            hashed_password=hashed_password,
            password_reset_token=None,
            password_reset_expires=None,
            updated_at=datetime.utcnow()
        )
        await self.db.execute(update_query)
        await self.db.commit()
        
        logger.info(f"Password reset completed for: {user.email}")
    
    # Role Management
    async def assign_role_to_user(self, user_id: str, role_name: str):
        """Assign role to user."""
        user = await self.get_user_by_id(user_id)
        if not user:
            raise ValidationError("User not found")
        
        role_query = select(Role).where(Role.name == role_name)
        role_result = await self.db.execute(role_query)
        role = role_result.scalar_one_or_none()
        
        if not role:
            raise ValidationError("Role not found")
        
        # Check if user already has this role
        existing_query = select(UserRole).where(
            UserRole.user_id == user_id,
            UserRole.role_id == role.id
        )
        existing_result = await self.db.execute(existing_query)
        existing = existing_result.scalar_one_or_none()
        
        if existing:
            return  # User already has this role
        
        user_role = UserRole(
            user_id=user_id,
            role_id=role.id,
            assigned_at=datetime.utcnow()
        )
        self.db.add(user_role)
        await self.db.commit()
        
        logger.info(f"Role '{role_name}' assigned to user: {user.email}")
    
    async def remove_role_from_user(self, user_id: str, role_name: str):
        """Remove role from user."""
        role_query = select(Role).where(Role.name == role_name)
        role_result = await self.db.execute(role_query)
        role = role_result.scalar_one_or_none()
        
        if not role:
            raise ValidationError("Role not found")
        
        user_role_query = select(UserRole).where(
            UserRole.user_id == user_id,
            UserRole.role_id == role.id
        )
        user_role_result = await self.db.execute(user_role_query)
        user_role = user_role_result.scalar_one_or_none()
        
        if user_role:
            await self.db.delete(user_role)
            await self.db.commit()
            logger.info(f"Role '{role_name}' removed from user: {user_id}")
    
    # Private Methods
    async def _generate_tokens(self, user: User) -> TokenResponse:
        """Generate access and refresh tokens for user."""
        now = datetime.utcnow()
        
        # Get user permissions
        permissions = await self._get_user_permissions(user)
        roles = [ur.role.name for ur in user.roles]
        
        # Access token payload
        access_payload = TokenPayload(
            user_id=user.id,
            email=user.email,
            user_type=user.user_type,
            roles=roles,
            permissions=permissions,
            exp=int((now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)).timestamp()),
            iat=int(now.timestamp()),
            type="access"
        )
        
        # Refresh token payload
        refresh_payload = TokenPayload(
            user_id=user.id,
            email=user.email,
            user_type=user.user_type,
            roles=roles,
            permissions=permissions,
            exp=int((now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)).timestamp()),
            iat=int(now.timestamp()),
            type="refresh"
        )
        
        # Generate tokens
        access_token = jwt.encode(
            access_payload.dict(),
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM
        )
        
        refresh_token = jwt.encode(
            refresh_payload.dict(),
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM
        )
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
    
    async def _get_user_permissions(self, user: User) -> List[str]:
        """Get all permissions for a user based on their roles."""
        permissions = set()
        
        for user_role in user.roles:
            role = user_role.role
            for permission in role.permissions:
                permissions.add(permission.name)
        
        return list(permissions)
    
    async def _assign_default_role(self, user: User):
        """Assign default role based on user type."""
        role_mapping = {
            "driver": "driver_role",
            "examiner": "examiner_role", 
            "admin": "admin_role",
            "super_admin": "super_admin_role"
        }
        
        default_role = role_mapping.get(user.user_type)
        if default_role:
            try:
                await self.assign_role_to_user(user.id, default_role)
            except ValidationError:
                logger.warning(f"Default role '{default_role}' not found for user type: {user.user_type}")
    
    async def _handle_failed_login(self, email: str):
        """Handle failed login attempt."""
        user = await self.get_user_by_email(email)
        if not user:
            return
        
        failed_attempts = user.failed_login_attempts + 1
        update_data = {
            "failed_login_attempts": failed_attempts,
            "updated_at": datetime.utcnow()
        }
        
        # Lock account after 5 failed attempts
        if failed_attempts >= 5:
            update_data["locked_until"] = datetime.utcnow() + timedelta(minutes=30)
        
        query = update(User).where(User.id == user.id).values(**update_data)
        await self.db.execute(query)
        await self.db.commit()
    
    async def _reset_failed_login_attempts(self, user_id: str):
        """Reset failed login attempts counter."""
        query = update(User).where(User.id == user_id).values(
            failed_login_attempts=0,
            locked_until=None,
            updated_at=datetime.utcnow()
        )
        await self.db.execute(query)
        await self.db.commit()
    
    async def _update_last_login(self, user_id: str):
        """Update user's last login timestamp."""
        query = update(User).where(User.id == user_id).values(
            last_login=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        await self.db.execute(query)
        await self.db.commit()