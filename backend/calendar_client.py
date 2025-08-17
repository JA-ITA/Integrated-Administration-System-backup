"""
Calendar Service Client for ITADIAS Backend
Handles communication with the Calendar microservice
"""
import httpx
import logging
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
import uuid
from datetime import datetime

logger = logging.getLogger(__name__)

# Configuration
CALENDAR_SERVICE_URL = "http://localhost:8002"  # In production: "http://calendar-service:8002"

class CalendarHealthResponse(BaseModel):
    """Calendar service health response"""
    status: str
    service: str
    version: str
    database: str
    events: str
    cleanup_service: str

class SlotResponse(BaseModel):
    """Response model for calendar slots"""
    id: uuid.UUID
    hub_id: uuid.UUID
    start_time: datetime
    end_time: datetime
    status: str
    current_bookings: int
    max_capacity: int
    is_available: bool
    notes: Optional[str] = None
    created_at: datetime

class BookingRequest(BaseModel):
    """Request model for creating bookings"""
    slot_id: uuid.UUID
    candidate_id: uuid.UUID
    contact_email: str
    contact_phone: Optional[str] = None
    special_requirements: Optional[str] = None

class BookingResponse(BaseModel):
    """Response model for bookings"""
    id: uuid.UUID
    slot_id: uuid.UUID
    candidate_id: uuid.UUID
    status: str
    booking_reference: str
    contact_email: str
    contact_phone: Optional[str] = None
    special_requirements: Optional[str] = None
    created_at: datetime
    slot: Optional[SlotResponse] = None

class BookingCreateResponse(BaseModel):
    """Response model for booking creation"""
    booking: BookingResponse
    lock_expires_at: datetime
    message: str

class CalendarClient:
    """Client for interacting with the Calendar microservice"""
    
    def __init__(self, base_url: str = CALENDAR_SERVICE_URL):
        self.base_url = base_url.rstrip('/')
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def health_check(self) -> Optional[CalendarHealthResponse]:
        """Check if calendar service is healthy"""
        try:
            response = await self.client.get(f"{self.base_url}/health")
            response.raise_for_status()
            return CalendarHealthResponse(**response.json())
        except Exception as e:
            logger.error(f"Calendar service health check failed: {e}")
            return None
    
    async def get_available_slots(
        self, 
        hub_id: uuid.UUID, 
        date: str,
        duration_minutes: Optional[int] = None
    ) -> List[SlotResponse]:
        """Get available slots for a hub and date"""
        try:
            params = {
                "hub": str(hub_id),
                "date": date
            }
            if duration_minutes:
                params["duration_minutes"] = duration_minutes
            
            response = await self.client.get(
                f"{self.base_url}/api/v1/slots",
                params=params
            )
            response.raise_for_status()
            
            slots_data = response.json()
            return [SlotResponse(**slot) for slot in slots_data]
            
        except Exception as e:
            logger.error(f"Failed to get available slots: {e}")
            raise
    
    async def create_booking(self, booking_data: BookingRequest) -> BookingCreateResponse:
        """Create a new booking"""
        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/bookings",
                json=booking_data.dict()
            )
            response.raise_for_status()
            
            return BookingCreateResponse(**response.json())
            
        except Exception as e:
            logger.error(f"Failed to create booking: {e}")
            raise
    
    async def get_booking(self, booking_id: uuid.UUID) -> Optional[BookingResponse]:
        """Get booking by ID"""
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/bookings/{booking_id}"
            )
            response.raise_for_status()
            
            return BookingResponse(**response.json())
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise
        except Exception as e:
            logger.error(f"Failed to get booking: {e}")
            raise
    
    async def confirm_booking(self, booking_id: uuid.UUID) -> Dict[str, Any]:
        """Confirm a pending booking"""
        try:
            response = await self.client.patch(
                f"{self.base_url}/api/v1/bookings/{booking_id}/confirm"
            )
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            logger.error(f"Failed to confirm booking: {e}")
            raise
    
    async def cancel_booking(
        self, 
        booking_id: uuid.UUID, 
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """Cancel a booking"""
        try:
            params = {}
            if reason:
                params["reason"] = reason
            
            response = await self.client.patch(
                f"{self.base_url}/api/v1/bookings/{booking_id}/cancel",
                params=params
            )
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            logger.error(f"Failed to cancel booking: {e}")
            raise
    
    async def get_candidate_bookings(self, candidate_id: uuid.UUID) -> List[BookingResponse]:
        """Get all bookings for a candidate"""
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/candidates/{candidate_id}/bookings"
            )
            response.raise_for_status()
            
            bookings_data = response.json()
            return [BookingResponse(**booking) for booking in bookings_data]
            
        except Exception as e:
            logger.error(f"Failed to get candidate bookings: {e}")
            raise
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()

# Global calendar client instance
calendar_client = CalendarClient()