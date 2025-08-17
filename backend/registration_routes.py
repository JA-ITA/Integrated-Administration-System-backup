"""
Registration routes for main backend
Proxy endpoints to registration microservice
"""
import logging
import uuid
from typing import List, Dict, Any
from fastapi import APIRouter, Request, HTTPException, Header, UploadFile, File, Form
from fastapi.responses import JSONResponse
import base64
from registration_client import registration_client, RegistrationRequest, DocumentUpload

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/registration/health")
async def registration_health():
    """Check registration service health"""
    try:
        health_status = await registration_client.health_check()
        if health_status:
            return health_status
        else:
            return {
                "status": "unavailable",
                "service": "Registration Service",
                "error": "Service not responding"
            }
    except Exception as e:
        logger.error(f"Registration health check failed: {e}")
        raise HTTPException(status_code=503, detail="Registration service unavailable")

@router.post("/registrations")
async def create_registration(
    booking_id: str = Form(...),
    receipt_no: str = Form(...),
    vehicle_weight_kg: int = Form(...),
    vehicle_category: str = Form(...),
    manager_override: bool = Form(False),
    override_reason: str = Form(None),
    override_by: str = Form(None),
    authorization: str = Header(None),
    # File uploads
    photo: UploadFile = File(...),
    id_proof: UploadFile = File(...),
    mc1: UploadFile = File(None),
    mc2: UploadFile = File(None),
    other: UploadFile = File(None)
):
    """Create a new driver registration with document uploads"""
    
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")
    
    try:
        # Validate booking_id format
        booking_uuid = uuid.UUID(booking_id)
        
        # Process uploaded files
        documents = []
        
        # Required documents
        if photo:
            photo_content = await photo.read()
            documents.append(DocumentUpload(
                type="photo",
                filename=photo.filename,
                content=base64.b64encode(photo_content).decode('utf-8'),
                mime_type=photo.content_type
            ))
        
        if id_proof:
            id_proof_content = await id_proof.read()
            documents.append(DocumentUpload(
                type="id_proof",
                filename=id_proof.filename,
                content=base64.b64encode(id_proof_content).decode('utf-8'),
                mime_type=id_proof.content_type
            ))
        
        # Optional documents
        if mc1:
            mc1_content = await mc1.read()
            documents.append(DocumentUpload(
                type="mc1",
                filename=mc1.filename,
                content=base64.b64encode(mc1_content).decode('utf-8'),
                mime_type=mc1.content_type
            ))
        
        if mc2:
            mc2_content = await mc2.read()
            documents.append(DocumentUpload(
                type="mc2",
                filename=mc2.filename,
                content=base64.b64encode(mc2_content).decode('utf-8'),
                mime_type=mc2.content_type
            ))
        
        if other:
            other_content = await other.read()
            documents.append(DocumentUpload(
                type="other",
                filename=other.filename,
                content=base64.b64encode(other_content).decode('utf-8'),
                mime_type=other.content_type
            ))
        
        # Create registration request
        registration_request = RegistrationRequest(
            booking_id=booking_uuid,
            receipt_no=receipt_no,
            vehicle_weight_kg=vehicle_weight_kg,
            vehicle_category=vehicle_category,
            docs=documents,
            manager_override=manager_override,
            override_reason=override_reason if override_reason else None,
            override_by=override_by if override_by else None
        )
        
        # Call registration service
        result = await registration_client.create_registration(
            registration_data=registration_request,
            jwt_token=authorization.replace("Bearer ", "")
        )
        
        if result and result.success:
            return result.dict()
        elif result:
            raise HTTPException(
                status_code=400, 
                detail={
                    "message": result.message,
                    "validation_errors": result.validation_errors
                }
            )
        else:
            raise HTTPException(status_code=503, detail="Registration service unavailable")
            
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid UUID format: {str(e)}")
    except Exception as e:
        logger.error(f"Registration creation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/registrations/{registration_id}")
async def get_registration(registration_id: uuid.UUID):
    """Get registration by ID"""
    try:
        registration = await registration_client.get_registration(registration_id)
        
        if registration:
            return registration
        else:
            raise HTTPException(status_code=404, detail="Registration not found")
            
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid registration ID format")
    except Exception as e:
        logger.error(f"Get registration failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/candidates/{candidate_id}/registrations")
async def get_candidate_registrations(candidate_id: uuid.UUID):
    """Get all registrations for a candidate"""
    try:
        registrations = await registration_client.get_candidate_registrations(candidate_id)
        return registrations
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid candidate ID format")
    except Exception as e:
        logger.error(f"Get candidate registrations failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/registrations")
async def get_registration_statistics():
    """Get registration statistics"""
    try:
        stats = await registration_client.get_statistics()
        
        if stats:
            return stats
        else:
            raise HTTPException(status_code=503, detail="Registration service unavailable")
            
    except Exception as e:
        logger.error(f"Get registration statistics failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/registration/dependencies")
async def check_registration_dependencies():
    """Check registration service dependencies"""
    try:
        dependencies = await registration_client.check_dependencies()
        
        if dependencies:
            return dependencies
        else:
            return {
                "status": "unavailable",
                "dependencies": {},
                "error": "Registration service not responding"
            }
            
    except Exception as e:
        logger.error(f"Check registration dependencies failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/registration/events")
async def get_registration_events_status():
    """Get registration event publishing status"""
    try:
        events_status = await registration_client.get_events_status()
        
        if events_status:
            return events_status
        else:
            return {
                "error": "Registration service not responding",
                "event_service": {"connected": False},
                "fallback_events_count": 0
            }
            
    except Exception as e:
        logger.error(f"Get registration events status failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))