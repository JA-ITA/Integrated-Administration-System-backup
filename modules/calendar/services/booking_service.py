"""
Booking service for ITADIAS Calendar Microservice
"""
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from models import Booking, BookingCreate, BookingStatus, generate_booking_reference
from services.slot_service import SlotService

logger = logging.getLogger(__name__)

class BookingService:
    """Service for managing booking operations"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.slot_service = SlotService(db)
    
    async def create_booking_with_lock(
        self,
        booking_data: BookingCreate,
        lock_expires_at: datetime
    ) -> Booking:
        """Create a booking and lock the associated slot"""
        try:
            # Generate unique booking reference
            booking_reference = generate_booking_reference()
            
            # Create booking
            booking = Booking(
                slot_id=booking_data.slot_id,
                candidate_id=booking_data.candidate_id,
                booking_reference=booking_reference,
                contact_email=booking_data.contact_email,
                contact_phone=booking_data.contact_phone,
                special_requirements=booking_data.special_requirements,
                status=BookingStatus.PENDING
            )
            
            # Lock the slot
            session_id = f"booking_{booking_reference}"
            locked_slot = await self.slot_service.lock_slot(
                slot_id=booking_data.slot_id,
                locked_until=lock_expires_at,
                locked_by=session_id
            )
            
            if not locked_slot:
                raise Exception(f"Failed to lock slot {booking_data.slot_id}")
            
            # Save booking
            self.db.add(booking)
            await self.db.commit()
            await self.db.refresh(booking)
            
            logger.info(f"Created booking: {booking.id} with lock until {lock_expires_at}")
            return booking
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error creating booking with lock: {e}")
            raise
    
    async def get_booking_by_id(self, booking_id: uuid.UUID) -> Optional[Booking]:
        """Get booking by ID with slot information"""
        try:
            result = await self.db.execute(
                select(Booking)
                .options(selectinload(Booking.slot))
                .where(Booking.id == booking_id)
            )
            return result.scalar_one_or_none()
            
        except Exception as e:
            logger.error(f"Error getting booking by ID {booking_id}: {e}")
            raise
    
    async def get_booking_by_reference(self, booking_reference: str) -> Optional[Booking]:
        """Get booking by reference"""
        try:
            result = await self.db.execute(
                select(Booking)
                .options(selectinload(Booking.slot))
                .where(Booking.booking_reference == booking_reference)
            )
            return result.scalar_one_or_none()
            
        except Exception as e:
            logger.error(f"Error getting booking by reference {booking_reference}: {e}")
            raise
    
    async def get_bookings_by_candidate(self, candidate_id: uuid.UUID) -> List[Booking]:
        """Get all bookings for a candidate"""
        try:
            result = await self.db.execute(
                select(Booking)
                .options(selectinload(Booking.slot))
                .where(Booking.candidate_id == candidate_id)
                .order_by(Booking.created_at.desc())
            )
            return result.scalars().all()
            
        except Exception as e:
            logger.error(f"Error getting bookings for candidate {candidate_id}: {e}")
            raise
    
    async def confirm_booking(self, booking_id: uuid.UUID) -> Optional[Booking]:
        """Confirm a pending booking and book the slot"""
        try:
            booking = await self.get_booking_by_id(booking_id)
            if not booking:
                return None
            
            if booking.status != BookingStatus.PENDING:
                logger.warning(f"Booking {booking_id} is not pending, current status: {booking.status}")
                return booking
            
            # Mark slot as booked
            booked_slot = await self.slot_service.book_slot(booking.slot_id)
            if not booked_slot:
                raise Exception(f"Failed to book slot {booking.slot_id}")
            
            # Update booking status
            booking.status = BookingStatus.CONFIRMED
            booking.confirmation_sent_at = datetime.now(timezone.utc)
            
            await self.db.commit()
            await self.db.refresh(booking)
            
            logger.info(f"Booking confirmed: {booking_id}")
            return booking
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error confirming booking {booking_id}: {e}")
            raise
    
    async def cancel_booking(
        self,
        booking_id: uuid.UUID,
        reason: Optional[str] = None
    ) -> Optional[Booking]:
        """Cancel a booking and release the slot"""
        try:
            booking = await self.get_booking_by_id(booking_id)
            if not booking:
                return None
            
            if booking.status == BookingStatus.CANCELLED:
                logger.warning(f"Booking {booking_id} is already cancelled")
                return booking
            
            # Release the slot
            if booking.status == BookingStatus.CONFIRMED:
                released_slot = await self.slot_service.release_slot(booking.slot_id)
                if not released_slot:
                    logger.warning(f"Failed to release slot {booking.slot_id}")
            else:
                # Just unlock if it was pending
                unlocked_slot = await self.slot_service.unlock_slot(booking.slot_id)
                if not unlocked_slot:
                    logger.warning(f"Failed to unlock slot {booking.slot_id}")
            
            # Update booking status
            booking.status = BookingStatus.CANCELLED
            booking.cancelled_at = datetime.now(timezone.utc)
            booking.cancellation_reason = reason
            
            await self.db.commit()
            await self.db.refresh(booking)
            
            logger.info(f"Booking cancelled: {booking_id}")
            return booking
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error cancelling booking {booking_id}: {e}")
            raise
    
    async def get_pending_bookings_past_lock_time(self) -> List[Booking]:
        """Get pending bookings where the lock time has expired"""
        try:
            now = datetime.now(timezone.utc)
            
            # Get pending bookings where slot lock has expired
            result = await self.db.execute(
                select(Booking)
                .join(Booking.slot)
                .where(
                    Booking.status == BookingStatus.PENDING,
                    Booking.slot.locked_until <= now
                )
            )
            
            bookings = result.scalars().all()
            logger.info(f"Found {len(bookings)} pending bookings past lock time")
            return bookings
            
        except Exception as e:
            logger.error(f"Error getting pending bookings past lock time: {e}")
            raise
    
    async def cleanup_expired_bookings(self) -> int:
        """Clean up expired pending bookings"""
        try:
            expired_bookings = await self.get_pending_bookings_past_lock_time()
            
            count = 0
            for booking in expired_bookings:
                await self.cancel_booking(
                    booking.id,
                    reason="Automatically cancelled due to expired lock time"
                )
                count += 1
            
            if count > 0:
                logger.info(f"Cleaned up {count} expired bookings")
            
            return count
            
        except Exception as e:
            logger.error(f"Error cleaning up expired bookings: {e}")
            raise