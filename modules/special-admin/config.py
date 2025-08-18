"""
Configuration for ITADIAS Special Admin Microservice
"""
import os
from dataclasses import dataclass
from pydantic import BaseModel

class DatabaseConfig(BaseModel):
    """Database configuration for PostgreSQL"""
    host: str = os.getenv("DB_HOST", "localhost")
    port: int = int(os.getenv("DB_PORT", "5432"))
    name: str = os.getenv("DB_NAME", "itadias")
    user: str = os.getenv("DB_USER", "ita_admin")
    password: str = os.getenv("DB_PASSWORD", "ita_secure_2024")
    schema: str = os.getenv("DB_SCHEMA", "config")
    
    @property
    def url(self) -> str:
        return f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"

@dataclass
class RabbitMQConfig:
    """RabbitMQ configuration"""
    host: str = os.getenv("RABBITMQ_HOST", "localhost")
    port: int = int(os.getenv("RABBITMQ_PORT", "5672"))
    user: str = os.getenv("RABBITMQ_USER", "guest")
    password: str = os.getenv("RABBITMQ_PASSWORD", "guest")
    exchange: str = os.getenv("RABBITMQ_EXCHANGE", "itadias_events")

@dataclass
class ServiceConfig:
    """Service configuration"""
    name: str = os.getenv("SERVICE_NAME", "special-admin")
    version: str = os.getenv("SERVICE_VERSION", "1.0.0")
    port: int = int(os.getenv("PORT", "8007"))
    env: str = os.getenv("ENV", "development")

# Global configuration instance
@dataclass
class Config:
    db: DatabaseConfig
    rabbitmq: RabbitMQConfig
    service: ServiceConfig

config = Config(
    db=DatabaseConfig(),
    rabbitmq=RabbitMQConfig(),
    service=ServiceConfig()
)