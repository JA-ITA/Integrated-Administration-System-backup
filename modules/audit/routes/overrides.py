"""
Override routes for ITADIAS Audit Microservice
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from models import (
    OverrideRequest, OverrideResponse, AuditLogResponse, 
    ErrorResponse, RDAuthUser, ResourceType, AuditAction
)
from services.auth_service import get_current_rd_user
from services.audit_service import AuditService
from services.event_service import EventService

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/overrides", tags=["overrides"])

# Dependencies will be injected in app.py
audit_service = None
event_service = None

def set_services(audit_svc: AuditService, event_svc: EventService):
    """Set service dependencies"""
    global audit_service, event_service
    audit_service = audit_svc
    event_service = event_svc

@router.post("/", response_model=OverrideResponse)
async def create_override(
    override_request: OverrideRequest,
    current_user: RDAuthUser = Depends(get_current_rd_user)
):
    """
    Create an override for a resource in RD_REVIEW state
    
    Requires:
    - Valid RD JWT token in Authorization header
    - Mandatory reason field
    
    Publishes OverrideIssued event for other microservices to process
    """
    try:
        if not audit_service:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Audit service not initialized"
            )
        
        logger.info(
            f"Processing override request by RD {current_user.user_id} for "
            f"{override_request.resource_type}:{override_request.resource_id}"
        )
        
        # Process the override request
        result = await audit_service.process_override_request(
            override_request, 
            current_user
        )
        
        if result.success:
            return result
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.message
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to process override: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while processing override"
        )

@router.get("/audit/{resource_type}/{resource_id}", response_model=List[AuditLogResponse])
async def get_resource_audit_history(
    resource_type: ResourceType,
    resource_id: str,
    current_user: RDAuthUser = Depends(get_current_rd_user)
):
    """
    Get audit history for a specific resource
    
    Requires valid RD JWT token
    """
    try:
        if not audit_service:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Audit service not initialized"
            )
        
        import uuid
        resource_uuid = uuid.UUID(resource_id)
        
        # Get audit history
        audit_logs = await audit_service.get_resource_audit_history(
            resource_type, 
            resource_uuid
        )
        
        logger.info(f"Retrieved {len(audit_logs)} audit logs for {resource_type}:{resource_id}")
        
        return audit_logs
        
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid resource ID format"
        )
    except Exception as e:
        logger.error(f"Failed to get audit history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while retrieving audit history"
        )

@router.get("/audit/actor/{actor_id}", response_model=List[AuditLogResponse])
async def get_actor_audit_history(
    actor_id: str,
    action: AuditAction = None,
    limit: int = 100,
    offset: int = 0,
    current_user: RDAuthUser = Depends(get_current_rd_user)
):
    """
    Get audit history for a specific actor (user)
    
    Requires valid RD JWT token
    """
    try:
        if not audit_service:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Audit service not initialized"
            )
        
        import uuid
        actor_uuid = uuid.UUID(actor_id)
        
        # Get audit logs for actor
        audit_logs = await audit_service.get_audit_logs(
            actor_id=actor_uuid,
            action=action,
            limit=min(limit, 1000),  # Cap at 1000
            offset=offset
        )
        
        logger.info(f"Retrieved {len(audit_logs)} audit logs for actor {actor_id}")
        
        return audit_logs
        
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid actor ID format"
        )
    except Exception as e:
        logger.error(f"Failed to get actor audit history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while retrieving actor audit history"
        )