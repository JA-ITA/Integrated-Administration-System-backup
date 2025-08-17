"""
Configuration management for ITADIAS Calendar Microservice
"""
import os
from typing import Optional
from pydantic import BaseModel

class DatabaseConfig(BaseModel):
    """Database configuration"""
    host: str = os.getenv("DB_HOST", "localhost")
    port: int = int(os.getenv("DB_PORT", "5432"))
    name: str = os.getenv("DB_NAME", "calendar_db")
    user: str = os.getenv("DB_USER", "calendar_user")
    password: str = os.getenv("DB_PASSWORD", "calendar_pass")
    schema: str = os.getenv("DB_SCHEMA", "calendar")
    
    @property
    def url(self) -> str:
        return f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"

class BookingConfig(BaseModel):
    """Booking configuration"""
    lock_duration_minutes: int = int(os.getenv("BOOKING_LOCK_DURATION_MINUTES", "15"))
    cleanup_interval_minutes: int = int(os.getenv("CLEANUP_INTERVAL_MINUTES", "5"))
    max_advance_booking_days: int = int(os.getenv("MAX_ADVANCE_BOOKING_DAYS", "90"))
    slot_duration_minutes: int = int(os.getenv("SLOT_DURATION_MINUTES", "60"))

class RabbitMQConfig(BaseModel):
    """RabbitMQ configuration"""
    host: str = os.getenv("RABBITMQ_HOST", "localhost")
    port: int = int(os.getenv("RABBITMQ_PORT", "5672"))
    user: str = os.getenv("RABBITMQ_USER", "guest")
    password: str = os.getenv("RABBITMQ_PASSWORD", "guest")
    vhost: str = os.getenv("RABBITMQ_VHOST", "/")
    exchange: str = os.getenv("RABBITMQ_EXCHANGE", "calendar_events")
    
    @property
    def url(self) -> str:
        return f"amqp://{self.user}:{self.password}@{self.host}:{self.port}{self.vhost}"

class NotificationConfig(BaseModel):
    """Notification configuration"""
    booking_confirmation_enabled: bool = os.getenv("BOOKING_CONFIRMATION_ENABLED", "true").lower() == "true"
    booking_reminder_enabled: bool = os.getenv("BOOKING_REMINDER_ENABLED", "true").lower() == "true"
    reminder_hours_before: int = int(os.getenv("REMINDER_HOURS_BEFORE", "24"))

class Config:
    """Main configuration class"""
    def __init__(self):
        self.db = DatabaseConfig()
        self.booking = BookingConfig()
        self.rabbitmq = RabbitMQConfig()
        self.notification = NotificationConfig()
        
        # General settings
        self.environment = os.getenv("ENVIRONMENT", "development")
        self.debug = os.getenv("DEBUG", "false").lower() == "true"
        self.log_level = os.getenv("LOG_LEVEL", "INFO")

# Global config instance
config = Config()