"""
Configuration management for ITADIAS Test Engine Microservice
"""
import os
from typing import Optional
from pydantic import BaseModel

class DatabaseConfig(BaseModel):
    """Database configuration"""
    host: str = os.getenv("DB_HOST", "localhost")
    port: int = int(os.getenv("DB_PORT", "5432"))
    name: str = os.getenv("DB_NAME", "test_engine_db")
    user: str = os.getenv("DB_USER", "test_engine_user")
    password: str = os.getenv("DB_PASSWORD", "test_engine_pass")
    schema: str = os.getenv("DB_SCHEMA", "test_engine")
    
    @property
    def url(self) -> str:
        return f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"

class TestConfig(BaseModel):
    """Test configuration"""
    questions_per_test: int = int(os.getenv("QUESTIONS_PER_TEST", "20"))
    time_limit_minutes: int = int(os.getenv("TIME_LIMIT_MINUTES", "25"))
    passing_score_percent: float = float(os.getenv("PASSING_SCORE_PERCENT", "75.0"))
    max_attempts_per_booking: int = int(os.getenv("MAX_ATTEMPTS_PER_BOOKING", "1"))

class RabbitMQConfig(BaseModel):
    """RabbitMQ configuration"""
    host: str = os.getenv("RABBITMQ_HOST", "localhost")
    port: int = int(os.getenv("RABBITMQ_PORT", "5672"))
    user: str = os.getenv("RABBITMQ_USER", "guest")
    password: str = os.getenv("RABBITMQ_PASSWORD", "guest")
    vhost: str = os.getenv("RABBITMQ_VHOST", "/")
    exchange: str = os.getenv("RABBITMQ_EXCHANGE", "test_engine_events")
    
    @property
    def url(self) -> str:
        return f"amqp://{self.user}:{self.password}@{self.host}:{self.port}{self.vhost}"

class Config:
    """Main configuration class"""
    def __init__(self):
        self.db = DatabaseConfig()
        self.test = TestConfig()
        self.rabbitmq = RabbitMQConfig()
        
        # General settings
        self.environment = os.getenv("ENVIRONMENT", "development")
        self.debug = os.getenv("DEBUG", "false").lower() == "true"
        self.log_level = os.getenv("LOG_LEVEL", "INFO")

# Global config instance
config = Config()