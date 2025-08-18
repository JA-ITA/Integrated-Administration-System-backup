"""
Configuration management for ITADIAS Certificate Microservice
"""
import os
from typing import Optional
from pydantic import BaseModel

class DatabaseConfig(BaseModel):
    """Database configuration"""
    host: str = os.getenv("DB_HOST", "localhost")
    port: int = int(os.getenv("DB_PORT", "5432"))
    name: str = os.getenv("DB_NAME", "certificate_db")
    user: str = os.getenv("DB_USER", "certificate_user")
    password: str = os.getenv("DB_PASSWORD", "certificate_pass")
    schema: str = os.getenv("DB_SCHEMA", "certificate")
    
    @property
    def url(self) -> str:
        return f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"

class StorageConfig(BaseModel):
    """Storage configuration"""
    backend: str = os.getenv("STORAGE_BACKEND", "minio")  # minio or s3
    
    # MinIO Configuration
    minio_endpoint: str = os.getenv("MINIO_ENDPOINT", "minio:9000")
    minio_access_key: str = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
    minio_secret_key: str = os.getenv("MINIO_SECRET_KEY", "minioadmin")
    minio_secure: bool = os.getenv("MINIO_SECURE", "false").lower() == "true"
    
    # AWS S3 Configuration
    aws_access_key_id: str = os.getenv("AWS_ACCESS_KEY_ID", "")
    aws_secret_access_key: str = os.getenv("AWS_SECRET_ACCESS_KEY", "")
    aws_region: str = os.getenv("AWS_REGION", "us-east-1")
    s3_endpoint_url: Optional[str] = os.getenv("S3_ENDPOINT_URL")
    
    # Common Configuration
    bucket_name: str = os.getenv("CERTIFICATES_BUCKET", "certificates")
    presigned_url_expiry: int = int(os.getenv("PRESIGNED_URL_EXPIRY", "3600"))  # 1 hour

class CertificateConfig(BaseModel):
    """Certificate configuration"""
    template_engine: str = os.getenv("TEMPLATE_ENGINE", "handlebars")
    pdf_service_url: str = os.getenv("PDF_SERVICE_URL", "http://localhost:3001")
    max_age_days: int = int(os.getenv("CERTIFICATE_MAX_AGE_DAYS", "365"))  # 1 year
    qr_code_enabled: bool = os.getenv("QR_CODE_ENABLED", "true").lower() == "true"
    qr_base_url: str = os.getenv("QR_BASE_URL", "https://certificates.itadias.com/verify")
    
    # ITADIAS Branding
    brand_color: str = os.getenv("BRAND_COLOR", "#006B54")
    logo_path: str = os.getenv("LOGO_PATH", "/assets/itadias-logo.png")
    font_family: str = os.getenv("FONT_FAMILY", "Roboto")

class RabbitMQConfig(BaseModel):
    """RabbitMQ configuration"""
    host: str = os.getenv("RABBITMQ_HOST", "localhost")
    port: int = int(os.getenv("RABBITMQ_PORT", "5672"))
    user: str = os.getenv("RABBITMQ_USER", "guest")
    password: str = os.getenv("RABBITMQ_PASSWORD", "guest")
    vhost: str = os.getenv("RABBITMQ_VHOST", "/")
    exchange: str = os.getenv("RABBITMQ_EXCHANGE", "certificate_events")
    
    @property
    def url(self) -> str:
        return f"amqp://{self.user}:{self.password}@{self.host}:{self.port}{self.vhost}"

class Config:
    """Main configuration class"""
    def __init__(self):
        self.db = DatabaseConfig()
        self.storage = StorageConfig()
        self.certificate = CertificateConfig()
        self.rabbitmq = RabbitMQConfig()
        
        # General settings
        self.environment = os.getenv("ENVIRONMENT", "development")
        self.debug = os.getenv("DEBUG", "false").lower() == "true"
        self.log_level = os.getenv("LOG_LEVEL", "INFO")

# Global config instance
config = Config()