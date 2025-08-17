"""
Event publishing service for Registration microservice
Handles RabbitMQ publishing with fallback to in-memory storage
"""
import logging
import json
import asyncio
from typing import Dict, Any, List
from datetime import datetime, timezone
import aio_pika
from aio_pika import Message, DeliveryMode
from config import config
from models import RegistrationCompletedEvent

logger = logging.getLogger(__name__)

class EventService:
    """Service for publishing registration events"""
    
    def __init__(self):
        self.connection = None
        self.channel = None
        self.exchange = None
        self.fallback_events: List[Dict[str, Any]] = []
        self.is_connected = False
    
    async def initialize(self):
        """Initialize RabbitMQ connection"""
        try:
            # Try to connect to RabbitMQ
            self.connection = await aio_pika.connect_robust(config.rabbitmq.url)
            self.channel = await self.connection.channel()
            
            # Declare exchange
            self.exchange = await self.channel.declare_exchange(
                config.rabbitmq.exchange,
                aio_pika.ExchangeType.TOPIC,
                durable=True
            )
            
            self.is_connected = True
            logger.info(f"Connected to RabbitMQ: {config.rabbitmq.host}:{config.rabbitmq.port}")
            
            # Process any fallback events
            await self._process_fallback_events()
            
        except Exception as e:
            logger.warning(f"Failed to connect to RabbitMQ: {e}")
            logger.info("Events will be stored in memory as fallback")
            self.is_connected = False
    
    async def publish_registration_completed(
        self,
        driver_record_id: str,
        candidate_id: str,
        booking_id: str,
        status: str
    ) -> bool:
        """Publish RegistrationCompleted event"""
        try:
            event = RegistrationCompletedEvent(
                driver_record_id=driver_record_id,
                candidate_id=candidate_id,
                booking_id=booking_id,
                status=status,
                timestamp=datetime.now(timezone.utc)
            )
            
            event_data = {
                "event_type": "RegistrationCompleted",
                "data": event.dict(),
                "service": "registration",
                "version": "1.0"
            }
            
            if self.is_connected and self.exchange:
                # Publish to RabbitMQ
                message = Message(
                    json.dumps(event_data, default=str).encode(),
                    delivery_mode=DeliveryMode.PERSISTENT,
                    headers={
                        "event_type": "RegistrationCompleted",
                        "service": "registration",
                        "timestamp": event.timestamp.isoformat()
                    }
                )
                
                routing_key = f"registration.completed.{status.lower()}"
                await self.exchange.publish(message, routing_key=routing_key)
                
                logger.info(f"Published RegistrationCompleted event: {driver_record_id}")
                return True
            else:
                # Fallback to in-memory storage
                self.fallback_events.append(event_data)
                logger.warning(f"Stored RegistrationCompleted event in fallback: {driver_record_id}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to publish RegistrationCompleted event: {e}")
            # Store in fallback even if RabbitMQ publish fails
            try:
                event_data = {
                    "event_type": "RegistrationCompleted",
                    "data": {
                        "driver_record_id": str(driver_record_id),
                        "candidate_id": str(candidate_id),
                        "booking_id": str(booking_id),
                        "status": status,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    },
                    "service": "registration",
                    "version": "1.0"
                }
                self.fallback_events.append(event_data)
                logger.info(f"Stored failed event in fallback: {driver_record_id}")
                return True
            except Exception as fallback_error:
                logger.error(f"Failed to store event even in fallback: {fallback_error}")
                return False
    
    async def _process_fallback_events(self):
        """Process events stored in fallback when connection is restored"""
        if not self.fallback_events or not self.is_connected:
            return
        
        logger.info(f"Processing {len(self.fallback_events)} fallback events")
        
        events_to_remove = []
        for event in self.fallback_events:
            try:
                if self.exchange:
                    message = Message(
                        json.dumps(event, default=str).encode(),
                        delivery_mode=DeliveryMode.PERSISTENT,
                        headers={
                            "event_type": event["event_type"],
                            "service": event["service"],
                            "timestamp": event["data"]["timestamp"]
                        }
                    )
                    
                    routing_key = f"registration.completed.{event['data']['status'].lower()}"
                    await self.exchange.publish(message, routing_key=routing_key)
                    
                    events_to_remove.append(event)
                    logger.info(f"Published fallback event: {event['data']['driver_record_id']}")
                    
            except Exception as e:
                logger.error(f"Failed to publish fallback event: {e}")
        
        # Remove successfully published events
        for event in events_to_remove:
            self.fallback_events.remove(event)
    
    async def get_fallback_events(self) -> List[Dict[str, Any]]:
        """Get events stored in fallback (for debugging/monitoring)"""
        return self.fallback_events.copy()
    
    async def get_connection_status(self) -> Dict[str, Any]:
        """Get connection status information"""
        return {
            "connected": self.is_connected,
            "rabbitmq_url": f"{config.rabbitmq.host}:{config.rabbitmq.port}",
            "exchange": config.rabbitmq.exchange,
            "fallback_events_count": len(self.fallback_events)
        }
    
    async def close(self):
        """Close RabbitMQ connection"""
        try:
            if self.connection and not self.connection.is_closed:
                await self.connection.close()
                logger.info("RabbitMQ connection closed")
        except Exception as e:
            logger.error(f"Error closing RabbitMQ connection: {e}")
        
        self.is_connected = False
        self.connection = None
        self.channel = None
        self.exchange = None