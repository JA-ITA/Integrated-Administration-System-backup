"""
Identity Module Router - Enhanced Candidate Management API
Handles candidate registration, OTP verification, and profile management.
API Version: v1
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from core.database import get_db
from core.logging_config import get_logger
from .schemas import (
    CandidateCreateRequest,
    CandidateCreateResponse,
    CandidateResponse,
    OTPVerificationRequest,
    OTPVerificationResponse,
    OTPResendRequest,
    PasswordSetRequest,
    OTPStatusResponse,
    OTPType,
    ApiErrorResponse
)
from .service import CandidateService

logger = get_logger("identity.router")

# Create router with v1 prefix
router = APIRouter(prefix="/v1")


def get_correlation_id(request: Request) -> str:
    """Extract or generate correlation ID for request tracing."""
    correlation_id = request.headers.get("X-Correlation-ID")
    if not correlation_id:
        correlation_id = str(uuid.uuid4())
    return correlation_id


def get_client_info(request: Request) -> tuple[Optional[str], Optional[str]]:
    """Extract client IP and User-Agent from request."""
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("User-Agent")
    return ip_address, user_agent


@router.post("/candidates", response_model=CandidateCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_candidate(
    candidate_request: CandidateCreateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new candidate with OTP verification.
    
    **This endpoint creates a new driver license candidate and initiates the verification process.**
    
    - **email**: Valid email address (will be used for login)
    - **first_name**: Candidate's first name 
    - **last_name**: Candidate's last name
    - **phone**: Bermuda phone number for SMS verification
    - **date_of_birth**: Date of birth (must be 16+ years old)
    - **national_id**: Bermuda national ID number (optional)
    - **passport_number**: Passport number (optional)
    - **street_address**: Street address (optional)
    - **city**: City (optional)
    - **postal_code**: Postal code (optional)
    - **country**: Country (defaults to Bermuda)
    
    **Process:**
    1. Validates candidate information
    2. Creates candidate record with PENDING_VERIFICATION status
    3. Sends OTP to email and phone
    4. Publishes CandidateCreated event
    5. Returns candidate info and verification instructions
    
    **Response includes:**
    - Created candidate information
    - OTP sending status for email and phone
    - Next steps for verification
    """
    service = CandidateService(db)
    correlation_id = get_correlation_id(request)
    ip_address, user_agent = get_client_info(request)
    
    try:
        logger.info(
            f"Creating candidate: {candidate_request.email}",
            extra={"correlation_id": correlation_id}
        )
        
        response = await service.create_candidate(
            candidate_data=candidate_request,
            correlation_id=correlation_id,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        logger.info(
            f"Candidate created successfully: {response.candidate.id}",
            extra={"correlation_id": correlation_id, "candidate_id": response.candidate.id}
        )
        
        return response
        
    except ValueError as e:
        logger.warning(
            f"Candidate creation validation error: {str(e)}",
            extra={"correlation_id": correlation_id, "email": candidate_request.email}
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "validation_error",
                "message": str(e),
                "correlation_id": correlation_id
            }
        )
    except Exception as e:
        logger.error(
            f"Candidate creation error: {str(e)}",
            extra={"correlation_id": correlation_id, "email": candidate_request.email}
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "internal_error",
                "message": "An error occurred while creating candidate",
                "correlation_id": correlation_id
            }
        )


@router.get("/candidates/{candidate_id}", response_model=CandidateResponse)
async def get_candidate(
    candidate_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Get candidate information by ID.
    
    **Returns detailed candidate information including:**
    - Personal information (with sensitive data masked)
    - Verification status (email, phone, identity)
    - Profile completion percentage
    - Current candidate status
    - Timestamps for creation and updates
    
    **Access Control:**
    - Public endpoint for candidate's own information
    - Admin endpoints for viewing any candidate (future implementation)
    
    **Data Privacy:**
    - National ID and passport numbers are masked in response
    - Full information available only to authorized personnel
    """
    service = CandidateService(db)
    correlation_id = get_correlation_id(request)
    
    try:
        candidate = await service.get_candidate_by_id(candidate_id)
        
        if not candidate:
            logger.warning(
                f"Candidate not found: {candidate_id}",
                extra={"correlation_id": correlation_id}
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "not_found",
                    "message": "Candidate not found",
                    "correlation_id": correlation_id
                }
            )
        
        response = await service._candidate_to_response(candidate)
        
        logger.info(
            f"Candidate retrieved: {candidate_id}",
            extra={"correlation_id": correlation_id, "candidate_id": candidate_id}
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error retrieving candidate: {str(e)}",
            extra={"correlation_id": correlation_id, "candidate_id": candidate_id}
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "internal_error", 
                "message": "An error occurred while retrieving candidate",
                "correlation_id": correlation_id
            }
        )


@router.post("/candidates/{candidate_id}/verify-otp", response_model=OTPVerificationResponse)
async def verify_candidate_otp(
    candidate_id: str,
    verification_request: OTPVerificationRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Verify OTP code for candidate email or phone verification.
    
    **OTP Verification Process:**
    1. Validates the provided OTP code
    2. Marks email or phone as verified
    3. Updates candidate status if both verifications complete
    4. Publishes verification events
    
    **Parameters:**
    - **candidate_id**: Must match the ID in the request body
    - **otp_type**: Either "email" or "phone"
    - **otp_code**: 6-digit verification code
    
    **Verification Rules:**
    - OTP expires after 10 minutes
    - Maximum 3 attempts per OTP
    - New OTP required after expiration or exhausted attempts
    
    **Success Response:**
    - Confirmation of successful verification  
    - Next steps (set password if both email/phone verified)
    """
    if verification_request.candidate_id != candidate_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "validation_error",
                "message": "Candidate ID mismatch"
            }
        )
    
    service = CandidateService(db)
    correlation_id = get_correlation_id(request)
    
    try:
        success, message = await service.verify_candidate_otp(
            candidate_id=candidate_id,
            otp_type=verification_request.otp_type,
            otp_code=verification_request.otp_code,
            correlation_id=correlation_id
        )
        
        # Determine next step
        next_step = None
        if success:
            candidate = await service.get_candidate_by_id(candidate_id)
            if candidate and candidate.is_fully_verified and not candidate.hashed_password:
                next_step = "set_password"
        
        response = OTPVerificationResponse(
            success=success,
            message=message,
            candidate_id=candidate_id,
            verification_type=verification_request.otp_type,
            next_step=next_step
        )
        
        if success:
            logger.info(
                f"OTP verification successful: {candidate_id} - {verification_request.otp_type.value}",
                extra={"correlation_id": correlation_id, "candidate_id": candidate_id}
            )
        else:
            logger.warning(
                f"OTP verification failed: {candidate_id} - {message}",
                extra={"correlation_id": correlation_id, "candidate_id": candidate_id}
            )
        
        return response
        
    except Exception as e:
        logger.error(
            f"OTP verification error: {str(e)}",
            extra={"correlation_id": correlation_id, "candidate_id": candidate_id}
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "internal_error",
                "message": "An error occurred during OTP verification",
                "correlation_id": correlation_id
            }
        )


@router.post("/candidates/{candidate_id}/resend-otp")
async def resend_candidate_otp(
    candidate_id: str,
    resend_request: OTPResendRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Resend OTP code to candidate's email or phone.
    
    **Resend Rules:**
    - 2-minute cooldown between resend requests
    - Previous OTP becomes invalid when new one is sent
    - Rate limiting applied per IP address
    
    **Parameters:**
    - **candidate_id**: Must match the ID in request body
    - **otp_type**: Either "email" or "phone"
    
    **Success Response:**
    - Confirmation that OTP was sent
    - Masked recipient information
    - Expiration time for new OTP
    """
    if resend_request.candidate_id != candidate_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "validation_error", 
                "message": "Candidate ID mismatch"
            }
        )
    
    service = CandidateService(db)
    correlation_id = get_correlation_id(request)
    ip_address, user_agent = get_client_info(request)
    
    try:
        success, message = await service.resend_otp(
            candidate_id=candidate_id,
            otp_type=resend_request.otp_type,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        if success:
            logger.info(
                f"OTP resent successfully: {candidate_id} - {resend_request.otp_type.value}",
                extra={"correlation_id": correlation_id, "candidate_id": candidate_id}
            )
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "success": True,
                    "message": message,
                    "candidate_id": candidate_id,
                    "otp_type": resend_request.otp_type.value,
                    "correlation_id": correlation_id
                }
            )
        else:
            logger.warning(
                f"OTP resend failed: {candidate_id} - {message}",
                extra={"correlation_id": correlation_id, "candidate_id": candidate_id}
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "resend_error",
                    "message": message,
                    "correlation_id": correlation_id
                }
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"OTP resend error: {str(e)}",
            extra={"correlation_id": correlation_id, "candidate_id": candidate_id}
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "internal_error",
                "message": "An error occurred while resending OTP",
                "correlation_id": correlation_id
            }
        )


@router.post("/candidates/{candidate_id}/set-password")
async def set_candidate_password(
    candidate_id: str,
    password_request: PasswordSetRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Set password for candidate after complete verification.
    
    **Prerequisites:**
    - Both email and phone must be verified
    - No existing password set
    - Valid candidate ID
    
    **Password Requirements:**
    - Minimum 8 characters
    - At least one uppercase letter
    - At least one lowercase letter  
    - At least one digit
    - At least one special character
    
    **Process:**
    1. Validates password requirements
    2. Confirms passwords match
    3. Hashes and stores password
    4. Activates candidate account
    5. Updates status to ACTIVE
    """
    if password_request.candidate_id != candidate_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "validation_error",
                "message": "Candidate ID mismatch"
            }
        )
    
    service = CandidateService(db)
    correlation_id = get_correlation_id(request)
    
    try:
        success = await service.set_candidate_password(
            candidate_id=candidate_id,
            password=password_request.password,
            correlation_id=correlation_id
        )
        
        if success:
            logger.info(
                f"Password set successfully: {candidate_id}",
                extra={"correlation_id": correlation_id, "candidate_id": candidate_id}
            )
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "success": True,
                    "message": "Password set successfully. Your account is now active.",
                    "candidate_id": candidate_id,
                    "status": "active",
                    "correlation_id": correlation_id
                }
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "error": "internal_error",
                    "message": "Failed to set password"
                }
            )
            
    except ValueError as e:
        logger.warning(
            f"Password set validation error: {str(e)}",
            extra={"correlation_id": correlation_id, "candidate_id": candidate_id}
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "validation_error",
                "message": str(e),
                "correlation_id": correlation_id
            }
        )
    except Exception as e:
        logger.error(
            f"Password set error: {str(e)}",
            extra={"correlation_id": correlation_id, "candidate_id": candidate_id}
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "internal_error",
                "message": "An error occurred while setting password",
                "correlation_id": correlation_id
            }
        )


@router.get("/candidates/{candidate_id}/otp-status", response_model=OTPStatusResponse)
async def get_otp_status(
    candidate_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Get OTP verification status for candidate.
    
    **Returns:**
    - Email OTP status (not_sent, pending, verified, expired, exhausted)
    - Phone OTP status (not_sent, pending, verified, expired, exhausted)
    - Overall verification status
    - Whether candidate can proceed to set password
    
    **Status Values:**
    - **not_sent**: No OTP has been sent
    - **pending**: OTP sent and awaiting verification
    - **verified**: OTP successfully verified
    - **expired**: OTP has expired (10+ minutes old)
    - **exhausted**: Maximum attempts (3) reached
    
    **Use Cases:**
    - Check verification progress
    - Determine if resend is needed
    - Show appropriate UI state
    """
    service = CandidateService(db)
    correlation_id = get_correlation_id(request)
    
    try:
        status_info = await service.get_otp_status(candidate_id)
        
        response = OTPStatusResponse(**status_info)
        
        logger.info(
            f"OTP status retrieved: {candidate_id}",
            extra={"correlation_id": correlation_id, "candidate_id": candidate_id}
        )
        
        return response
        
    except ValueError as e:
        logger.warning(
            f"OTP status validation error: {str(e)}",
            extra={"correlation_id": correlation_id, "candidate_id": candidate_id}
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "not_found",
                "message": str(e),
                "correlation_id": correlation_id
            }
        )
    except Exception as e:
        logger.error(
            f"OTP status error: {str(e)}",
            extra={"correlation_id": correlation_id, "candidate_id": candidate_id}
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "internal_error",
                "message": "An error occurred while retrieving OTP status",
                "correlation_id": correlation_id
            }
        )


# Health check endpoint for the identity module
@router.get("/health")
async def identity_health_check():
    """
    Health check endpoint for the Identity module.
    
    **Returns:**
    - Module status
    - Available features
    - Version information
    """
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "module": "Identity & Profile Management",
            "version": "1.0.0",
            "status": "healthy",
            "features": {
                "candidate_registration": "available",
                "otp_verification": "available",
                "event_publishing": "available",
                "profile_management": "available"
            },
            "endpoints": {
                "create_candidate": "POST /api/v1/candidates",
                "get_candidate": "GET /api/v1/candidates/{id}",
                "verify_otp": "POST /api/v1/candidates/{id}/verify-otp",
                "resend_otp": "POST /api/v1/candidates/{id}/resend-otp",
                "set_password": "POST /api/v1/candidates/{id}/set-password",
                "otp_status": "GET /api/v1/candidates/{id}/otp-status"
            }
        }
    )


# Error handlers for the identity module
@router.exception_handler(HTTPException)
async def identity_http_exception_handler(request: Request, exc: HTTPException):
    """Custom HTTP exception handler for identity module."""
    correlation_id = get_correlation_id(request)
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "http_error",
            "message": exc.detail,
            "status_code": exc.status_code,
            "correlation_id": correlation_id,
            "timestamp": "2025-01-27T00:00:00Z"  # In real app, use actual timestamp
        }
    )