"""
Configuration for ITADIAS Registration Microservice
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
    user: str = os.getenv("DB_USER", "itadias_user")
    password: str = os.getenv("DB_PASSWORD", "itadias_pass")
    schema: str = "registration"
    
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
class RegistrationConfig:
    """Registration business rules configuration"""
    # Age limits (in years)
    min_age_provisional: float = 16.5
    min_age_class_b: int = 17
    min_age_class_c_ppv: int = 20
    weight_threshold_class_c: int = 7000  # kg
    
    # Document size limits (in bytes)
    max_document_size: int = 5 * 1024 * 1024  # 5MB
    
    # Allowed document types and formats
    allowed_photo_formats: List[str] = None
    allowed_id_proof_formats: List[str] = None
    allowed_medical_formats: List[str] = None
    allowed_other_formats: List[str] = None
    
    def __post_init__(self):
        if self.allowed_photo_formats is None:
            self.allowed_photo_formats = ["jpeg", "jpg", "png"]
        if self.allowed_id_proof_formats is None:
            self.allowed_id_proof_formats = ["jpeg", "jpg", "png", "pdf"]
        if self.allowed_medical_formats is None:
            self.allowed_medical_formats = ["pdf"]
        if self.allowed_other_formats is None:
            self.allowed_other_formats = ["pdf"]

@dataclass
class Config:
    """Main configuration class"""
    environment: str = os.getenv("ENVIRONMENT", "development")
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"
    port: int = int(os.getenv("PORT", "8004"))
    
    db: DatabaseConfig = None
    rabbitmq: RabbitMQConfig = None
    registration: RegistrationConfig = None
    
    def __post_init__(self):
        if self.db is None:
            self.db = DatabaseConfig()
        if self.rabbitmq is None:
            self.rabbitmq = RabbitMQConfig()
        if self.registration is None:
            self.registration = RegistrationConfig()

# Global configuration instance
config = Config()