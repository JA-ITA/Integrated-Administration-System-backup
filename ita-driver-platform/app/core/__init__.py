"""
Core module for Island Traffic Authority Driver Platform.

This module contains shared configuration, utilities, and foundational components
used across all modules in the application.
"""

from .config import settings, get_settings
from .database import Base, get_db, get_session, init_database, close_database
from .exceptions import (
    ITAException,
    AuthenticationError,
    AuthorizationError,
    ValidationError,
    BusinessRuleError,
    ExternalServiceError,
    DatabaseError,
)

__all__ = [
    # Configuration
    "settings",
    "get_settings",
    
    # Database
    "Base",
    "get_db",
    "get_session",
    "init_database",
    "close_database",
    
    # Exceptions
    "ITAException",
    "AuthenticationError",
    "AuthorizationError",
    "ValidationError", 
    "BusinessRuleError",
    "ExternalServiceError",
    "DatabaseError",
]