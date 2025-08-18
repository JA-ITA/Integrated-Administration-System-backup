"""
Core audit service for creating audit logs and handling overrides
"""
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy import select, desc, and_
from sqlalchemy.ext.asyncio import AsyncSession
from models import (
    AuditLog, AuditLogCreate, AuditLogResponse, OverrideRequest, 
    OverrideResponse, OverrideIssuedEvent, ActorRole, AuditAction, 
    ResourceType, RDAuthUser
)
from database import get_db_session
from services.event_service import EventService

logger = logging.getLogger(__name__)

class AuditService:
    """Core audit service"""
    
    def __init__(self, event_service: EventService):
        self.event_service = event_service
    
    async def create_audit_log(
        self, 
        audit_data: AuditLogCreate,
        db_session: Optional[AsyncSession] = None
    ) -> AuditLogResponse:
        """Create a new audit log entry"""
        try:
            # Use provided session or create new one
            if db_session:
                session = db_session
                should_close = False
            else:
                session = await anext(get_db_session())
                should_close = True
            
            try:
                # Create audit log entry
                audit_log = AuditLog(
                    actor_id=audit_data.actor_id,
                    actor_role=audit_data.actor_role.value,
                    action=audit_data.action.value,
                    resource_type=audit_data.resource_type.value,
                    resource_id=audit_data.resource_id,
                    old_val=audit_data.old_val,
                    new_val=audit_data.new_val,
                    reason=audit_data.reason,
                    created_at=datetime.now(timezone.utc)
                )
                
                session.add(audit_log)
                await session.commit()
                await session.refresh(audit_log)
                
                logger.info(f"Created audit log entry: {audit_log.id}")
                
                return AuditLogResponse.from_orm(audit_log)
                
            finally:
                if should_close:
                    await session.close()
                    
        except Exception as e:
            logger.error(f"Failed to create audit log: {e}")
            if not db_session:
                await session.rollback()
            raise e
    
    async def process_override_request(
        self, 
        override_request: OverrideRequest,
        rd_user: RDAuthUser
    ) -> OverrideResponse:
        """Process an override request from RD"""
        try:
            async with await anext(get_db_session()) as session:
                # Create audit log for the override action
                audit_data = AuditLogCreate(
                    actor_id=rd_user.user_id,
                    actor_role=ActorRole.RD,
                    action=AuditAction.OVERRIDE,
                    resource_type=override_request.resource_type,
                    resource_id=override_request.resource_id,
                    old_val={"status": override_request.old_status} if override_request.old_status else None,
                    new_val={
                        "status": override_request.new_status,
                        "metadata": override_request.metadata
                    },
                    reason=override_request.reason
                )
                
                audit_log = await self.create_audit_log(audit_data, session)
                
                # Create and publish OverrideIssued event
                override_event = OverrideIssuedEvent(
                    audit_id=audit_log.id,
                    actor_id=rd_user.user_id,
                    actor_role=rd_user.role,
                    resource_type=override_request.resource_type.value,
                    resource_id=override_request.resource_id,
                    old_status=override_request.old_status,
                    new_status=override_request.new_status,
                    reason=override_request.reason,
                    timestamp=audit_log.created_at
                )
                
                # Publish event
                event_published = await self.event_service.publish_override_issued_event(override_event)
                
                if not event_published:
                    logger.warning(f"Failed to publish OverrideIssued event for audit {audit_log.id}")
                
                logger.info(f"Processed override for {override_request.resource_type}:{override_request.resource_id}")
                
                return OverrideResponse(
                    success=True,
                    audit_id=audit_log.id,
                    message=f"Override successfully processed for {override_request.resource_type}",
                    resource_type=override_request.resource_type.value,
                    resource_id=override_request.resource_id,
                    new_status=override_request.new_status
                )
                
        except Exception as e:
            logger.error(f"Failed to process override request: {e}")
            return OverrideResponse(
                success=False,
                message=f"Failed to process override: {str(e)}",
                resource_type=override_request.resource_type.value,
                resource_id=override_request.resource_id,
                new_status=override_request.new_status
            )
    
    async def get_audit_logs(
        self,
        resource_type: Optional[ResourceType] = None,
        resource_id: Optional[uuid.UUID] = None,
        actor_id: Optional[uuid.UUID] = None,
        action: Optional[AuditAction] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[AuditLogResponse]:
        """Get audit logs with optional filters"""
        try:
            async with await anext(get_db_session()) as session:
                query = select(AuditLog)
                
                # Apply filters
                conditions = []
                if resource_type:
                    conditions.append(AuditLog.resource_type == resource_type.value)
                if resource_id:
                    conditions.append(AuditLog.resource_id == resource_id)
                if actor_id:
                    conditions.append(AuditLog.actor_id == actor_id)
                if action:
                    conditions.append(AuditLog.action == action.value)
                
                if conditions:
                    query = query.where(and_(*conditions))
                
                # Order by created_at desc and apply pagination
                query = query.order_by(desc(AuditLog.created_at)).limit(limit).offset(offset)
                
                result = await session.execute(query)
                audit_logs = result.scalars().all()
                
                return [AuditLogResponse.from_orm(log) for log in audit_logs]
                
        except Exception as e:
            logger.error(f"Failed to get audit logs: {e}")
            return []
    
    async def get_resource_audit_history(
        self, 
        resource_type: ResourceType, 
        resource_id: uuid.UUID
    ) -> List[AuditLogResponse]:
        """Get complete audit history for a specific resource"""
        return await self.get_audit_logs(
            resource_type=resource_type,
            resource_id=resource_id
        )