"""
Custom exceptions and error handlers for the Island Traffic Authority application.
Provides structured error responses and centralized exception handling.
"""

import logging
from typing import Any, Dict
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError, HTTPException
from sqlalchemy.exc import SQLAlchemyError
from pydantic import ValidationError

logger = logging.getLogger("ita.exceptions")


# Custom Exception Classes
class ITAException(Exception):
    """Base exception class for Island Traffic Authority application."""
    
    def __init__(self, message: str, details: Dict[str, Any] = None):
        self.message = message
        self.details = details or {}
        super().__init__(message)


class AuthenticationError(ITAException):
    """Raised when authentication fails."""
    pass


class AuthorizationError(ITAException):
    """Raised when user lacks required permissions."""
    pass


class ValidationError(ITAException):
    """Raised when data validation fails."""
    pass


class BusinessRuleError(ITAException):
    """Raised when business rules are violated."""
    pass


class ExternalServiceError(ITAException):
    """Raised when external service calls fail."""
    pass


class DatabaseError(ITAException):
    """Raised when database operations fail."""
    pass


# Error Response Models
def create_error_response(
    message: str,
    error_code: str = None,
    details: Dict[str, Any] = None,
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
) -> JSONResponse:
    """Create standardized error response."""
    
    error_response = {
        "error": {
            "message": message,
            "code": error_code,
            "details": details or {},
            "timestamp": "2025-01-27T00:00:00Z"  # In real app, use actual timestamp
        },
        "success": False
    }
    
    return JSONResponse(
        status_code=status_code,
        content=error_response
    )


# Exception Handlers
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle FastAPI validation errors."""
    logger.warning(f"Validation error: {exc.errors()}")
    
    return create_error_response(
        message="Validation failed",
        error_code="VALIDATION_ERROR",
        details={
            "validation_errors": exc.errors(),
            "body": exc.body if hasattr(exc, 'body') else None
        },
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY
    )


async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions."""
    logger.warning(f"HTTP exception: {exc.detail}")
    
    return create_error_response(
        message=exc.detail,
        error_code="HTTP_ERROR",
        status_code=exc.status_code
    )


async def authentication_exception_handler(request: Request, exc: AuthenticationError):
    """Handle authentication errors."""
    logger.warning(f"Authentication error: {exc.message}")
    
    return create_error_response(
        message=exc.message,
        error_code="AUTHENTICATION_ERROR",
        details=exc.details,
        status_code=status.HTTP_401_UNAUTHORIZED
    )


async def authorization_exception_handler(request: Request, exc: AuthorizationError):
    """Handle authorization errors."""
    logger.warning(f"Authorization error: {exc.message}")
    
    return create_error_response(
        message=exc.message,
        error_code="AUTHORIZATION_ERROR",
        details=exc.details,
        status_code=status.HTTP_403_FORBIDDEN
    )


async def business_rule_exception_handler(request: Request, exc: BusinessRuleError):
    """Handle business rule violations."""
    logger.warning(f"Business rule error: {exc.message}")
    
    return create_error_response(
        message=exc.message,
        error_code="BUSINESS_RULE_ERROR",
        details=exc.details,
        status_code=status.HTTP_400_BAD_REQUEST
    )


async def external_service_exception_handler(request: Request, exc: ExternalServiceError):
    """Handle external service errors."""
    logger.error(f"External service error: {exc.message}")
    
    return create_error_response(
        message="External service temporarily unavailable",
        error_code="EXTERNAL_SERVICE_ERROR",
        details=exc.details if not exc.details.get("sensitive") else {},
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE
    )


async def database_exception_handler(request: Request, exc: DatabaseError):
    """Handle database errors."""
    logger.error(f"Database error: {exc.message}")
    
    return create_error_response(
        message="Database operation failed",
        error_code="DATABASE_ERROR",
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
    )


async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    """Handle SQLAlchemy database errors."""
    logger.error(f"SQLAlchemy error: {str(exc)}")
    
    return create_error_response(
        message="Database operation failed",
        error_code="DATABASE_ERROR",
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
    )


async def generic_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions."""
    logger.error(f"Unexpected error: {str(exc)}", exc_info=True)
    
    # In production, don't expose internal error details
    message = "Internal server error"
    details = {}
    
    if not settings.is_production:
        message = str(exc)
        details = {"type": type(exc).__name__}
    
    return create_error_response(
        message=message,
        error_code="INTERNAL_SERVER_ERROR",
        details=details,
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
    )


def setup_exception_handlers(app: FastAPI) -> None:
    """Configure exception handlers for the FastAPI application."""
    
    # FastAPI built-in exceptions
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    
    # Custom application exceptions
    app.add_exception_handler(AuthenticationError, authentication_exception_handler)
    app.add_exception_handler(AuthorizationError, authorization_exception_handler)
    app.add_exception_handler(BusinessRuleError, business_rule_exception_handler)
    app.add_exception_handler(ExternalServiceError, external_service_exception_handler)
    app.add_exception_handler(DatabaseError, database_exception_handler)
    
    # SQLAlchemy exceptions
    app.add_exception_handler(SQLAlchemyError, sqlalchemy_exception_handler)
    
    # Generic exception handler (catch-all)
    app.add_exception_handler(Exception, generic_exception_handler)
    
    logger.info("Exception handlers configured")


# Import settings after defining exception handlers to avoid circular imports
from core.config import settings