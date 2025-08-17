"""
Calendar Module - Test Scheduling and Appointment Management

This module handles all aspects of test scheduling and appointment management including:
- Test slot availability management
- Appointment booking and rescheduling
- Examiner availability scheduling
- Calendar integration and notifications
- Conflict detection and resolution
- Appointment status tracking
- Resource optimization for test centers

The module supports:
- Multiple test types (theory, practical, medical)
- Multiple test center locations
- Examiner specialization and preferences
- Automated reminders and notifications
- Waitlist management for popular slots
- Statistical reporting for resource planning
"""

from .models import Appointment, ExaminerAvailability, TestCenter, AppointmentHistory
from .schemas import (
    AppointmentCreate,
    AppointmentUpdate,
    AppointmentResponse,
    AvailabilityCreate,
    AvailabilityResponse,
    TestSlotResponse,
    AppointmentStatusUpdate,
    AppointmentStatus,
    TestType
)
from .service import CalendarService

__all__ = [
    # Models
    "Appointment",
    "ExaminerAvailability", 
    "TestCenter",
    "AppointmentHistory",
    
    # Schemas
    "AppointmentCreate",
    "AppointmentUpdate",
    "AppointmentResponse", 
    "AvailabilityCreate",
    "AvailabilityResponse",
    "TestSlotResponse",
    "AppointmentStatusUpdate",
    "AppointmentStatus",
    "TestType",
    
    # Service
    "CalendarService",
]