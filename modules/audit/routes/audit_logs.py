"""
Audit log routes for ITADIAS Audit Microservice
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional
from models import (
    AuditLogCreate, AuditLogResponse, ErrorResponse, 
    RDAuthUser, ResourceType, AuditAction, ActorRole
)
from services.auth_service import get_current_rd_user
from services.audit_service import AuditService

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/audit-logs", tags=["audit-logs"])

# Dependencies will be injected in app.py
audit_service = None

def set_audit_service(audit_svc: AuditService):
    """Set audit service dependency"""
    global audit_service
    audit_service = audit_svc

@router.post("/", response_model=AuditLogResponse)
async def create_audit_log(
    audit_data: AuditLogCreate,
    current_user: RDAuthUser = Depends(get_current_rd_user)
):
    """
    Create a new audit log entry
    
    Requires valid RD JWT token
    """
    try:
        if not audit_service:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Audit service not initialized"
            )
        
        # Create audit log
        audit_log = await audit_service.create_audit_log(audit_data)
        
        logger.info(f"Created audit log entry: {audit_log.id}")
        
        return audit_log
        
    except Exception as e:
        logger.error(f"Failed to create audit log: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while creating audit log"
        )

@router.get("/", response_model=List[AuditLogResponse])
async def get_audit_logs(
    resource_type: Optional[ResourceType] = Query(None, description="Filter by resource type"),
    resource_id: Optional[str] = Query(None, description="Filter by resource ID"),
    actor_id: Optional[str] = Query(None, description="Filter by actor ID"),
    action: Optional[AuditAction] = Query(None, description="Filter by action"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records"),
    offset: int = Query(0, ge=0, description="Number of records to skip"),
    current_user: RDAuthUser = Depends(get_current_rd_user)
):
    """
    Get audit logs with optional filters
    
    Requires valid RD JWT token
    """
    try:
        if not audit_service:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Audit service not initialized"
            )
        
        # Parse UUID fields if provided
        resource_uuid = None
        actor_uuid = None
        
        try:
            if resource_id:
                import uuid
                resource_uuid = uuid.UUID(resource_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid resource_id format"
            )
        
        try:
            if actor_id:
                import uuid
                actor_uuid = uuid.UUID(actor_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid actor_id format"
            )
        
        # Get audit logs
        audit_logs = await audit_service.get_audit_logs(
            resource_type=resource_type,
            resource_id=resource_uuid,
            actor_id=actor_uuid,
            action=action,
            limit=limit,
            offset=offset
        )
        
        logger.info(f"Retrieved {len(audit_logs)} audit logs with filters")
        
        return audit_logs
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get audit logs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while retrieving audit logs"
        )

@router.get("/statistics")
async def get_audit_statistics(
    current_user: RDAuthUser = Depends(get_current_rd_user)
):
    """
    Get audit statistics
    
    Requires valid RD JWT token
    """
    try:
        if not audit_service:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Audit service not initialized"
            )
        
        # Get recent audit logs to calculate statistics
        recent_logs = await audit_service.get_audit_logs(limit=1000)
        
        # Calculate statistics
        total_logs = len(recent_logs)
        
        action_counts = {}
        resource_type_counts = {}
        actor_role_counts = {}
        
        for log in recent_logs:
            # Count actions
            action_counts[log.action] = action_counts.get(log.action, 0) + 1
            
            # Count resource types
            resource_type_counts[log.resource_type] = resource_type_counts.get(log.resource_type, 0) + 1
            
            # Count actor roles
            actor_role_counts[log.actor_role] = actor_role_counts.get(log.actor_role, 0) + 1
        
        statistics = {
            "total_audit_logs": total_logs,
            "action_distribution": action_counts,
            "resource_type_distribution": resource_type_counts,
            "actor_role_distribution": actor_role_counts,
            "recent_logs_sample_size": min(1000, total_logs)
        }
        
        logger.info("Generated audit statistics")
        
        return statistics
        
    except Exception as e:
        logger.error(f"Failed to get audit statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while calculating statistics"
        )