"""
Event publishing service for Special Admin Microservice
Publishes SpecialTypeCreated and TemplateUpdated events
"""
import json
import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional
import pika
from pika.adapters.asyncio_connection import AsyncioConnection
from config import config

logger = logging.getLogger(__name__)

class EventService:
    """Event service for publishing events with RabbitMQ fallback"""
    
    def __init__(self):
        self.connection = None
        self.channel = None
        self.exchange = config.rabbitmq.exchange
        self.rabbitmq_available = False
        self.fallback_events = []  # In-memory fallback storage
        
    async def initialize(self):
        """Initialize event service with RabbitMQ connection"""
        try:
            # Try to connect to RabbitMQ
            connection_params = pika.ConnectionParameters(
                host=config.rabbitmq.host,
                port=config.rabbitmq.port,
                credentials=pika.PlainCredentials(
                    config.rabbitmq.user,
                    config.rabbitmq.password
                ),
                heartbeat=600,
                blocked_connection_timeout=300,
            )
            
            # Test connection
            connection = pika.BlockingConnection(connection_params)
            channel = connection.channel()
            
            # Declare exchange
            channel.exchange_declare(
                exchange=self.exchange,
                exchange_type='topic',
                durable=True
            )
            
            connection.close()
            
            self.rabbitmq_available = True
            logger.info("RabbitMQ connection established successfully")
            
        except Exception as e:
            logger.warning(f"RabbitMQ not available, using fallback mode: {e}")
            self.rabbitmq_available = False
    
    async def publish_special_type_created(self, special_type_data: Dict[str, Any]):
        """Publish SpecialTypeCreated event"""
        event = {
            "event_type": "SpecialTypeCreated",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "service": "special-admin",
            "data": {
                "special_type_id": str(special_type_data["id"]),
                "name": special_type_data["name"],
                "fee": float(special_type_data["fee"]),
                "validity_months": special_type_data["validity_months"],
                "required_docs": special_type_data["required_docs"],
                "created_by": special_type_data["created_by"]
            }
        }
        
        await self._publish_event("special.type.created", event)
    
    async def publish_template_updated(self, template_data: Dict[str, Any]):
        """Publish TemplateUpdated event"""
        event = {
            "event_type": "TemplateUpdated",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "service": "special-admin",
            "data": {
                "template_id": str(template_data["id"]),
                "name": template_data["name"],
                "type": template_data["type"],
                "status": template_data["status"],
                "is_default": template_data.get("is_default", False),
                "created_by": template_data["created_by"]
            }
        }
        
        await self._publish_event("template.updated", event)
    
    async def publish_module_created(self, module_data: Dict[str, Any]):
        """Publish ModuleCreated event"""
        event = {
            "event_type": "ModuleCreated",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "service": "special-admin",
            "data": {
                "module_id": str(module_data["id"]),
                "code": module_data["code"],
                "description": module_data["description"],
                "category": module_data.get("category"),
                "created_by": module_data["created_by"]
            }
        }
        
        await self._publish_event("module.created", event)
    
    async def _publish_event(self, routing_key: str, event: Dict[str, Any]):
        """Publish event to RabbitMQ or fallback storage"""
        try:
            if self.rabbitmq_available:
                await self._publish_to_rabbitmq(routing_key, event)
            else:
                await self._publish_to_fallback(routing_key, event)
        except Exception as e:
            logger.error(f"Failed to publish event: {e}")
            # Try fallback if RabbitMQ fails
            await self._publish_to_fallback(routing_key, event)
    
    async def _publish_to_rabbitmq(self, routing_key: str, event: Dict[str, Any]):
        """Publish event to RabbitMQ"""
        try:
            connection_params = pika.ConnectionParameters(
                host=config.rabbitmq.host,
                port=config.rabbitmq.port,
                credentials=pika.PlainCredentials(
                    config.rabbitmq.user,
                    config.rabbitmq.password
                )
            )
            
            connection = pika.BlockingConnection(connection_params)
            channel = connection.channel()
            
            channel.basic_publish(
                exchange=self.exchange,
                routing_key=routing_key,
                body=json.dumps(event),
                properties=pika.BasicProperties(
                    delivery_mode=2,  # Make message persistent
                    content_type='application/json'
                )
            )
            
            connection.close()
            logger.info(f"Event published to RabbitMQ: {routing_key}")
            
        except Exception as e:
            logger.error(f"RabbitMQ publish failed: {e}")
            self.rabbitmq_available = False
            raise
    
    async def _publish_to_fallback(self, routing_key: str, event: Dict[str, Any]):
        """Publish event to fallback storage"""
        fallback_event = {
            "routing_key": routing_key,
            "event": event,
            "stored_at": datetime.now(timezone.utc).isoformat()
        }
        
        self.fallback_events.append(fallback_event)
        
        # Keep only last 1000 events in memory
        if len(self.fallback_events) > 1000:
            self.fallback_events = self.fallback_events[-1000:]
        
        logger.info(f"Event stored in fallback: {routing_key}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get event service status"""
        return {
            "rabbitmq_available": self.rabbitmq_available,
            "rabbitmq_host": config.rabbitmq.host,
            "rabbitmq_port": config.rabbitmq.port,
            "exchange": self.exchange,
            "fallback_events_count": len(self.fallback_events)
        }
    
    def get_fallback_events(self, limit: int = 100) -> list:
        """Get fallback events"""
        return self.fallback_events[-limit:] if self.fallback_events else []
    
    async def close(self):
        """Close event service connections"""
        try:
            if self.channel and not self.channel.is_closed:
                self.channel.close()
            if self.connection and not self.connection.is_closed:
                self.connection.close()
            logger.info("Event service connections closed")
        except Exception as e:
            logger.error(f"Error closing event service: {e}")