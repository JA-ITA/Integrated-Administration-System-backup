"""
Registration API routes
"""
import logging
import uuid
from typing import List, Dict, Any
from fastapi import APIRouter, Request, HTTPException, Depends, Header
from fastapi.responses import JSONResponse
import jwt
from datetime import datetime
from models import (
    RegistrationRequest, RegistrationResponse, RegistrationCreateResponse, 
    ErrorResponse
)
from services.registration_service import RegistrationService
from services.event_service import EventService

logger = logging.getLogger(__name__)

router = APIRouter()

# JWT Secret (in production, this should come from environment variables)
JWT_SECRET = "your-jwt-secret-key"  # TODO: Move to config

def get_candidate_from_jwt(authorization: str = Header(None)) -> Dict[str, Any]:
    """Extract candidate information from JWT token"""
    
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")
    
    try:
        # Extract token from "Bearer <token>" format
        if not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Invalid authorization format")
        
        token = authorization.split(" ")[1]
        
        # Decode JWT (in production, use proper validation)
        # For now, we'll create a mock candidate info for testing
        payload = {
            "candidate_id": str(uuid.uuid4()),
            "full_name": "John Doe",
            "dob": "1995-06-15T00:00:00Z",
            "address": "123 Main Street, Anytown, Country",
            "phone": "+1234567890"
        }
        
        # TODO: Implement actual JWT validation
        # payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        
        return payload
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        logger.error(f"JWT validation error: {e}")
        raise HTTPException(status_code=401, detail="Authentication failed")

@router.post("/registrations", response_model=RegistrationCreateResponse)
async def create_registration(
    request: Request,
    registration_data: RegistrationRequest,
    candidate_info: Dict[str, Any] = Depends(get_candidate_from_jwt)
):
    """Create a new driver registration"""
    
    try:
        # Get services from app state
        registration_service = RegistrationService()
        event_service = request.app.state.event_service
        
        # Create registration
        result = await registration_service.create_registration(
            registration_data=registration_data,
            candidate_info=candidate_info
        )
        
        # If registration successful, publish event
        if result.success and result.driver_record_id:
            try:
                await event_service.publish_registration_completed(
                    driver_record_id=str(result.driver_record_id),
                    candidate_id=str(candidate_info["candidate_id"]),
                    booking_id=str(registration_data.booking_id),
                    status=result.registration.status if result.registration else "UNKNOWN"
                )
            except Exception as e:
                logger.error(f"Failed to publish RegistrationCompleted event: {e}")
                # Don't fail the registration if event publishing fails
        
        return result
        
    except Exception as e:
        logger.error(f"Registration creation failed: {e}")
        return RegistrationCreateResponse(
            success=False,
            message="Internal server error",
            validation_errors=[str(e)]
        )

@router.get("/registrations/{registration_id}", response_model=RegistrationResponse)
async def get_registration(registration_id: uuid.UUID):
    """Get registration by ID"""
    
    try:
        registration_service = RegistrationService()
        registration = await registration_service.get_registration(registration_id)
        
        if not registration:
            raise HTTPException(status_code=404, detail="Registration not found")
        
        return registration
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get registration {registration_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/candidates/{candidate_id}/registrations", response_model=List[RegistrationResponse])
async def get_candidate_registrations(candidate_id: uuid.UUID):
    """Get all registrations for a candidate"""
    
    try:
        registration_service = RegistrationService()
        registrations = await registration_service.get_candidate_registrations(candidate_id)
        
        return registrations
        
    except Exception as e:
        logger.error(f"Failed to get candidate registrations {candidate_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/registrations", response_model=Dict[str, Any])
async def get_registrations_stats():
    """Get registration statistics (admin endpoint)"""
    
    try:
        # TODO: Implement statistics gathering
        return {
            "total_registrations": 0,
            "by_status": {
                "REGISTERED": 0,
                "REJECTED": 0,
                "RD_REVIEW": 0
            },
            "by_category": {
                "B": 0,
                "C": 0,
                "PPV": 0,
                "SPECIAL": 0
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get registration statistics: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Health check endpoint for dependencies
@router.get("/health/dependencies")
async def check_dependencies():
    """Check health of dependent services"""
    
    try:
        from services.validation_service import ValidationService
        validation_service = ValidationService()
        
        dependency_status = await validation_service.health_check_dependencies()
        
        return {
            "status": "healthy" if dependency_status["all_dependencies_available"] else "degraded",
            "dependencies": dependency_status
        }
        
    except Exception as e:
        logger.error(f"Dependency health check failed: {e}")
        return {
            "status": "error",
            "dependencies": {},
            "error": str(e)
        }