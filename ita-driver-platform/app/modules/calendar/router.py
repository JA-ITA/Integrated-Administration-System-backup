"""
Calendar Module Router - Test Scheduling and Appointment Management
Handles test scheduling, examiner availability, and appointment management.
"""

from typing import List, Optional
from datetime import datetime, date
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from modules.identity.dependencies import get_current_user, require_user_type, require_permissions
from .schemas import (
    AppointmentCreate,
    AppointmentUpdate,
    AppointmentResponse,
    AvailabilityCreate,
    AvailabilityResponse,
    TestSlotResponse,
    AppointmentStatusUpdate
)
from .service import CalendarService

router = APIRouter()


@router.get("/test-slots", response_model=List[TestSlotResponse])
async def get_available_test_slots(
    start_date: date = Query(..., description="Start date for slot search"),
    end_date: date = Query(..., description="End date for slot search"), 
    test_type: Optional[str] = Query(None, description="Filter by test type"),
    location: Optional[str] = Query(None, description="Filter by test location"),
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get available test slots within date range.
    
    - **start_date**: Start date for searching slots (YYYY-MM-DD)
    - **end_date**: End date for searching slots (YYYY-MM-DD)
    - **test_type**: Optional filter by test type (theory, practical)
    - **location**: Optional filter by test center location
    """
    service = CalendarService(db)
    
    slots = await service.get_available_slots(
        start_date=start_date,
        end_date=end_date,
        test_type=test_type,
        location=location
    )
    
    return slots


@router.post("/appointments", response_model=AppointmentResponse, status_code=status.HTTP_201_CREATED)
async def create_appointment(
    appointment_data: AppointmentCreate,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Book a new test appointment.
    
    - **test_type**: Type of test (theory, practical)
    - **test_date**: Date and time for the test
    - **location**: Test center location
    - **examiner_id**: Preferred examiner (optional)
    """
    service = CalendarService(db)
    
    try:
        appointment = await service.create_appointment(
            user_id=current_user.id,
            appointment_data=appointment_data
        )
        return appointment
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/appointments", response_model=List[AppointmentResponse])
async def get_user_appointments(
    status_filter: Optional[str] = Query(None, description="Filter by appointment status"),
    start_date: Optional[date] = Query(None, description="Filter from start date"),
    end_date: Optional[date] = Query(None, description="Filter to end date"),
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get current user's appointments with optional filtering.
    
    - **status**: Filter by status (scheduled, completed, cancelled, rescheduled)
    - **start_date**: Filter appointments from this date
    - **end_date**: Filter appointments to this date
    """
    service = CalendarService(db)
    
    appointments = await service.get_user_appointments(
        user_id=current_user.id,
        status_filter=status_filter,
        start_date=start_date,
        end_date=end_date
    )
    
    return appointments


@router.get("/appointments/{appointment_id}", response_model=AppointmentResponse)
async def get_appointment(
    appointment_id: str,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get specific appointment details."""
    service = CalendarService(db)
    
    appointment = await service.get_appointment_by_id(appointment_id)
    
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found"
        )
    
    # Check if user owns this appointment or has permission to view
    if appointment.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    return appointment


@router.put("/appointments/{appointment_id}", response_model=AppointmentResponse)
async def update_appointment(
    appointment_id: str,
    appointment_data: AppointmentUpdate,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update/reschedule an appointment.
    
    - **test_date**: New date and time for the test
    - **location**: New test center location (optional)
    - **notes**: Additional notes (optional)
    """
    service = CalendarService(db)
    
    # Check if appointment exists and user has access
    existing_appointment = await service.get_appointment_by_id(appointment_id)
    if not existing_appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found"
        )
    
    if existing_appointment.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    try:
        updated_appointment = await service.update_appointment(
            appointment_id=appointment_id,
            appointment_data=appointment_data,
            updated_by=current_user.id
        )
        return updated_appointment
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.patch("/appointments/{appointment_id}/status")
async def update_appointment_status(
    appointment_id: str,
    status_update: AppointmentStatusUpdate,
    current_user = Depends(require_user_type(["examiner", "admin", "super_admin"])),
    db: AsyncSession = Depends(get_db)
):
    """
    Update appointment status (examiner/admin only).
    
    - **status**: New status (completed, cancelled, no_show)
    - **notes**: Optional notes about status change
    - **score**: Test score (if completed)
    """
    service = CalendarService(db)
    
    try:
        appointment = await service.update_appointment_status(
            appointment_id=appointment_id,
            new_status=status_update.status,
            notes=status_update.notes,
            score=status_update.score,
            updated_by=current_user.id
        )
        
        if not appointment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Appointment not found"
            )
        
        return {
            "message": "Appointment status updated successfully",
            "appointment_id": appointment_id,
            "new_status": status_update.status
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/appointments/{appointment_id}")
async def cancel_appointment(
    appointment_id: str,
    reason: str = Query(..., description="Reason for cancellation"),
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Cancel an appointment."""
    service = CalendarService(db)
    
    # Check if appointment exists and user has access
    existing_appointment = await service.get_appointment_by_id(appointment_id)
    if not existing_appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found"
        )
    
    if existing_appointment.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    try:
        await service.cancel_appointment(
            appointment_id=appointment_id,
            reason=reason,
            cancelled_by=current_user.id
        )
        
        return {
            "message": "Appointment cancelled successfully",
            "appointment_id": appointment_id
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# Examiner Availability Management
@router.post("/availability", response_model=AvailabilityResponse, status_code=status.HTTP_201_CREATED)
async def create_availability(
    availability_data: AvailabilityCreate,
    current_user = Depends(require_user_type(["examiner", "admin", "super_admin"])),
    db: AsyncSession = Depends(get_db)
):
    """
    Create examiner availability slots.
    
    - **date**: Available date
    - **start_time**: Start time for availability
    - **end_time**: End time for availability
    - **location**: Test center location
    - **test_types**: List of test types examiner can conduct
    - **max_appointments**: Maximum appointments for this slot
    """
    service = CalendarService(db)
    
    try:
        availability = await service.create_availability(
            examiner_id=current_user.id,
            availability_data=availability_data
        )
        return availability
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/availability", response_model=List[AvailabilityResponse])
async def get_examiner_availability(
    examiner_id: Optional[str] = Query(None, description="Examiner ID (admin only)"),
    start_date: Optional[date] = Query(None, description="Filter from start date"),
    end_date: Optional[date] = Query(None, description="Filter to end date"),
    current_user = Depends(require_user_type(["examiner", "admin", "super_admin"])),
    db: AsyncSession = Depends(get_db)
):
    """Get examiner availability slots."""
    service = CalendarService(db)
    
    # Determine which examiner's availability to show
    target_examiner_id = examiner_id
    
    # If not admin and trying to view other examiner's availability
    if not current_user.is_admin and examiner_id and examiner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You can only view your own availability."
        )
    
    # If no examiner_id specified and user is examiner, show their own
    if not target_examiner_id and current_user.user_type == "examiner":
        target_examiner_id = current_user.id
    
    availability_slots = await service.get_examiner_availability(
        examiner_id=target_examiner_id,
        start_date=start_date,
        end_date=end_date
    )
    
    return availability_slots


@router.put("/availability/{availability_id}", response_model=AvailabilityResponse)
async def update_availability(
    availability_id: str,
    availability_data: AvailabilityCreate,
    current_user = Depends(require_user_type(["examiner", "admin", "super_admin"])),
    db: AsyncSession = Depends(get_db)
):
    """Update examiner availability slot."""
    service = CalendarService(db)
    
    # Check if availability exists and user has access
    existing_availability = await service.get_availability_by_id(availability_id)
    if not existing_availability:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Availability slot not found"
        )
    
    if existing_availability.examiner_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    try:
        updated_availability = await service.update_availability(
            availability_id=availability_id,
            availability_data=availability_data
        )
        return updated_availability
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/availability/{availability_id}")
async def delete_availability(
    availability_id: str,
    current_user = Depends(require_user_type(["examiner", "admin", "super_admin"])),
    db: AsyncSession = Depends(get_db)
):
    """Delete examiner availability slot."""
    service = CalendarService(db)
    
    # Check if availability exists and user has access
    existing_availability = await service.get_availability_by_id(availability_id)
    if not existing_availability:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Availability slot not found"
        )
    
    if existing_availability.examiner_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    try:
        await service.delete_availability(availability_id)
        
        return {
            "message": "Availability slot deleted successfully",
            "availability_id": availability_id
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# Admin endpoints for appointment management
@router.get("/admin/appointments", response_model=List[AppointmentResponse])
async def get_all_appointments(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    status_filter: Optional[str] = Query(None, description="Filter by status"),
    examiner_id: Optional[str] = Query(None, description="Filter by examiner"),
    location: Optional[str] = Query(None, description="Filter by location"),
    current_user = Depends(require_permissions(["view_all_appointments"])),
    db: AsyncSession = Depends(get_db)
):
    """Get all appointments with filtering and pagination (admin only)."""
    service = CalendarService(db)
    
    appointments = await service.get_all_appointments(
        page=page,
        limit=limit,
        status_filter=status_filter,
        examiner_id=examiner_id,
        location=location
    )
    
    return appointments


@router.get("/admin/dashboard-stats")
async def get_dashboard_stats(
    start_date: Optional[date] = Query(None, description="Stats from date"),
    end_date: Optional[date] = Query(None, description="Stats to date"),
    current_user = Depends(require_permissions(["view_dashboard"])),
    db: AsyncSession = Depends(get_db)
):
    """Get appointment statistics for admin dashboard."""
    service = CalendarService(db)
    
    stats = await service.get_appointment_stats(
        start_date=start_date,
        end_date=end_date
    )
    
    return stats