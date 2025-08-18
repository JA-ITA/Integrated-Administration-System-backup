"""
Event publishing service for ITADIAS Audit Microservice
"""
import json
import asyncio
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
import aio_pika
from aio_pika import ExchangeType, Message
from config import config
from models import OverrideIssuedEvent

logger = logging.getLogger(__name__)

class EventService:
    """RabbitMQ event publishing service with fallback storage"""
    
    def __init__(self):
        self.rabbitmq_url = config.rabbitmq.url
        self.exchange_name = config.rabbitmq.exchange
        self.connection = None
        self.channel = None
        self.exchange = None
        self.fallback_events = []  # In-memory fallback
        self.max_fallback_events = 1000
    
    async def initialize(self):
        """Initialize RabbitMQ connection"""
        try:
            self.connection = await aio_pika.connect_robust(
                self.rabbitmq_url,
                timeout=10
            )
            self.channel = await self.connection.channel()
            
            # Declare exchange
            self.exchange = await self.channel.declare_exchange(
                self.exchange_name,
                ExchangeType.TOPIC,
                durable=True
            )
            
            logger.info("Event service initialized with RabbitMQ")
            return True
            
        except Exception as e:
            logger.warning(f"Failed to initialize RabbitMQ: {e}")
            logger.info("Event service will use fallback storage")
            return False
    
    async def publish_override_issued_event(self, event: OverrideIssuedEvent) -> bool:
        """Publish OverrideIssued event"""
        try:
            event_data = {
                "event_type": "OverrideIssued",
                "audit_id": str(event.audit_id),
                "actor_id": str(event.actor_id),
                "actor_role": event.actor_role,
                "resource_type": event.resource_type,
                "resource_id": str(event.resource_id),
                "old_status": event.old_status,
                "new_status": event.new_status,
                "reason": event.reason,
                "timestamp": event.timestamp.isoformat()
            }
            
            # Try to publish to RabbitMQ
            if self.exchange:
                message = Message(
                    json.dumps(event_data).encode(),
                    delivery_mode=2,  # Persistent
                    headers={
                        "event_type": "OverrideIssued",
                        "source": "audit-service",
                        "version": "1.0"
                    }
                )
                
                routing_key = f"audit.override.{event.resource_type.lower()}"
                await self.exchange.publish(message, routing_key=routing_key)
                
                logger.info(f"Published OverrideIssued event for {event.resource_type}:{event.resource_id}")
                return True
            else:
                # Store in fallback
                await self._store_fallback_event(event_data)
                logger.info(f"Stored OverrideIssued event in fallback for {event.resource_type}:{event.resource_id}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to publish OverrideIssued event: {e}")
            # Store in fallback as last resort
            try:
                await self._store_fallback_event(event_data)
                logger.info("Stored event in fallback due to publish failure")
                return True
            except Exception as fallback_error:
                logger.error(f"Failed to store event in fallback: {fallback_error}")
                return False
    
    async def _store_fallback_event(self, event_data: dict):
        """Store event in fallback storage"""
        # Add fallback metadata
        event_data["_fallback"] = True
        event_data["_stored_at"] = datetime.utcnow().isoformat()
        
        # Add to in-memory fallback
        self.fallback_events.append(event_data)
        
        # Keep only the latest events
        if len(self.fallback_events) > self.max_fallback_events:
            self.fallback_events = self.fallback_events[-self.max_fallback_events:]
    
    async def get_fallback_events(self) -> List[Dict[str, Any]]:
        """Get fallback events"""
        return self.fallback_events.copy()
    
    async def get_connection_status(self) -> Dict[str, Any]:
        """Get event service connection status"""
        try:
            is_connected = (
                self.connection is not None and 
                not self.connection.is_closed and
                self.channel is not None and
                not self.channel.is_closed
            )
            
            return {
                "connected": is_connected,
                "rabbitmq_url": config.rabbitmq.host,
                "exchange": self.exchange_name,
                "fallback_events_count": len(self.fallback_events),
                "status": "connected" if is_connected else "using_fallback"
            }
        except Exception as e:
            return {
                "connected": False,
                "error": str(e),
                "fallback_events_count": len(self.fallback_events),
                "status": "error"
            }
    
    async def close(self):
        """Close event service connections"""
        try:
            if self.channel and not self.channel.is_closed:
                await self.channel.close()
            
            if self.connection and not self.connection.is_closed:
                await self.connection.close()
            
            logger.info("Event service connections closed")
        except Exception as e:
            logger.error(f"Error closing event service: {e}")