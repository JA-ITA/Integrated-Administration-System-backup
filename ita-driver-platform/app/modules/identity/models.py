"""
Identity Module SQLAlchemy Models
Database models for users, roles, permissions, and authentication.
"""

from datetime import datetime
from typing import List
from sqlalchemy import String, Boolean, DateTime, Text, ForeignKey, Table, Column
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base


# Association table for many-to-many relationship between roles and permissions
role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column("role_id", String, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    Column("permission_id", String, ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True),
    Column("assigned_at", DateTime, default=datetime.utcnow),
)


class User(Base):
    """User model for authentication and profile management."""
    
    __tablename__ = "users"
    
    # Primary key and basic info
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # Profile information
    first_name: Mapped[str] = mapped_column(String(50), nullable=False)
    last_name: Mapped[str] = mapped_column(String(50), nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    
    # User type and status
    user_type: Mapped[str] = mapped_column(String(20), nullable=False, default="driver")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    
    # Password reset functionality
    password_reset_token: Mapped[str] = mapped_column(String(64), nullable=True)
    password_reset_expires: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    
    # Email verification
    email_verification_token: Mapped[str] = mapped_column(String(64), nullable=True)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    email_verified_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    
    # Security features
    failed_login_attempts: Mapped[int] = mapped_column(default=0)
    locked_until: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    
    # Two-factor authentication
    two_factor_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    two_factor_secret: Mapped[str] = mapped_column(String(32), nullable=True)
    
    # Profile completion tracking
    profile_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    profile_completion_percentage: Mapped[int] = mapped_column(default=0)
    
    # Preferences
    preferred_language: Mapped[str] = mapped_column(String(5), default="en")
    timezone: Mapped[str] = mapped_column(String(50), default="UTC")
    
    # Relationships
    roles: Mapped[List["UserRole"]] = relationship("UserRole", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, type={self.user_type})>"
    
    @property
    def full_name(self):
        """Get user's full name."""
        return f"{self.first_name} {self.last_name}"
    
    @property
    def is_driver(self):
        """Check if user is a driver."""
        return self.user_type == "driver"
    
    @property
    def is_examiner(self):
        """Check if user is an examiner."""
        return self.user_type == "examiner"
    
    @property
    def is_admin(self):
        """Check if user is an admin."""
        return self.user_type in ["admin", "super_admin"]
    
    @property
    def is_super_admin(self):
        """Check if user is a super admin."""
        return self.user_type == "super_admin"


class Role(Base):
    """Role model for role-based access control."""
    
    __tablename__ = "roles"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    
    # Role status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_system_role: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    users: Mapped[List["UserRole"]] = relationship("UserRole", back_populates="role", cascade="all, delete-orphan")
    permissions: Mapped[List["Permission"]] = relationship(
        "Permission", 
        secondary=role_permissions, 
        back_populates="roles"
    )
    
    def __repr__(self):
        return f"<Role(id={self.id}, name={self.name})>"


class Permission(Base):
    """Permission model for granular access control."""
    
    __tablename__ = "permissions"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    
    # Permission categorization
    resource: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g., 'users', 'tests', 'certificates'
    action: Mapped[str] = mapped_column(String(50), nullable=False)    # e.g., 'create', 'read', 'update', 'delete'
    
    # Permission status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_system_permission: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    roles: Mapped[List["Role"]] = relationship(
        "Role", 
        secondary=role_permissions, 
        back_populates="permissions"
    )
    
    def __repr__(self):
        return f"<Permission(id={self.id}, name={self.name})>"


class UserRole(Base):
    """Association model between users and roles with additional metadata."""
    
    __tablename__ = "user_roles"
    
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    role_id: Mapped[str] = mapped_column(String(36), ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True)
    
    # Assignment metadata
    assigned_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    assigned_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="roles", foreign_keys=[user_id])
    role: Mapped["Role"] = relationship("Role", back_populates="users")
    assigned_by_user: Mapped["User"] = relationship("User", foreign_keys=[assigned_by])
    
    def __repr__(self):
        return f"<UserRole(user_id={self.user_id}, role_id={self.role_id})>"


class UserSession(Base):
    """Model for tracking user sessions and token management."""
    
    __tablename__ = "user_sessions"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Session information
    access_token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    refresh_token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    
    # Session metadata
    ip_address: Mapped[str] = mapped_column(String(45), nullable=True)  # IPv6 compatible
    user_agent: Mapped[str] = mapped_column(Text, nullable=True)
    device_info: Mapped[str] = mapped_column(Text, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_accessed: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    
    # Session status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    revoked_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    revoked_reason: Mapped[str] = mapped_column(String(100), nullable=True)
    
    # Relationships
    user: Mapped["User"] = relationship("User")
    
    def __repr__(self):
        return f"<UserSession(id={self.id}, user_id={self.user_id})>"


class AuditLog(Base):
    """Model for auditing user actions and security events."""
    
    __tablename__ = "audit_logs"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    
    # Event information
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    resource: Mapped[str] = mapped_column(String(100), nullable=True)
    resource_id: Mapped[str] = mapped_column(String(36), nullable=True)
    
    # Event details
    description: Mapped[str] = mapped_column(Text, nullable=True)
    changes: Mapped[str] = mapped_column(Text, nullable=True)  # JSON string of changes
    
    # Request information
    ip_address: Mapped[str] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str] = mapped_column(Text, nullable=True)
    request_id: Mapped[str] = mapped_column(String(36), nullable=True)
    
    # Event classification
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)  # 'login', 'logout', 'create', 'update', 'delete'
    severity: Mapped[str] = mapped_column(String(20), default="info")    # 'info', 'warning', 'error', 'critical'
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user: Mapped["User"] = relationship("User")
    
    def __repr__(self):
        return f"<AuditLog(id={self.id}, action={self.action}, user_id={self.user_id})>"