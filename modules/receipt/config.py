"""
Configuration management for ITADIAS Receipt Microservice
"""
import os
from typing import Optional, List
from pydantic import BaseModel

class DatabaseConfig(BaseModel):
    """Database configuration"""
    host: str = os.getenv("DB_HOST", "localhost")
    port: int = int(os.getenv("DB_PORT", "5432"))
    name: str = os.getenv("DB_NAME", "receipt_db")
    user: str = os.getenv("DB_USER", "receipt_user")
    password: str = os.getenv("DB_PASSWORD", "receipt_pass")
    schema: str = os.getenv("DB_SCHEMA", "receipt")
    
    @property
    def url(self) -> str:
        return f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"

class ReceiptConfig(BaseModel):
    """Receipt validation configuration"""
    receipt_no_pattern: str = r"^[A-Z0-9]{8,20}$"
    max_age_days: int = int(os.getenv("MAX_RECEIPT_AGE_DAYS", "365"))
    
    # Pre-defined TAJ office locations
    valid_locations: List[str] = [
        "TAJ Online",
        "TAJ Mumbai Office",
        "TAJ Delhi Office", 
        "TAJ Bangalore Office",
        "TAJ Chennai Office",
        "TAJ Kolkata Office",
        "TAJ Pune Office",
        "TAJ Hyderabad Office",
        "TAJ Ahmedabad Office"
    ]

class RabbitMQConfig(BaseModel):
    """RabbitMQ configuration"""
    host: str = os.getenv("RABBITMQ_HOST", "localhost")
    port: int = int(os.getenv("RABBITMQ_PORT", "5672"))
    user: str = os.getenv("RABBITMQ_USER", "guest")
    password: str = os.getenv("RABBITMQ_PASSWORD", "guest")
    vhost: str = os.getenv("RABBITMQ_VHOST", "/")
    exchange: str = os.getenv("RABBITMQ_EXCHANGE", "receipt_events")
    
    @property
    def url(self) -> str:
        return f"amqp://{self.user}:{self.password}@{self.host}:{self.port}{self.vhost}"

class Config:
    """Main configuration class"""
    def __init__(self):
        self.db = DatabaseConfig()
        self.receipt = ReceiptConfig()
        self.rabbitmq = RabbitMQConfig()
        
        # General settings
        self.environment = os.getenv("ENVIRONMENT", "development")
        self.debug = os.getenv("DEBUG", "false").lower() == "true"
        self.log_level = os.getenv("LOG_LEVEL", "INFO")

# Global config instance
config = Config()