"""
Slots API routes for ITADIAS Calendar Microservice
"""
import uuid
import logging
from datetime import datetime, date, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from database import get_db
from models import Slot, Hub, SlotResponse, SlotAvailabilityQuery
from services.slot_service import SlotService

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/slots", response_model=List[SlotResponse])
async def get_available_slots(
    hub: uuid.UUID = Query(..., description="Hub ID to query slots for"),
    date: str = Query(..., description="Date in YYYY-MM-DD format"),
    duration_minutes: Optional[int] = Query(None, ge=15, le=480, description="Minimum slot duration in minutes"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get available slots for a specific hub and date
    
    - **hub**: UUID of the hub to query slots for
    - **date**: Date in YYYY-MM-DD format
    - **duration_minutes**: Optional minimum slot duration filter
    
    Returns list of available slots that can be booked.
    """
    try:
        logger.info(f"Getting available slots for hub {hub} on date {date}")
        
        # Check if database is available
        if db is None:
            # Return mock data for testing without database
            mock_slots = [
                {
                    "id": uuid.uuid4(),
                    "hub_id": hub,
                    "start_time": datetime.now(timezone.utc).replace(hour=9, minute=0, second=0, microsecond=0),
                    "end_time": datetime.now(timezone.utc).replace(hour=10, minute=0, second=0, microsecond=0),
                    "status": "available",
                    "current_bookings": 0,
                    "max_capacity": 1,
                    "notes": None,
                    "is_available": True,
                    "created_at": datetime.now(timezone.utc)
                },
                {
                    "id": uuid.uuid4(),
                    "hub_id": hub,
                    "start_time": datetime.now(timezone.utc).replace(hour=11, minute=0, second=0, microsecond=0),
                    "end_time": datetime.now(timezone.utc).replace(hour=12, minute=0, second=0, microsecond=0),
                    "status": "available",
                    "current_bookings": 0,
                    "max_capacity": 1,
                    "notes": None,
                    "is_available": True,
                    "created_at": datetime.now(timezone.utc)
                }
            ]
            
            logger.info(f"Returning {len(mock_slots)} mock slots")
            return [SlotResponse(**slot) for slot in mock_slots]
        
        # Validate date format
        try:
            query_date = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(
                status_code=422,
                detail="Invalid date format. Use YYYY-MM-DD"
            )
        
        # Initialize service
        slot_service = SlotService(db)
        
        # Verify hub exists
        hub_exists = await slot_service.hub_exists(hub)
        if not hub_exists:
            raise HTTPException(
                status_code=404,
                detail=f"Hub with ID {hub} not found"
            )
        
        # Get available slots
        slots = await slot_service.get_available_slots(
            hub_id=hub,
            query_date=query_date,
            duration_minutes=duration_minutes
        )
        
        logger.info(f"Found {len(slots)} available slots for hub {hub} on {date}")
        
        # Convert to response models
        slot_responses = []
        for slot in slots:
            slot_response = SlotResponse.from_orm(slot)
            slot_response.is_available = slot.is_available
            slot_responses.append(slot_response)
        
        return slot_responses
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting available slots: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/slots/{slot_id}", response_model=SlotResponse)
async def get_slot(
    slot_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific slot by ID
    
    - **slot_id**: UUID of the slot to retrieve
    """
    try:
        logger.info(f"Getting slot with ID: {slot_id}")
        
        if db is None:
            raise HTTPException(
                status_code=503,
                detail="Database not available"
            )
        
        slot_service = SlotService(db)
        slot = await slot_service.get_slot_by_id(slot_id)
        
        if not slot:
            raise HTTPException(
                status_code=404,
                detail=f"Slot with ID {slot_id} not found"
            )
        
        slot_response = SlotResponse.from_orm(slot)
        slot_response.is_available = slot.is_available
        
        return slot_response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting slot {slot_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/hubs/{hub_id}/slots/calendar")
async def get_hub_calendar(
    hub_id: uuid.UUID,
    start_date: str = Query(..., description="Start date in YYYY-MM-DD format"),
    end_date: str = Query(..., description="End date in YYYY-MM-DD format"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get calendar view of all slots for a hub within date range
    
    - **hub_id**: UUID of the hub
    - **start_date**: Start date in YYYY-MM-DD format
    - **end_date**: End date in YYYY-MM-DD format
    """
    try:
        logger.info(f"Getting calendar for hub {hub_id} from {start_date} to {end_date}")
        
        # Validate date formats
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
            end_dt = datetime.strptime(end_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(
                status_code=422,
                detail="Invalid date format. Use YYYY-MM-DD"
            )
        
        if start_dt > end_dt:
            raise HTTPException(
                status_code=422,
                detail="Start date must be before or equal to end date"
            )
        
        if db is None:
            # Return mock calendar data
            return {
                "hub_id": hub_id,
                "start_date": start_date,
                "end_date": end_date,
                "slots": [],
                "summary": {
                    "total_slots": 0,
                    "available_slots": 0,
                    "booked_slots": 0,
                    "locked_slots": 0
                }
            }
        
        slot_service = SlotService(db)
        
        # Verify hub exists
        hub_exists = await slot_service.hub_exists(hub_id)
        if not hub_exists:
            raise HTTPException(
                status_code=404,
                detail=f"Hub with ID {hub_id} not found"
            )
        
        # Get all slots in date range
        slots = await slot_service.get_slots_in_date_range(hub_id, start_dt, end_dt)
        
        # Calculate summary statistics
        total_slots = len(slots)
        available_slots = sum(1 for slot in slots if slot.is_available)
        booked_slots = sum(1 for slot in slots if slot.status.value == "booked")
        locked_slots = sum(1 for slot in slots if slot.status.value == "locked")
        
        return {
            "hub_id": hub_id,
            "start_date": start_date,
            "end_date": end_date,
            "slots": [SlotResponse.from_orm(slot) for slot in slots],
            "summary": {
                "total_slots": total_slots,
                "available_slots": available_slots,
                "booked_slots": booked_slots,
                "locked_slots": locked_slots
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting hub calendar: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")