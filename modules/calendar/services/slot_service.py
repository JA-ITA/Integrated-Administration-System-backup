"""
Slot service for ITADIAS Calendar Microservice
"""
import uuid
import logging
from datetime import datetime, timezone, date, timedelta
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from models import Slot, Hub, SlotStatus

logger = logging.getLogger(__name__)

class SlotService:
    """Service for managing slot operations"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def hub_exists(self, hub_id: uuid.UUID) -> bool:
        """Check if hub exists"""
        try:
            result = await self.db.execute(
                select(Hub).where(Hub.id == hub_id)
            )
            return result.scalar_one_or_none() is not None
            
        except Exception as e:
            logger.error(f"Error checking if hub exists {hub_id}: {e}")
            raise
    
    async def get_slot_by_id(self, slot_id: uuid.UUID) -> Optional[Slot]:
        """Get slot by ID"""
        try:
            result = await self.db.execute(
                select(Slot).where(Slot.id == slot_id)
            )
            return result.scalar_one_or_none()
            
        except Exception as e:
            logger.error(f"Error getting slot by ID {slot_id}: {e}")
            raise
    
    async def get_available_slots(
        self,
        hub_id: uuid.UUID,
        query_date: date,
        duration_minutes: Optional[int] = None
    ) -> List[Slot]:
        """Get available slots for a hub on a specific date"""
        try:
            # Define date range for the query (start and end of the day)
            start_of_day = datetime.combine(query_date, datetime.min.time().replace(tzinfo=timezone.utc))
            end_of_day = datetime.combine(query_date, datetime.max.time().replace(tzinfo=timezone.utc))
            
            # Base query for slots on the specified date
            query = select(Slot).where(
                and_(
                    Slot.hub_id == hub_id,
                    Slot.start_time >= start_of_day,
                    Slot.start_time <= end_of_day,
                    Slot.status == SlotStatus.AVAILABLE,
                    or_(
                        Slot.locked_until.is_(None),
                        Slot.locked_until <= datetime.now(timezone.utc)
                    ),
                    Slot.current_bookings < Slot.max_capacity,
                    Slot.start_time > datetime.now(timezone.utc)  # Only future slots
                )
            ).order_by(Slot.start_time)
            
            # Add duration filter if specified
            if duration_minutes:
                duration_timedelta = timedelta(minutes=duration_minutes)
                query = query.where(
                    (Slot.end_time - Slot.start_time) >= duration_timedelta
                )
            
            result = await self.db.execute(query)
            slots = result.scalars().all()
            
            logger.info(f"Found {len(slots)} available slots for hub {hub_id} on {query_date}")
            return slots
            
        except Exception as e:
            logger.error(f"Error getting available slots: {e}")
            raise
    
    async def get_slots_in_date_range(
        self,
        hub_id: uuid.UUID,
        start_date: date,
        end_date: date
    ) -> List[Slot]:
        """Get all slots for a hub within a date range"""
        try:
            start_datetime = datetime.combine(start_date, datetime.min.time().replace(tzinfo=timezone.utc))
            end_datetime = datetime.combine(end_date, datetime.max.time().replace(tzinfo=timezone.utc))
            
            query = select(Slot).where(
                and_(
                    Slot.hub_id == hub_id,
                    Slot.start_time >= start_datetime,
                    Slot.start_time <= end_datetime
                )
            ).order_by(Slot.start_time)
            
            result = await self.db.execute(query)
            slots = result.scalars().all()
            
            logger.info(f"Found {len(slots)} slots for hub {hub_id} from {start_date} to {end_date}")
            return slots
            
        except Exception as e:
            logger.error(f"Error getting slots in date range: {e}")
            raise
    
    async def lock_slot(
        self,
        slot_id: uuid.UUID,
        locked_until: datetime,
        locked_by: str
    ) -> Optional[Slot]:
        """Lock a slot for booking"""
        try:
            slot = await self.get_slot_by_id(slot_id)
            if not slot:
                return None
            
            # Check if slot is available for locking
            if not slot.is_available:
                logger.warning(f"Slot {slot_id} is not available for locking")
                return None
            
            # Lock the slot
            slot.status = SlotStatus.LOCKED
            slot.locked_until = locked_until
            slot.locked_by = locked_by
            
            await self.db.commit()
            await self.db.refresh(slot)
            
            logger.info(f"Slot {slot_id} locked until {locked_until}")
            return slot
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error locking slot {slot_id}: {e}")
            raise
    
    async def unlock_slot(self, slot_id: uuid.UUID) -> Optional[Slot]:
        """Unlock a slot"""
        try:
            slot = await self.get_slot_by_id(slot_id)
            if not slot:
                return None
            
            slot.status = SlotStatus.AVAILABLE
            slot.locked_until = None
            slot.locked_by = None
            
            await self.db.commit()
            await self.db.refresh(slot)
            
            logger.info(f"Slot {slot_id} unlocked")
            return slot
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error unlocking slot {slot_id}: {e}")
            raise
    
    async def book_slot(self, slot_id: uuid.UUID) -> Optional[Slot]:
        """Mark a slot as booked"""
        try:
            slot = await self.get_slot_by_id(slot_id)
            if not slot:
                return None
            
            slot.status = SlotStatus.BOOKED
            slot.current_bookings += 1
            slot.locked_until = None
            slot.locked_by = None
            
            await self.db.commit()
            await self.db.refresh(slot)
            
            logger.info(f"Slot {slot_id} marked as booked")
            return slot
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error booking slot {slot_id}: {e}")
            raise
    
    async def release_slot(self, slot_id: uuid.UUID) -> Optional[Slot]:
        """Release a booked slot back to available"""
        try:
            slot = await self.get_slot_by_id(slot_id)
            if not slot:
                return None
            
            if slot.current_bookings > 0:
                slot.current_bookings -= 1
            
            # If no more bookings and slot has capacity, make it available
            if slot.current_bookings < slot.max_capacity:
                slot.status = SlotStatus.AVAILABLE
            
            slot.locked_until = None
            slot.locked_by = None
            
            await self.db.commit()
            await self.db.refresh(slot)
            
            logger.info(f"Slot {slot_id} released")
            return slot
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error releasing slot {slot_id}: {e}")
            raise
    
    async def cleanup_expired_locks(self) -> int:
        """Clean up expired slot locks"""
        try:
            now = datetime.now(timezone.utc)
            
            # Find slots with expired locks
            query = select(Slot).where(
                and_(
                    Slot.status == SlotStatus.LOCKED,
                    Slot.locked_until <= now
                )
            )
            
            result = await self.db.execute(query)
            expired_slots = result.scalars().all()
            
            # Unlock expired slots
            count = 0
            for slot in expired_slots:
                slot.status = SlotStatus.AVAILABLE
                slot.locked_until = None
                slot.locked_by = None
                count += 1
            
            if count > 0:
                await self.db.commit()
                logger.info(f"Cleaned up {count} expired slot locks")
            
            return count
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error cleaning up expired locks: {e}")
            raise