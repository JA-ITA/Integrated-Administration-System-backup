"""
Core application configuration using Pydantic Settings.
Manages environment variables, database connections, and feature flags.
"""

import os
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import validator
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Application
    APP_NAME: str = "Island Traffic Authority Driver Platform"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    
    # API Configuration
    API_PREFIX: str = "/api"
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    
    # Database Configuration
    DATABASE_URL: str = "postgresql://ita_admin:ita_secure_2024@localhost:5432/ita_driver_platform"
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20
    DATABASE_POOL_TIMEOUT: int = 30
    DATABASE_POOL_RECYCLE: int = 3600
    
    # Redis Configuration (for caching and sessions)
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_PASSWORD: Optional[str] = None
    
    # RabbitMQ Configuration
    RABBITMQ_URL: str = "amqp://ita_admin:ita_rabbit_2024@localhost:5672/ita_vhost"
    
    # Security Configuration
    SECRET_KEY: str = "your-super-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # CORS Configuration
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:3001"]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: List[str] = ["*"]
    CORS_ALLOW_HEADERS: List[str] = ["*"]
    
    # File Upload Configuration
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_EXTENSIONS: List[str] = [".pdf", ".jpg", ".jpeg", ".png", ".doc", ".docx"]
    UPLOAD_PATH: str = "/app/uploads"
    
    # Email Configuration
    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 587
    SMTP_USERNAME: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_USE_TLS: bool = True
    FROM_EMAIL: str = "noreply@ita.gov"
    
    # Payment Configuration
    STRIPE_PUBLISHABLE_KEY: Optional[str] = None
    STRIPE_SECRET_KEY: Optional[str] = None
    STRIPE_WEBHOOK_SECRET: Optional[str] = None
    
    # Feature Flags
    ENABLE_REGISTRATION: bool = True
    ENABLE_ONLINE_PAYMENTS: bool = True
    ENABLE_SMS_NOTIFICATIONS: bool = False
    ENABLE_EMAIL_NOTIFICATIONS: bool = True
    
    # Monitoring and Observability
    JAEGER_AGENT_HOST: str = "localhost"
    JAEGER_AGENT_PORT: int = 6831
    ENABLE_TRACING: bool = True
    ENABLE_METRICS: bool = True
    
    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW: int = 60  # seconds
    
    # Logging Configuration
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    LOG_FILE: Optional[str] = None
    
    # Testing Configuration
    TESTING: bool = False
    TEST_DATABASE_URL: Optional[str] = None
    
    @validator("ENVIRONMENT")
    def validate_environment(cls, v):
        """Validate environment value."""
        allowed = ["development", "staging", "production", "testing"]
        if v not in allowed:
            raise ValueError(f"Environment must be one of: {allowed}")
        return v
    
    @validator("CORS_ORIGINS", pre=True)
    def parse_cors_origins(cls, v):
        """Parse CORS origins from string or list."""
        if isinstance(v, str):
            return [url.strip() for url in v.split(",")]
        return v
    
    @validator("SECRET_KEY")
    def validate_secret_key(cls, v, values):
        """Ensure secret key is secure in production."""
        environment = values.get("ENVIRONMENT", "development")
        if environment == "production" and v == "your-super-secret-key-change-in-production":
            raise ValueError("SECRET_KEY must be changed in production environment")
        return v
    
    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.ENVIRONMENT == "development"
    
    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.ENVIRONMENT == "production"
    
    @property
    def is_testing(self) -> bool:
        """Check if running in testing mode."""
        return self.TESTING or self.ENVIRONMENT == "testing"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Global settings instance
settings = get_settings()


# Environment-specific configurations
def get_database_url() -> str:
    """Get database URL based on environment."""
    if settings.is_testing and settings.TEST_DATABASE_URL:
        return settings.TEST_DATABASE_URL
    return settings.DATABASE_URL


def get_cors_config() -> dict:
    """Get CORS configuration for FastAPI."""
    return {
        "allow_origins": settings.CORS_ORIGINS,
        "allow_credentials": settings.CORS_ALLOW_CREDENTIALS,
        "allow_methods": settings.CORS_ALLOW_METHODS,
        "allow_headers": settings.CORS_ALLOW_HEADERS,
    }


def get_upload_config() -> dict:
    """Get file upload configuration."""
    return {
        "max_size": settings.MAX_UPLOAD_SIZE,
        "allowed_extensions": settings.ALLOWED_EXTENSIONS,
        "upload_path": settings.UPLOAD_PATH,
    }