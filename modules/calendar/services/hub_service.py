"""
Hub service for ITADIAS Calendar Microservice
"""
import uuid
import logging
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models import Hub, HubCreate

logger = logging.getLogger(__name__)

class HubService:
    """Service for managing hub operations"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_hub(self, hub_data: HubCreate) -> Hub:
        """Create a new hub"""
        try:
            hub = Hub(
                name=hub_data.name,
                location=hub_data.location,
                address=hub_data.address,
                timezone=hub_data.timezone,
                operating_hours_start=hub_data.operating_hours_start,
                operating_hours_end=hub_data.operating_hours_end,
                operating_days=hub_data.operating_days,
                capacity=hub_data.capacity,
                description=hub_data.description,
                contact_info=hub_data.contact_info
            )
            
            self.db.add(hub)
            await self.db.commit()
            await self.db.refresh(hub)
            
            logger.info(f"Created hub: {hub.id}")
            return hub
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error creating hub: {e}")
            raise
    
    async def get_hub_by_id(self, hub_id: uuid.UUID) -> Optional[Hub]:
        """Get hub by ID"""
        try:
            result = await self.db.execute(
                select(Hub).where(Hub.id == hub_id)
            )
            return result.scalar_one_or_none()
            
        except Exception as e:
            logger.error(f"Error getting hub by ID {hub_id}: {e}")
            raise
    
    async def get_hub_by_name(self, name: str) -> Optional[Hub]:
        """Get hub by name"""
        try:
            result = await self.db.execute(
                select(Hub).where(Hub.name == name)
            )
            return result.scalar_one_or_none()
            
        except Exception as e:
            logger.error(f"Error getting hub by name {name}: {e}")
            raise
    
    async def list_hubs(
        self, 
        skip: int = 0, 
        limit: int = 100, 
        active_only: bool = True
    ) -> List[Hub]:
        """List hubs with pagination"""
        try:
            query = select(Hub)
            
            if active_only:
                query = query.where(Hub.is_active == True)
            
            query = query.offset(skip).limit(limit).order_by(Hub.created_at.desc())
            
            result = await self.db.execute(query)
            return result.scalars().all()
            
        except Exception as e:
            logger.error(f"Error listing hubs: {e}")
            raise
    
    async def update_hub(self, hub_id: uuid.UUID, hub_data: HubCreate) -> Optional[Hub]:
        """Update hub"""
        try:
            hub = await self.get_hub_by_id(hub_id)
            if not hub:
                return None
            
            # Update fields
            hub.name = hub_data.name
            hub.location = hub_data.location
            hub.address = hub_data.address
            hub.timezone = hub_data.timezone
            hub.operating_hours_start = hub_data.operating_hours_start
            hub.operating_hours_end = hub_data.operating_hours_end
            hub.operating_days = hub_data.operating_days
            hub.capacity = hub_data.capacity
            hub.description = hub_data.description
            hub.contact_info = hub_data.contact_info
            
            await self.db.commit()
            await self.db.refresh(hub)
            
            logger.info(f"Updated hub: {hub_id}")
            return hub
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error updating hub {hub_id}: {e}")
            raise
    
    async def delete_hub(self, hub_id: uuid.UUID) -> bool:
        """Soft delete hub by setting is_active to False"""
        try:
            hub = await self.get_hub_by_id(hub_id)
            if not hub:
                return False
            
            hub.is_active = False
            await self.db.commit()
            
            logger.info(f"Deleted hub: {hub_id}")
            return True
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error deleting hub {hub_id}: {e}")
            raise