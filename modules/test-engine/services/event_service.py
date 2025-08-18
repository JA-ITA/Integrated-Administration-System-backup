"""
Event publishing service for ITADIAS Test Engine Microservice
"""
import json
import logging
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
import aio_pika
from aio_pika import ExchangeType
from config import config

logger = logging.getLogger(__name__)

class EventService:
    """Service for publishing events to RabbitMQ"""
    
    def __init__(self):
        self.connection = None
        self.channel = None
        self.exchange = None
        self.fallback_events = []  # In-memory fallback when RabbitMQ is unavailable
    
    async def initialize(self):
        """Initialize RabbitMQ connection"""
        try:
            self.connection = await aio_pika.connect_robust(
                config.rabbitmq.url,
                loop=None
            )
            self.channel = await self.connection.channel()
            
            # Declare exchange
            self.exchange = await self.channel.declare_exchange(
                config.rabbitmq.exchange,
                ExchangeType.TOPIC,
                durable=True
            )
            
            logger.info("RabbitMQ connection established")
            
        except Exception as e:
            logger.warning(f"Failed to connect to RabbitMQ: {e}")
            logger.info("Events will be stored in memory as fallback")
            self.connection = None
            self.channel = None
            self.exchange = None
    
    async def close(self):
        """Close RabbitMQ connection"""
        try:
            if self.connection and not self.connection.is_closed:
                await self.connection.close()
                logger.info("RabbitMQ connection closed")
        except Exception as e:
            logger.error(f"Error closing RabbitMQ connection: {e}")
    
    async def publish_event(self, event_type: str, data: Dict[str, Any], routing_key: str = ""):
        """Publish an event to RabbitMQ or store as fallback"""
        event = {
            "event_type": event_type,
            "data": data,
            "timestamp": datetime.utcnow().isoformat(),
            "service": "test-engine"
        }
        
        try:
            if self.exchange:
                # Publish to RabbitMQ
                message = aio_pika.Message(
                    json.dumps(event, default=str).encode(),
                    content_type="application/json"
                )
                
                await self.exchange.publish(
                    message,
                    routing_key=routing_key or event_type
                )
                
                logger.info(f"Event published: {event_type}")
                
            else:
                # Fallback to in-memory storage
                self.fallback_events.append(event)
                logger.info(f"Event stored in fallback: {event_type}")
                
        except Exception as e:
            logger.error(f"Failed to publish event {event_type}: {e}")
            # Store in fallback
            self.fallback_events.append(event)
    
    async def publish_test_completed(
        self,
        driver_record_id: uuid.UUID,
        test_id: uuid.UUID,
        score: float,
        passed: bool,
        timestamp: datetime
    ):
        """Publish TestCompleted event"""
        data = {
            "driver_record_id": str(driver_record_id),
            "test_id": str(test_id),
            "score": score,
            "passed": passed,
            "timestamp": timestamp.isoformat()
        }
        
        await self.publish_event(
            event_type="TestCompleted",
            data=data,
            routing_key="test.completed"
        )
    
    async def publish_test_started(
        self,
        driver_record_id: uuid.UUID,
        test_id: uuid.UUID,
        module: str,
        timestamp: datetime
    ):
        """Publish TestStarted event"""
        data = {
            "driver_record_id": str(driver_record_id),
            "test_id": str(test_id),
            "module": module,
            "timestamp": timestamp.isoformat()
        }
        
        await self.publish_event(
            event_type="TestStarted",
            data=data,
            routing_key="test.started"
        )
    
    async def publish_test_expired(
        self,
        driver_record_id: uuid.UUID,
        test_id: uuid.UUID,
        timestamp: datetime
    ):
        """Publish TestExpired event"""
        data = {
            "driver_record_id": str(driver_record_id),
            "test_id": str(test_id),
            "timestamp": timestamp.isoformat()
        }
        
        await self.publish_event(
            event_type="TestExpired",
            data=data,
            routing_key="test.expired"
        )
    
    def get_fallback_events(self) -> list:
        """Get fallback events stored in memory"""
        return self.fallback_events.copy()
    
    def clear_fallback_events(self) -> int:
        """Clear fallback events and return count"""
        count = len(self.fallback_events)
        self.fallback_events.clear()
        return count
    
    def get_status(self) -> Dict[str, Any]:
        """Get event service status"""
        return {
            "rabbitmq_connected": self.connection is not None and not self.connection.is_closed,
            "fallback_events_count": len(self.fallback_events),
            "exchange": config.rabbitmq.exchange
        }