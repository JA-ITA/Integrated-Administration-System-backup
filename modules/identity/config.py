"""
Configuration management for ITADIAS Identity Microservice
"""
import os
from typing import Optional
from pydantic import BaseModel

class DatabaseConfig(BaseModel):
    """Database configuration"""
    host: str = os.getenv("DB_HOST", "localhost")
    port: int = int(os.getenv("DB_PORT", "5432"))
    name: str = os.getenv("DB_NAME", "identity_db")
    user: str = os.getenv("DB_USER", "identity_user")
    password: str = os.getenv("DB_PASSWORD", "identity_pass")
    schema: str = os.getenv("DB_SCHEMA", "identity")
    
    @property
    def url(self) -> str:
        return f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"

class OTPConfig(BaseModel):
    """OTP service configuration"""
    email_enabled: bool = os.getenv("EMAIL_OTP_ENABLED", "true").lower() == "true"
    sms_enabled: bool = os.getenv("SMS_OTP_ENABLED", "false").lower() == "true"
    otp_length: int = int(os.getenv("OTP_LENGTH", "6"))
    otp_expiry_minutes: int = int(os.getenv("OTP_EXPIRY_MINUTES", "10"))
    max_attempts: int = int(os.getenv("OTP_MAX_ATTEMPTS", "3"))

class SendGridConfig(BaseModel):
    """SendGrid configuration"""
    api_key: Optional[str] = os.getenv("SENDGRID_API_KEY")
    from_email: str = os.getenv("SENDGRID_FROM_EMAIL", "noreply@itadias.com")
    from_name: str = os.getenv("SENDGRID_FROM_NAME", "ITADIAS Identity Service")

class TwilioConfig(BaseModel):
    """Twilio configuration"""
    account_sid: Optional[str] = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token: Optional[str] = os.getenv("TWILIO_AUTH_TOKEN")
    from_phone: Optional[str] = os.getenv("TWILIO_FROM_PHONE")

class RabbitMQConfig(BaseModel):
    """RabbitMQ configuration"""
    host: str = os.getenv("RABBITMQ_HOST", "localhost")
    port: int = int(os.getenv("RABBITMQ_PORT", "5672"))
    user: str = os.getenv("RABBITMQ_USER", "guest")
    password: str = os.getenv("RABBITMQ_PASSWORD", "guest")
    vhost: str = os.getenv("RABBITMQ_VHOST", "/")
    exchange: str = os.getenv("RABBITMQ_EXCHANGE", "identity_events")
    
    @property
    def url(self) -> str:
        return f"amqp://{self.user}:{self.password}@{self.host}:{self.port}{self.vhost}"

class Config:
    """Main configuration class"""
    def __init__(self):
        self.db = DatabaseConfig()
        self.otp = OTPConfig()
        self.sendgrid = SendGridConfig()
        self.twilio = TwilioConfig()
        self.rabbitmq = RabbitMQConfig()
        
        # General settings
        self.environment = os.getenv("ENVIRONMENT", "development")
        self.debug = os.getenv("DEBUG", "false").lower() == "true"
        self.log_level = os.getenv("LOG_LEVEL", "INFO")

# Global config instance
config = Config()