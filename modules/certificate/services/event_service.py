"""
Event service for publishing certificate events via RabbitMQ
"""
import json
import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional
import aio_pika
from aio_pika import connect_robust, Message, DeliveryMode

from config import config

logger = logging.getLogger(__name__)

class EventService:
    """Event service for publishing certificate-related events"""
    
    def __init__(self):
        self.connection = None
        self.channel = None
        self.exchange = None
        self.fallback_events = []  # Store events when RabbitMQ is unavailable
        self.max_fallback_events = 1000
        
    async def initialize(self):
        """Initialize RabbitMQ connection and exchange"""
        try:
            await self._connect_rabbitmq()
            logger.info("Event service initialized with RabbitMQ")
        except Exception as e:
            logger.warning(f"Failed to connect to RabbitMQ: {e}")
            logger.info("Event service will use fallback storage")
    
    async def _connect_rabbitmq(self):
        """Establish RabbitMQ connection"""
        try:
            # Connect to RabbitMQ
            self.connection = await connect_robust(
                config.rabbitmq.url,
                heartbeat=300,
                blocked_connection_timeout=300,
            )
            
            # Create channel
            self.channel = await self.connection.channel()
            
            # Declare exchange
            self.exchange = await self.channel.declare_exchange(
                config.rabbitmq.exchange,
                aio_pika.ExchangeType.TOPIC,
                durable=True
            )
            
            logger.info("Connected to RabbitMQ successfully")
            
        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            raise
    
    async def publish_certificate_generated(
        self,
        driver_record_id: str,
        certificate_id: str,
        candidate_name: str,
        licence_endorsement: str,
        issue_date: datetime,
        expiry_date: Optional[datetime],
        download_url: str,
        service_hub: str,
        additional_data: Optional[Dict[str, Any]] = None
    ):
        """Publish CertificateGenerated event"""
        
        event_data = {
            "driver_record_id": driver_record_id,
            "certificate_id": certificate_id,
            "candidate_name": candidate_name,
            "licence_endorsement": licence_endorsement,
            "issue_date": issue_date.isoformat(),
            "expiry_date": expiry_date.isoformat() if expiry_date else None,
            "download_url": download_url,
            "service_hub": service_hub,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        if additional_data:
            event_data.update(additional_data)
        
        await self._publish_event(
            routing_key="certificate.generated",
            event_type="CertificateGenerated",
            data=event_data
        )
    
    async def publish_certificate_downloaded(
        self,
        certificate_id: str,
        download_timestamp: datetime,
        client_info: Optional[Dict[str, str]] = None
    ):
        """Publish CertificateDownloaded event"""
        
        event_data = {
            "certificate_id": certificate_id,
            "download_timestamp": download_timestamp.isoformat(),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        if client_info:
            event_data["client_info"] = client_info
        
        await self._publish_event(
            routing_key="certificate.downloaded",
            event_type="CertificateDownloaded",
            data=event_data
        )
    
    async def publish_certificate_verified(
        self,
        certificate_id: str,
        verification_token: str,
        verification_result: bool,
        verification_timestamp: datetime,
        client_info: Optional[Dict[str, str]] = None
    ):
        """Publish CertificateVerified event"""
        
        event_data = {
            "certificate_id": certificate_id,
            "verification_token": verification_token,
            "verification_result": verification_result,
            "verification_timestamp": verification_timestamp.isoformat(),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        if client_info:
            event_data["client_info"] = client_info
        
        await self._publish_event(
            routing_key="certificate.verified",
            event_type="CertificateVerified",
            data=event_data
        )
    
    async def _publish_event(
        self,
        routing_key: str,
        event_type: str,
        data: Dict[str, Any]
    ):
        """Publish event to RabbitMQ or store in fallback"""
        
        event = {
            "event_type": event_type,
            "routing_key": routing_key,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        if self.exchange and self.channel:
            try:
                # Publish to RabbitMQ
                message_body = json.dumps(event)
                message = Message(
                    message_body.encode(),
                    delivery_mode=DeliveryMode.PERSISTENT,
                    content_type="application/json"
                )
                
                await self.exchange.publish(
                    message,
                    routing_key=routing_key
                )
                
                logger.info(f"Published {event_type} event to RabbitMQ")
                return
                
            except Exception as e:
                logger.error(f"Failed to publish event to RabbitMQ: {e}")
                # Fall through to fallback storage
        
        # Store in fallback
        self._store_fallback_event(event)
    
    def _store_fallback_event(self, event: Dict[str, Any]):
        """Store event in fallback storage when RabbitMQ is unavailable"""
        if len(self.fallback_events) >= self.max_fallback_events:
            # Remove oldest event to make space
            self.fallback_events.pop(0)
            logger.warning("Fallback event storage full, removed oldest event")
        
        self.fallback_events.append(event)
        logger.info(f"Stored {event['event_type']} event in fallback storage")
    
    async def retry_fallback_events(self):
        """Attempt to publish stored fallback events"""
        if not self.fallback_events or not (self.exchange and self.channel):
            return
        
        published_count = 0
        failed_events = []
        
        for event in self.fallback_events:
            try:
                message_body = json.dumps(event)
                message = Message(
                    message_body.encode(),
                    delivery_mode=DeliveryMode.PERSISTENT,
                    content_type="application/json"
                )
                
                await self.exchange.publish(
                    message,
                    routing_key=event["routing_key"]
                )
                
                published_count += 1
                
            except Exception as e:
                logger.error(f"Failed to retry event: {e}")
                failed_events.append(event)
        
        # Update fallback storage with failed events
        self.fallback_events = failed_events
        
        if published_count > 0:
            logger.info(f"Successfully published {published_count} fallback events")
    
    def get_status(self) -> Dict[str, Any]:
        """Get event service status"""
        return {
            "connected": self.connection is not None and not self.connection.is_closed,
            "exchange": config.rabbitmq.exchange,
            "fallback_events_count": len(self.fallback_events),
            "max_fallback_events": self.max_fallback_events
        }
    
    async def close(self):
        """Close RabbitMQ connection"""
        try:
            if self.channel:
                await self.channel.close()
            if self.connection:
                await self.connection.close()
            logger.info("Event service connections closed")
        except Exception as e:
            logger.error(f"Error closing event service: {e}")