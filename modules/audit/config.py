"""
Configuration for ITADIAS Audit Microservice
"""
import os
from dataclasses import dataclass
from typing import List

@dataclass
class DatabaseConfig:
    """Database configuration"""
    host: str = os.getenv("DB_HOST", "localhost")
    port: int = int(os.getenv("DB_PORT", "5432"))
    name: str = os.getenv("DB_NAME", "itadias")
    user: str = os.getenv("DB_USER", "ita_admin")
    password: str = os.getenv("DB_PASSWORD", "ita_admin_pass")
    schema: str = "audit"
    
    @property
    def url(self) -> str:
        return f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"

@dataclass
class RabbitMQConfig:
    """RabbitMQ configuration"""
    host: str = os.getenv("RABBITMQ_HOST", "localhost")
    port: int = int(os.getenv("RABBITMQ_PORT", "5672"))
    username: str = os.getenv("RABBITMQ_USER", "guest")
    password: str = os.getenv("RABBITMQ_PASS", "guest")
    exchange: str = os.getenv("RABBITMQ_EXCHANGE", "itadias.events")
    
    @property
    def url(self) -> str:
        return f"amqp://{self.username}:{self.password}@{self.host}:{self.port}/"

@dataclass
class IdentityConfig:
    """Identity service configuration for JWT validation"""
    service_url: str = os.getenv("IDENTITY_SERVICE_URL", "http://localhost:8001")
    jwt_secret: str = os.getenv("JWT_SECRET", "your-secret-key-here")
    jwt_algorithm: str = os.getenv("JWT_ALGORITHM", "HS256")

@dataclass
class Config:
    """Main configuration class"""
    environment: str = os.getenv("ENVIRONMENT", "development")
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"
    port: int = int(os.getenv("PORT", "8008"))
    
    db: DatabaseConfig = None
    rabbitmq: RabbitMQConfig = None
    identity: IdentityConfig = None
    
    def __post_init__(self):
        if self.db is None:
            self.db = DatabaseConfig()
        if self.rabbitmq is None:
            self.rabbitmq = RabbitMQConfig()
        if self.identity is None:
            self.identity = IdentityConfig()

# Global configuration instance
config = Config()