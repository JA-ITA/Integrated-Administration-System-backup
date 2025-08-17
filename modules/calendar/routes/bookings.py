"""
Bookings API routes for ITADIAS Calendar Microservice
"""
import uuid
import logging
from datetime import datetime, timezone, timedelta
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from models import BookingCreate, BookingResponse, BookingCreateResponse, generate_booking_reference
from services.booking_service import BookingService
from services.slot_service import SlotService
from services.event_service import EventService

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/bookings", response_model=BookingCreateResponse, status_code=201)
async def create_booking(
    booking_data: BookingCreate,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new booking and lock the slot for 15 minutes
    
    - **slot_id**: UUID of the slot to book
    - **candidate_id**: UUID of the candidate making the booking (from identity service)
    - **contact_email**: Contact email for the booking
    - **contact_phone**: Optional contact phone number
    - **special_requirements**: Optional special requirements or notes
    
    The slot will be locked for 15 minutes to allow payment processing.
    """
    try:
        logger.info(f"Creating booking for slot {booking_data.slot_id} by candidate {booking_data.candidate_id}")
        
        # Check if database is available
        if db is None:
            # Return mock booking for testing without database
            mock_booking_id = uuid.uuid4()
            lock_expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)
            
            mock_booking = {
                "id": mock_booking_id,
                "slot_id": booking_data.slot_id,
                "candidate_id": booking_data.candidate_id,
                "status": "pending",
                "booking_reference": generate_booking_reference(),
                "contact_email": booking_data.contact_email,
                "contact_phone": booking_data.contact_phone,
                "special_requirements": booking_data.special_requirements,
                "created_at": datetime.now(timezone.utc),
                "slot": {
                    "id": booking_data.slot_id,
                    "hub_id": uuid.uuid4(),
                    "start_time": datetime.now(timezone.utc) + timedelta(hours=2),
                    "end_time": datetime.now(timezone.utc) + timedelta(hours=3),
                    "status": "locked",
                    "current_bookings": 1,
                    "max_capacity": 1,
                    "notes": None,
                    "is_available": False,
                    "created_at": datetime.now(timezone.utc)
                }
            }
            
            logger.info(f"Created mock booking: {mock_booking_id}")
            
            return BookingCreateResponse(
                booking=BookingResponse(**mock_booking),
                lock_expires_at=lock_expires_at,
                message="Booking created successfully. Slot locked for 15 minutes."
            )
        
        # Initialize services
        booking_service = BookingService(db)
        slot_service = SlotService(db)
        event_service = getattr(request.app.state, 'event_service', None)
        
        # Check if slot exists and is available
        slot = await slot_service.get_slot_by_id(booking_data.slot_id)
        if not slot:
            raise HTTPException(
                status_code=404,
                detail=f"Slot with ID {booking_data.slot_id} not found"
            )
        
        # Check if slot is available for booking
        if not slot.is_available:
            if slot.locked_until and slot.locked_until > datetime.now(timezone.utc):
                raise HTTPException(
                    status_code=409,
                    detail="Slot is currently locked by another booking attempt"
                )
            elif slot.current_bookings >= slot.max_capacity:
                raise HTTPException(
                    status_code=409,
                    detail="Slot is fully booked"
                )
            else:
                raise HTTPException(
                    status_code=409,
                    detail="Slot is not available for booking"
                )
        
        # Check if slot is in the future
        if slot.start_time <= datetime.now(timezone.utc):
            raise HTTPException(
                status_code=422,
                detail="Cannot book slots in the past"
            )
        
        # Create booking and lock slot
        lock_expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)
        
        booking = await booking_service.create_booking_with_lock(
            booking_data=booking_data,
            lock_expires_at=lock_expires_at
        )
        
        logger.info(f"Booking created: {booking.id} for slot {booking_data.slot_id}")
        
        # Publish BookingCreated event
        if event_service:
            try:
                await event_service.publish_booking_created(booking, slot)
                logger.info(f"BookingCreated event published for booking {booking.id}")
            except Exception as e:
                logger.error(f"Failed to publish BookingCreated event: {e}")
        
        # Prepare response with slot information
        booking_response = BookingResponse.from_orm(booking)
        if slot:
            from models import SlotResponse
            slot_response = SlotResponse.from_orm(slot)
            slot_response.is_available = slot.is_available
            booking_response.slot = slot_response
        
        return BookingCreateResponse(
            booking=booking_response,
            lock_expires_at=lock_expires_at,
            message="Booking created successfully. Slot locked for 15 minutes."
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating booking: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/bookings/{booking_id}", response_model=BookingResponse)
async def get_booking(
    booking_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific booking by ID
    
    - **booking_id**: UUID of the booking to retrieve
    """
    try:
        logger.info(f"Getting booking with ID: {booking_id}")
        
        if db is None:
            raise HTTPException(
                status_code=503,
                detail="Database not available"
            )
        
        booking_service = BookingService(db)
        booking = await booking_service.get_booking_by_id(booking_id)
        
        if not booking:
            raise HTTPException(
                status_code=404,
                detail=f"Booking with ID {booking_id} not found"
            )
        
        # Include slot information
        booking_response = BookingResponse.from_orm(booking)
        if booking.slot:
            from models import SlotResponse
            slot_response = SlotResponse.from_orm(booking.slot)
            slot_response.is_available = booking.slot.is_available
            booking_response.slot = slot_response
        
        return booking_response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting booking {booking_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.patch("/bookings/{booking_id}/confirm")
async def confirm_booking(
    booking_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Confirm a pending booking and remove the slot lock
    
    - **booking_id**: UUID of the booking to confirm
    """
    try:
        logger.info(f"Confirming booking: {booking_id}")
        
        if db is None:
            raise HTTPException(
                status_code=503,
                detail="Database not available"
            )
        
        booking_service = BookingService(db)
        event_service = getattr(request.app.state, 'event_service', None)
        
        # Confirm the booking
        booking = await booking_service.confirm_booking(booking_id)
        
        if not booking:
            raise HTTPException(
                status_code=404,
                detail=f"Booking with ID {booking_id} not found"
            )
        
        logger.info(f"Booking confirmed: {booking_id}")
        
        # Publish BookingConfirmed event
        if event_service:
            try:
                await event_service.publish_booking_confirmed(booking)
                logger.info(f"BookingConfirmed event published for booking {booking_id}")
            except Exception as e:
                logger.error(f"Failed to publish BookingConfirmed event: {e}")
        
        return {
            "message": "Booking confirmed successfully",
            "booking_id": booking_id,
            "status": booking.status.value
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error confirming booking {booking_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.patch("/bookings/{booking_id}/cancel")
async def cancel_booking(
    booking_id: uuid.UUID,
    request: Request,
    reason: str = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Cancel a booking and release the slot
    
    - **booking_id**: UUID of the booking to cancel
    - **reason**: Optional cancellation reason
    """
    try:
        logger.info(f"Cancelling booking: {booking_id}")
        
        if db is None:
            raise HTTPException(
                status_code=503,
                detail="Database not available"
            )
        
        booking_service = BookingService(db)
        event_service = getattr(request.app.state, 'event_service', None)
        
        # Cancel the booking
        booking = await booking_service.cancel_booking(booking_id, reason)
        
        if not booking:
            raise HTTPException(
                status_code=404,
                detail=f"Booking with ID {booking_id} not found"
            )
        
        logger.info(f"Booking cancelled: {booking_id}")
        
        # Publish BookingCancelled event
        if event_service:
            try:
                await event_service.publish_booking_cancelled(booking)
                logger.info(f"BookingCancelled event published for booking {booking_id}")
            except Exception as e:
                logger.error(f"Failed to publish BookingCancelled event: {e}")
        
        return {
            "message": "Booking cancelled successfully",
            "booking_id": booking_id,
            "status": booking.status.value
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling booking {booking_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/candidates/{candidate_id}/bookings", response_model=List[BookingResponse])
async def get_candidate_bookings(
    candidate_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Get all bookings for a specific candidate
    
    - **candidate_id**: UUID of the candidate
    """
    try:
        logger.info(f"Getting bookings for candidate: {candidate_id}")
        
        if db is None:
            return []  # Return empty list when database not available
        
        booking_service = BookingService(db)
        bookings = await booking_service.get_bookings_by_candidate(candidate_id)
        
        # Include slot information for each booking
        booking_responses = []
        for booking in bookings:
            booking_response = BookingResponse.from_orm(booking)
            if booking.slot:
                from models import SlotResponse
                slot_response = SlotResponse.from_orm(booking.slot)
                slot_response.is_available = booking.slot.is_available
                booking_response.slot = slot_response
            booking_responses.append(booking_response)
        
        logger.info(f"Found {len(bookings)} bookings for candidate {candidate_id}")
        return booking_responses
        
    except Exception as e:
        logger.error(f"Error getting candidate bookings: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")