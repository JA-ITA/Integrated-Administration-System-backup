"""
Cleanup service for expired locks and bookings
"""
import asyncio
import logging
from datetime import timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from services.slot_service import SlotService
from services.booking_service import BookingService
from database import get_db_session
from config import config

logger = logging.getLogger(__name__)

class CleanupService:
    """Service for cleaning up expired locks and bookings"""
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.is_running = False
    
    async def start(self):
        """Start the cleanup service"""
        try:
            # Schedule cleanup job to run every few minutes
            self.scheduler.add_job(
                self.cleanup_expired_items,
                'interval',
                minutes=config.booking.cleanup_interval_minutes,
                id='cleanup_expired_items',
                replace_existing=True
            )
            
            self.scheduler.start()
            self.is_running = True
            
            logger.info(f"Cleanup service started, running every {config.booking.cleanup_interval_minutes} minutes")
            
        except Exception as e:
            logger.error(f"Failed to start cleanup service: {e}")
            raise
    
    async def stop(self):
        """Stop the cleanup service"""
        try:
            if self.is_running:
                self.scheduler.shutdown()
                self.is_running = False
                logger.info("Cleanup service stopped")
                
        except Exception as e:
            logger.error(f"Error stopping cleanup service: {e}")
    
    async def cleanup_expired_items(self):
        """Clean up expired slot locks and bookings"""
        try:
            logger.debug("Running cleanup of expired items")
            
            async with get_db_session() as db:
                slot_service = SlotService(db)
                booking_service = BookingService(db)
                
                # Clean up expired slot locks
                expired_locks = await slot_service.cleanup_expired_locks()
                
                # Clean up expired bookings
                expired_bookings = await booking_service.cleanup_expired_bookings()
                
                if expired_locks > 0 or expired_bookings > 0:
                    logger.info(f"Cleanup completed: {expired_locks} expired locks, {expired_bookings} expired bookings")
                
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
    
    async def manual_cleanup(self):
        """Manually trigger cleanup (for testing/admin use)"""
        logger.info("Manual cleanup triggered")
        await self.cleanup_expired_items()
    
    def get_status(self) -> dict:
        """Get cleanup service status"""
        return {
            "is_running": self.is_running,
            "interval_minutes": config.booking.cleanup_interval_minutes,
            "next_run": self.scheduler.get_job('cleanup_expired_items').next_run_time if self.is_running else None
        }