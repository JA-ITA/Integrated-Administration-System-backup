"""
Event service for publishing receipt domain events
"""
import json
import logging
import asyncio
from datetime import datetime, timezone
from typing import Optional, Dict, Any
import aio_pika
from aio_pika import ExchangeType
from models import Receipt
from config import config

logger = logging.getLogger(__name__)

class EventService:
    """Service for publishing receipt domain events"""
    
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
                client_properties={"connection_name": "receipt-service"}
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
                "service": "receipt-service",
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
                            "service": "receipt-service"
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
    
    async def publish_receipt_validated(self, receipt: Receipt) -> bool:
        """Publish ReceiptValidated event"""
        event_data = {
            "receipt_no": receipt.receipt_no,
            "issue_date": receipt.issue_date.isoformat(),
            "location": receipt.location,
            "amount": float(receipt.amount),
            "used_flag": receipt.used_flag,
            "validated_at": receipt.validated_at.isoformat() if receipt.validated_at else None,
            "created_at": receipt.created_at.isoformat()
        }
        
        return await self.publish_event(
            event_type="ReceiptValidated",
            event_data=event_data,
            routing_key="receipt.validation.completed",
            entity_id=receipt.receipt_no,
            entity_type="receipt"
        )
    
    async def publish_receipt_duplicate(self, receipt_no: str, validation_attempt: Dict[str, Any]) -> bool:
        """Publish ReceiptDuplicate event"""
        event_data = {
            "receipt_no": receipt_no,
            "attempted_at": datetime.now(timezone.utc).isoformat(),
            "validation_attempt": validation_attempt,
            "reason": "Receipt already used"
        }
        
        return await self.publish_event(
            event_type="ReceiptDuplicate",
            event_data=event_data,
            routing_key="receipt.validation.duplicate",
            entity_id=receipt_no,
            entity_type="receipt"
        )
    
    async def publish_receipt_invalid(self, receipt_no: str, validation_errors: list, validation_attempt: Dict[str, Any]) -> bool:
        """Publish ReceiptInvalid event"""
        event_data = {
            "receipt_no": receipt_no,
            "attempted_at": datetime.now(timezone.utc).isoformat(),
            "validation_attempt": validation_attempt,
            "validation_errors": validation_errors,
            "reason": "Receipt validation failed"
        }
        
        return await self.publish_event(
            event_type="ReceiptInvalid",
            event_data=event_data,
            routing_key="receipt.validation.failed",
            entity_id=receipt_no,
            entity_type="receipt"
        )
    
    def get_fallback_events(self) -> list:
        """Get events from fallback storage (for testing/debugging)"""
        return self.fallback_events.copy()
    
    def clear_fallback_events(self):
        """Clear fallback events (for testing)"""
        self.fallback_events.clear()