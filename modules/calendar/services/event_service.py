"""
Event service for publishing domain events
"""
import json
import logging
import asyncio
from datetime import datetime, timezone
from typing import Optional, Dict, Any
import aio_pika
from aio_pika import ExchangeType
from models import Booking, Slot
from config import config

logger = logging.getLogger(__name__)

class EventService:
    """Service for publishing domain events"""
    
    def __init__(self):
        self.connection: Optional[aio_pika.Connection] = None
        self.channel: Optional[aio_pika.Channel] = None
        self.exchange: Optional[aio_pika.Exchange] = None
        self.fallback_events: list = []  # In-memory fallback
    
    async def initialize(self):
        """Initialize RabbitMQ connection"""
        try:
            # Try to connect to RabbitMQ
            self.connection = await aio_pika.connect_robust(
                config.rabbitmq.url,
                client_properties={"connection_name": "calendar-service"}
            )
            
            self.channel = await self.connection.channel()
            await self.channel.set_qos(prefetch_count=10)
            
            # Declare exchange
            self.exchange = await self.channel.declare_exchange(
                config.rabbitmq.exchange,
                ExchangeType.TOPIC,
                durable=True
            )
            
            logger.info("RabbitMQ connection established")
            
        except Exception as e:
            logger.warning(f"Failed to connect to RabbitMQ: {e}")
            logger.info("Using fallback in-memory event storage")
    
    async def close(self):
        """Close RabbitMQ connection"""
        try:
            if self.connection and not self.connection.is_closed:
                await self.connection.close()
                logger.info("RabbitMQ connection closed")
        except Exception as e:
            logger.error(f"Error closing RabbitMQ connection: {e}")
    
    async def publish_event(
        self,
        event_type: str,
        event_data: Dict[str, Any],
        routing_key: str,
        entity_id: Optional[str] = None,
        entity_type: Optional[str] = None
    ) -> bool:
        """Publish an event to RabbitMQ or fallback storage"""
        try:
            # Prepare event payload
            event_payload = {
                "event_type": event_type,
                "event_data": event_data,
                "entity_id": entity_id,
                "entity_type": entity_type,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "service": "calendar-service",
                "version": "1.0.0"
            }
            
            # Try RabbitMQ first
            if self.exchange:
                try:
                    message = aio_pika.Message(
                        body=json.dumps(event_payload).encode(),
                        content_type="application/json",
                        headers={
                            "event_type": event_type,
                            "entity_type": entity_type or "unknown",
                            "service": "calendar-service"
                        }
                    )
                    
                    await self.exchange.publish(
                        message,
                        routing_key=routing_key
                    )
                    
                    logger.info(f"Event published to RabbitMQ: {event_type}")
                    return True
                    
                except Exception as e:
                    logger.error(f"Failed to publish to RabbitMQ: {e}")
                    # Fall through to fallback
            
            # Fallback to in-memory storage
            self.fallback_events.append({
                **event_payload,
                "stored_at": datetime.now(timezone.utc).isoformat(),
                "routing_key": routing_key
            })
            
            logger.info(f"Event stored in fallback: {event_type}")
            
            # Keep only last 1000 events in memory
            if len(self.fallback_events) > 1000:
                self.fallback_events = self.fallback_events[-1000:]
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to publish event {event_type}: {e}")
            return False
    
    async def publish_booking_created(self, booking: Booking, slot: Slot) -> bool:
        """Publish BookingCreated event"""
        event_data = {
            "booking_id": str(booking.id),
            "slot_id": str(booking.slot_id),
            "candidate_id": str(booking.candidate_id),
            "booking_reference": booking.booking_reference,
            "contact_email": booking.contact_email,
            "contact_phone": booking.contact_phone,
            "slot_start_time": slot.start_time.isoformat(),
            "slot_end_time": slot.end_time.isoformat(),
            "hub_id": str(slot.hub_id),
            "status": booking.status.value,
            "created_at": booking.created_at.isoformat()
        }
        
        return await self.publish_event(
            event_type="BookingCreated",
            event_data=event_data,
            routing_key="calendar.booking.created",
            entity_id=str(booking.id),
            entity_type="booking"
        )
    
    async def publish_booking_confirmed(self, booking: Booking) -> bool:
        """Publish BookingConfirmed event"""
        event_data = {
            "booking_id": str(booking.id),
            "slot_id": str(booking.slot_id),
            "candidate_id": str(booking.candidate_id),
            "booking_reference": booking.booking_reference,
            "confirmed_at": booking.confirmation_sent_at.isoformat() if booking.confirmation_sent_at else None
        }
        
        return await self.publish_event(
            event_type="BookingConfirmed",
            event_data=event_data,
            routing_key="calendar.booking.confirmed",
            entity_id=str(booking.id),
            entity_type="booking"
        )
    
    async def publish_booking_cancelled(self, booking: Booking) -> bool:
        """Publish BookingCancelled event"""
        event_data = {
            "booking_id": str(booking.id),
            "slot_id": str(booking.slot_id),
            "candidate_id": str(booking.candidate_id),
            "booking_reference": booking.booking_reference,
            "cancelled_at": booking.cancelled_at.isoformat() if booking.cancelled_at else None,
            "cancellation_reason": booking.cancellation_reason
        }
        
        return await self.publish_event(
            event_type="BookingCancelled",
            event_data=event_data,
            routing_key="calendar.booking.cancelled",
            entity_id=str(booking.id),
            entity_type="booking"
        )
    
    async def publish_slot_locked(self, slot: Slot, locked_by: str) -> bool:
        """Publish SlotLocked event"""
        event_data = {
            "slot_id": str(slot.id),
            "hub_id": str(slot.hub_id),
            "start_time": slot.start_time.isoformat(),
            "end_time": slot.end_time.isoformat(),
            "locked_until": slot.locked_until.isoformat() if slot.locked_until else None,
            "locked_by": locked_by
        }
        
        return await self.publish_event(
            event_type="SlotLocked",
            event_data=event_data,
            routing_key="calendar.slot.locked",
            entity_id=str(slot.id),
            entity_type="slot"
        )
    
    async def publish_slot_unlocked(self, slot: Slot) -> bool:
        """Publish SlotUnlocked event"""
        event_data = {
            "slot_id": str(slot.id),
            "hub_id": str(slot.hub_id),
            "start_time": slot.start_time.isoformat(),
            "end_time": slot.end_time.isoformat()
        }
        
        return await self.publish_event(
            event_type="SlotUnlocked",
            event_data=event_data,
            routing_key="calendar.slot.unlocked",
            entity_id=str(slot.id),
            entity_type="slot"
        )
    
    def get_fallback_events(self) -> list:
        """Get events from fallback storage (for testing/debugging)"""
        return self.fallback_events.copy()
    
    def clear_fallback_events(self):
        """Clear fallback events (for testing)"""
        self.fallback_events.clear()