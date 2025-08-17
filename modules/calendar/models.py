"""
SQLAlchemy models for ITADIAS Calendar Microservice
"""
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, List
from sqlalchemy import Column, String, DateTime, Boolean, Integer, Text, ForeignKey, Date, Time, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from pydantic import BaseModel, Field, validator
import enum
from database import Base
from config import config

# Enums

class BookingStatus(str, enum.Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"

class SlotStatus(str, enum.Enum):
    AVAILABLE = "available"
    LOCKED = "locked"
    BOOKED = "booked"
    UNAVAILABLE = "unavailable"

# SQLAlchemy Models

class Hub(Base):
    """Hub model for calendar schema"""
    __tablename__ = "hubs"
    __table_args__ = {"schema": config.db.schema}
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    location = Column(String(500), nullable=False)
    address = Column(Text, nullable=True)
    timezone = Column(String(50), default="UTC", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    operating_hours_start = Column(Time, nullable=False)  # e.g., 09:00
    operating_hours_end = Column(Time, nullable=False)    # e.g., 17:00
    operating_days = Column(String(20), default="1,2,3,4,5", nullable=False)  # Mon=1, Sun=7
    capacity = Column(Integer, default=1, nullable=False)  # Number of concurrent slots
    description = Column(Text, nullable=True)
    contact_info = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    slots = relationship("Slot", back_populates="hub", cascade="all, delete-orphan")

class Slot(Base):
    """Slot model for calendar schema"""
    __tablename__ = "slots"
    __table_args__ = {"schema": config.db.schema}
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    hub_id = Column(UUID(as_uuid=True), ForeignKey(f"{config.db.schema}.hubs.id"), nullable=False)
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)
    status = Column(Enum(SlotStatus), default=SlotStatus.AVAILABLE, nullable=False)
    locked_until = Column(DateTime(timezone=True), nullable=True)  # For 15-minute lock
    locked_by = Column(String(255), nullable=True)  # Session/user identifier
    max_capacity = Column(Integer, default=1, nullable=False)
    current_bookings = Column(Integer, default=0, nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    hub = relationship("Hub", back_populates="slots")
    bookings = relationship("Booking", back_populates="slot", cascade="all, delete-orphan")
    
    @property
    def is_available(self) -> bool:
        """Check if slot is available for booking"""
        now = datetime.now(timezone.utc)
        
        # Check if slot is locked and lock hasn't expired
        if self.locked_until and self.locked_until > now:
            return False
            
        # Check if slot has capacity
        if self.current_bookings >= self.max_capacity:
            return False
            
        # Check if slot is in the past
        if self.start_time <= now:
            return False
            
        return self.status == SlotStatus.AVAILABLE

class Booking(Base):
    """Booking model for calendar schema"""
    __tablename__ = "bookings"
    __table_args__ = {"schema": config.db.schema}
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slot_id = Column(UUID(as_uuid=True), ForeignKey(f"{config.db.schema}.slots.id"), nullable=False)
    candidate_id = Column(UUID(as_uuid=True), nullable=False)  # Reference to identity service
    status = Column(Enum(BookingStatus), default=BookingStatus.PENDING, nullable=False)
    booking_reference = Column(String(50), unique=True, nullable=False)
    contact_email = Column(String(255), nullable=False)
    contact_phone = Column(String(20), nullable=True)
    special_requirements = Column(Text, nullable=True)
    confirmation_sent_at = Column(DateTime(timezone=True), nullable=True)
    reminder_sent_at = Column(DateTime(timezone=True), nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    cancellation_reason = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    slot = relationship("Slot", back_populates="bookings")

# Pydantic Models for API

class HubBase(BaseModel):
    """Base hub schema"""
    name: str = Field(..., min_length=1, max_length=255)
    location: str = Field(..., min_length=1, max_length=500)
    address: Optional[str] = None
    timezone: str = Field(default="UTC", max_length=50)
    operating_hours_start: str = Field(..., description="Operating start time in HH:MM format")
    operating_hours_end: str = Field(..., description="Operating end time in HH:MM format")
    operating_days: str = Field(default="1,2,3,4,5", description="Comma-separated operating days (1=Mon, 7=Sun)")
    capacity: int = Field(default=1, ge=1, le=100)
    description: Optional[str] = None
    contact_info: Optional[str] = None

class HubCreate(HubBase):
    """Schema for creating a hub"""
    pass

class HubResponse(HubBase):
    """Schema for hub response"""
    id: uuid.UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class SlotBase(BaseModel):
    """Base slot schema"""
    start_time: datetime
    end_time: datetime
    max_capacity: int = Field(default=1, ge=1, le=10)
    notes: Optional[str] = None

class SlotCreate(SlotBase):
    """Schema for creating a slot"""
    hub_id: uuid.UUID

class SlotResponse(SlotBase):
    """Schema for slot response"""
    id: uuid.UUID
    hub_id: uuid.UUID
    status: SlotStatus
    current_bookings: int
    is_available: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

class SlotAvailabilityQuery(BaseModel):
    """Query parameters for slot availability"""
    hub: uuid.UUID = Field(..., description="Hub ID to query slots for")
    date: str = Field(..., description="Date in YYYY-MM-DD format")
    duration_minutes: Optional[int] = Field(None, ge=15, le=480, description="Minimum slot duration in minutes")

class BookingBase(BaseModel):
    """Base booking schema"""
    contact_email: str = Field(..., description="Contact email for the booking")
    contact_phone: Optional[str] = Field(None, description="Contact phone number")
    special_requirements: Optional[str] = Field(None, max_length=1000)

class BookingCreate(BookingBase):
    """Schema for creating a booking"""
    slot_id: uuid.UUID
    candidate_id: uuid.UUID

class BookingResponse(BookingBase):
    """Schema for booking response"""
    id: uuid.UUID
    slot_id: uuid.UUID
    candidate_id: uuid.UUID
    status: BookingStatus
    booking_reference: str
    created_at: datetime
    
    # Include slot information
    slot: Optional[SlotResponse] = None
    
    class Config:
        from_attributes = True

class BookingCreateResponse(BaseModel):
    """Response schema for booking creation"""
    booking: BookingResponse
    lock_expires_at: datetime
    message: str

class ErrorResponse(BaseModel):
    """Standard error response schema"""
    error: str
    detail: Optional[str] = None
    code: Optional[str] = None

# Utility functions for booking references
def generate_booking_reference() -> str:
    """Generate a unique booking reference"""
    import random
    import string
    timestamp = datetime.now().strftime("%y%m%d")
    random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"BK{timestamp}{random_part}"