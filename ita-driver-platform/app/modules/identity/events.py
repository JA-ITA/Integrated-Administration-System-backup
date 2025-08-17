"""
Identity Module Event Publishing System
Handles event publishing for candidate-related activities using RabbitMQ.
"""

import json
import uuid
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional
from dataclasses import asdict

import aio_pika
from aio_pika import Message, ExchangeType
from core.config import settings
from core.logging_config import get_logger

logger = get_logger("identity.events")


class CandidateEventPublisher:
    """Publisher for candidate-related events."""
    
    def __init__(self):
        self.connection = None
        self.channel = None
        self.exchange = None
        self.exchange_name = "ita.identity.events"
        
    async def connect(self):
        """Establish connection to RabbitMQ."""
        try:
            self.connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
            self.channel = await self.connection.channel()
            
            # Declare exchange
            self.exchange = await self.channel.declare_exchange(
                self.exchange_name,
                ExchangeType.TOPIC,
                durable=True
            )
            
            logger.info("Connected to RabbitMQ for event publishing")
            
        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {str(e)}")
            raise
    
    async def disconnect(self):
        """Close RabbitMQ connection."""
        if self.connection:
            await self.connection.close()
            logger.info("Disconnected from RabbitMQ")
    
    async def publish_event(
        self,
        event_type: str,
        candidate_id: str,
        event_data: Dict[str, Any],
        correlation_id: Optional[str] = None
    ):
        """
        Publish a candidate event to RabbitMQ.
        
        Args:
            event_type: Type of event (e.g., 'CandidateCreated')
            candidate_id: ID of the candidate
            event_data: Event payload
            correlation_id: Optional correlation ID for tracing
        """
        if not self.exchange:
            await self.connect()
        
        correlation_id = correlation_id or str(uuid.uuid4())
        
        # Create event payload
        event_payload = {
            "event_id": str(uuid.uuid4()),
            "event_type": event_type,
            "candidate_id": candidate_id,
            "event_data": event_data,
            "correlation_id": correlation_id,
            "source": "identity_service",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0"
        }
        
        try:
            # Create message
            message = Message(
                json.dumps(event_payload).encode(),
                headers={
                    "event_type": event_type,
                    "candidate_id": candidate_id,
                    "correlation_id": correlation_id,
                    "content_type": "application/json"
                },
                delivery_mode=2,  # Persistent message
                correlation_id=correlation_id
            )
            
            # Routing key format: identity.{event_type}.{candidate_id}
            routing_key = f"identity.{event_type.lower()}.{candidate_id}"
            
            # Publish message
            await self.exchange.publish(message, routing_key=routing_key)
            
            logger.info(
                f"Published event: {event_type}",
                extra={
                    "event_type": event_type,
                    "candidate_id": candidate_id,
                    "correlation_id": correlation_id,
                    "routing_key": routing_key
                }
            )
            
        except Exception as e:
            logger.error(
                f"Failed to publish event: {event_type}",
                extra={
                    "error": str(e),
                    "event_type": event_type,
                    "candidate_id": candidate_id,
                    "correlation_id": correlation_id
                }
            )
            raise
    
    async def publish_candidate_created(
        self,
        candidate_id: str,
        candidate_data: Dict[str, Any],
        correlation_id: Optional[str] = None
    ):
        """Publish CandidateCreated event."""
        await self.publish_event(
            event_type="CandidateCreated",
            candidate_id=candidate_id,
            event_data=candidate_data,
            correlation_id=correlation_id
        )
    
    async def publish_candidate_verified(
        self,
        candidate_id: str,
        verification_type: str,
        correlation_id: Optional[str] = None
    ):
        """Publish CandidateVerified event."""
        await self.publish_event(
            event_type="CandidateVerified",
            candidate_id=candidate_id,
            event_data={
                "verification_type": verification_type,
                "verified_at": datetime.utcnow().isoformat()
            },
            correlation_id=correlation_id
        )
    
    async def publish_otp_sent(
        self,
        candidate_id: str,
        otp_type: str,
        recipient: str,
        correlation_id: Optional[str] = None
    ):
        """Publish OTPSent event."""
        await self.publish_event(
            event_type="OTPSent",
            candidate_id=candidate_id,
            event_data={
                "otp_type": otp_type,
                "recipient": recipient,
                "sent_at": datetime.utcnow().isoformat()
            },
            correlation_id=correlation_id
        )
    
    async def publish_otp_verified(
        self,
        candidate_id: str,
        otp_type: str,
        correlation_id: Optional[str] = None
    ):
        """Publish OTPVerified event."""
        await self.publish_event(
            event_type="OTPVerified",
            candidate_id=candidate_id,
            event_data={
                "otp_type": otp_type,
                "verified_at": datetime.utcnow().isoformat()
            },
            correlation_id=correlation_id
        )
    
    async def publish_password_set(
        self,
        candidate_id: str,
        correlation_id: Optional[str] = None
    ):
        """Publish PasswordSet event."""
        await self.publish_event(
            event_type="PasswordSet",
            candidate_id=candidate_id,
            event_data={
                "password_set_at": datetime.utcnow().isoformat()
            },
            correlation_id=correlation_id
        )
    
    async def publish_profile_updated(
        self,
        candidate_id: str,
        updated_fields: list,
        correlation_id: Optional[str] = None
    ):
        """Publish ProfileUpdated event."""
        await self.publish_event(
            event_type="ProfileUpdated",
            candidate_id=candidate_id,
            event_data={
                "updated_fields": updated_fields,
                "updated_at": datetime.utcnow().isoformat()
            },
            correlation_id=correlation_id
        )


class EventConsumer:
    """Consumer for candidate events (for other services to use)."""
    
    def __init__(self, queue_name: str, routing_keys: list):
        self.connection = None
        self.channel = None
        self.queue = None
        self.queue_name = queue_name
        self.routing_keys = routing_keys
        self.exchange_name = "ita.identity.events"
        
    async def connect(self):
        """Establish connection and setup queue."""
        try:
            self.connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
            self.channel = await self.connection.channel()
            
            # Declare exchange
            exchange = await self.channel.declare_exchange(
                self.exchange_name,
                ExchangeType.TOPIC,
                durable=True
            )
            
            # Declare queue
            self.queue = await self.channel.declare_queue(
                self.queue_name,
                durable=True
            )
            
            # Bind queue to routing keys
            for routing_key in self.routing_keys:
                await self.queue.bind(exchange, routing_key)
            
            logger.info(f"Consumer connected for queue: {self.queue_name}")
            
        except Exception as e:
            logger.error(f"Failed to connect consumer: {str(e)}")
            raise
    
    async def consume(self, callback):
        """Start consuming messages."""
        if not self.queue:
            await self.connect()
        
        async def message_handler(message):
            async with message.process():
                try:
                    event_data = json.loads(message.body.decode())
                    await callback(event_data)
                except Exception as e:
                    logger.error(f"Error processing message: {str(e)}")
                    raise
        
        await self.queue.consume(message_handler)
        logger.info(f"Started consuming messages for queue: {self.queue_name}")


# Global event publisher instance
event_publisher = CandidateEventPublisher()


# Helper functions
async def ensure_publisher_connected():
    """Ensure event publisher is connected."""
    if not event_publisher.connection or event_publisher.connection.is_closed:
        await event_publisher.connect()


async def publish_candidate_created_event(
    candidate_id: str,
    candidate_data: Dict[str, Any],
    correlation_id: Optional[str] = None
):
    """Helper function to publish candidate created event."""
    try:
        await ensure_publisher_connected()
        await event_publisher.publish_candidate_created(
            candidate_id=candidate_id,
            candidate_data=candidate_data,
            correlation_id=correlation_id
        )
    except Exception as e:
        logger.error(f"Failed to publish CandidateCreated event: {str(e)}")
        # Don't re-raise to avoid breaking the main flow


async def publish_candidate_verified_event(
    candidate_id: str,
    verification_type: str,
    correlation_id: Optional[str] = None
):
    """Helper function to publish candidate verified event."""
    try:
        await ensure_publisher_connected()
        await event_publisher.publish_candidate_verified(
            candidate_id=candidate_id,
            verification_type=verification_type,
            correlation_id=correlation_id
        )
    except Exception as e:
        logger.error(f"Failed to publish CandidateVerified event: {str(e)}")


async def publish_otp_sent_event(
    candidate_id: str,
    otp_type: str,
    recipient: str,
    correlation_id: Optional[str] = None
):
    """Helper function to publish OTP sent event."""
    try:
        await ensure_publisher_connected()
        await event_publisher.publish_otp_sent(
            candidate_id=candidate_id,
            otp_type=otp_type,
            recipient=recipient,
            correlation_id=correlation_id
        )
    except Exception as e:
        logger.error(f"Failed to publish OTPSent event: {str(e)}")


async def cleanup_event_publisher():
    """Cleanup event publisher connection."""
    await event_publisher.disconnect()


# Context manager for event publishing
class EventPublishingContext:
    """Context manager for event publishing with automatic connection management."""
    
    async def __aenter__(self):
        await ensure_publisher_connected()
        return event_publisher
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # Don't disconnect here as the connection might be reused
        # Connection will be closed when the application shuts down
        pass