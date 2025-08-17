"""
Identity Module OTP Service
Handles OTP generation, sending, and verification for candidate authentication.
"""

import secrets
import random
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict
import uuid
import asyncio
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_
from twilio.rest import Client as TwilioClient
from twilio.base.exceptions import TwilioException

from core.config import settings
from core.logging_config import get_logger
from core.exceptions import ValidationError, ExternalServiceError
from .models import Candidate, OTPAttempt
from .schemas import OTPType

logger = get_logger("identity.otp")


class OTPService:
    """Service for handling OTP operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.otp_expiry_minutes = 10
        self.max_attempts = 3
        self.resend_cooldown_minutes = 2
        
    def generate_otp(self, length: int = 6) -> str:
        """Generate a secure OTP code."""
        return ''.join([str(random.randint(0, 9)) for _ in range(length)])
    
    async def create_otp_attempt(
        self,
        candidate_id: str,
        otp_type: OTPType,
        recipient: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Tuple[str, str]:  # Returns (otp_code, attempt_id)
        """
        Create a new OTP attempt record.
        
        Returns:
            Tuple of (otp_code, attempt_id)
        """
        # Check if there's an existing valid OTP for this candidate and type
        existing_query = select(OTPAttempt).where(
            and_(
                OTPAttempt.candidate_id == candidate_id,
                OTPAttempt.otp_type == otp_type.value,
                OTPAttempt.expires_at > datetime.utcnow(),
                OTPAttempt.is_verified == False
            )
        ).order_by(OTPAttempt.created_at.desc())
        
        result = await self.db.execute(existing_query)
        existing_attempt = result.scalar_one_or_none()
        
        # Check resend cooldown
        if existing_attempt:
            time_since_last = datetime.utcnow() - existing_attempt.created_at
            if time_since_last.total_seconds() < (self.resend_cooldown_minutes * 60):
                cooldown_remaining = (self.resend_cooldown_minutes * 60) - time_since_last.total_seconds()
                raise ValidationError(
                    f"Please wait {int(cooldown_remaining)} seconds before requesting another OTP"
                )
        
        # Generate new OTP
        otp_code = self.generate_otp()
        attempt_id = str(uuid.uuid4())
        
        # Create OTP attempt record
        otp_attempt = OTPAttempt(
            id=attempt_id,
            candidate_id=candidate_id,
            otp_type=otp_type.value,
            otp_code=otp_code,
            recipient=recipient,
            expires_at=datetime.utcnow() + timedelta(minutes=self.otp_expiry_minutes),
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        self.db.add(otp_attempt)
        await self.db.commit()
        await self.db.refresh(otp_attempt)
        
        logger.info(
            f"OTP attempt created",
            extra={
                "attempt_id": attempt_id,
                "candidate_id": candidate_id,
                "otp_type": otp_type.value,
                "recipient": self._mask_recipient(recipient)
            }
        )
        
        return otp_code, attempt_id
    
    async def send_email_otp(self, email: str, otp_code: str, candidate_name: str) -> bool:
        """
        Send OTP via email.
        
        Returns:
            True if sent successfully, False otherwise
        """
        try:
            # Email configuration
            smtp_server = settings.SMTP_HOST
            smtp_port = settings.SMTP_PORT
            smtp_username = settings.SMTP_USERNAME
            smtp_password = settings.SMTP_PASSWORD
            from_email = settings.FROM_EMAIL
            
            # Create message
            message = MIMEMultipart()
            message["From"] = from_email
            message["To"] = email
            message["Subject"] = "Island Traffic Authority - Email Verification"
            
            # Email body
            body = f"""
            Dear {candidate_name},

            Welcome to the Island Traffic Authority Driver Platform!

            Your email verification code is: {otp_code}

            This code will expire in {self.otp_expiry_minutes} minutes.

            Please enter this code to verify your email address and continue with your driver's license application.

            If you didn't request this code, please ignore this email.

            Best regards,
            Island Traffic Authority
            Digital Services Team
            
            ---
            This is an automated message. Please do not reply to this email.
            For support, visit: https://ita.gov/support
            """
            
            message.attach(MIMEText(body, "plain"))
            
            # Send email
            if smtp_username and smtp_password:
                # SMTP with authentication
                server = smtplib.SMTP(smtp_server, smtp_port)
                server.starttls()
                server.login(smtp_username, smtp_password)
                server.send_message(message)
                server.quit()
            else:
                # SMTP without authentication (for development)
                server = smtplib.SMTP(smtp_server, smtp_port)
                server.send_message(message)
                server.quit()
            
            logger.info(f"Email OTP sent successfully to {self._mask_email(email)}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email OTP: {str(e)}")
            return False
    
    async def send_sms_otp(self, phone: str, otp_code: str, candidate_name: str) -> bool:
        """
        Send OTP via SMS using Twilio.
        
        Returns:
            True if sent successfully, False otherwise
        """
        try:
            # For development, just log the OTP
            if settings.ENVIRONMENT == "development":
                logger.info(
                    f"SMS OTP for development: {otp_code}",
                    extra={
                        "phone": self._mask_phone(phone),
                        "otp_code": otp_code
                    }
                )
                return True
            
            # Production SMS sending logic (if Twilio is configured)
            # This would require TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN in settings
            if hasattr(settings, 'TWILIO_ACCOUNT_SID') and settings.TWILIO_ACCOUNT_SID:
                client = TwilioClient(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
                
                message_body = f"""
Island Traffic Authority

Your phone verification code is: {otp_code}

This code expires in {self.otp_expiry_minutes} minutes.

Reply STOP to opt out.
                """.strip()
                
                message = client.messages.create(
                    body=message_body,
                    from_=settings.TWILIO_PHONE_NUMBER,
                    to=phone
                )
                
                logger.info(f"SMS OTP sent successfully to {self._mask_phone(phone)}")
                return True
            else:
                logger.warning("SMS service not configured, OTP not sent")
                return False
                
        except Exception as e:
            logger.error(f"Failed to send SMS OTP: {str(e)}")
            return False
    
    async def verify_otp(
        self,
        candidate_id: str,
        otp_type: OTPType,
        otp_code: str
    ) -> Tuple[bool, str]:  # Returns (success, message)
        """
        Verify OTP code.
        
        Returns:
            Tuple of (success, message)
        """
        # Find the latest OTP attempt for this candidate and type
        query = select(OTPAttempt).where(
            and_(
                OTPAttempt.candidate_id == candidate_id,
                OTPAttempt.otp_type == otp_type.value,
                OTPAttempt.is_verified == False
            )
        ).order_by(OTPAttempt.created_at.desc())
        
        result = await self.db.execute(query)
        otp_attempt = result.scalar_one_or_none()
        
        if not otp_attempt:
            return False, "No OTP found for this candidate"
        
        # Check if OTP is expired
        if otp_attempt.is_expired:
            return False, "OTP has expired. Please request a new one"
        
        # Check if maximum attempts reached
        if otp_attempt.is_exhausted:
            return False, "Maximum verification attempts reached. Please request a new OTP"
        
        # Increment attempt count
        otp_attempt.attempts_count += 1
        
        # Verify OTP code
        if otp_attempt.otp_code == otp_code:
            # Mark as verified
            otp_attempt.is_verified = True
            otp_attempt.verified_at = datetime.utcnow()
            
            # Update candidate verification status
            await self._update_candidate_verification_status(candidate_id, otp_type)
            
            await self.db.commit()
            
            logger.info(
                f"OTP verified successfully",
                extra={
                    "candidate_id": candidate_id,
                    "otp_type": otp_type.value,
                    "attempt_id": otp_attempt.id
                }
            )
            
            return True, "OTP verified successfully"
        else:
            # Save the failed attempt
            await self.db.commit()
            
            attempts_remaining = otp_attempt.max_attempts - otp_attempt.attempts_count
            if attempts_remaining > 0:
                return False, f"Invalid OTP code. {attempts_remaining} attempts remaining"
            else:
                return False, "Invalid OTP code. Maximum attempts reached. Please request a new OTP"
    
    async def resend_otp(
        self,
        candidate_id: str,
        otp_type: OTPType,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Tuple[bool, str]:  # Returns (success, message)
        """
        Resend OTP to candidate.
        
        Returns:
            Tuple of (success, message)
        """
        # Get candidate information
        candidate_query = select(Candidate).where(Candidate.id == candidate_id)
        result = await self.db.execute(candidate_query)
        candidate = result.scalar_one_or_none()
        
        if not candidate:
            return False, "Candidate not found"
        
        # Determine recipient based on OTP type
        recipient = candidate.email if otp_type == OTPType.EMAIL else candidate.phone
        
        try:
            # Create new OTP attempt
            otp_code, attempt_id = await self.create_otp_attempt(
                candidate_id=candidate_id,
                otp_type=otp_type,
                recipient=recipient,
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            # Send OTP
            if otp_type == OTPType.EMAIL:
                sent = await self.send_email_otp(recipient, otp_code, candidate.full_name)
            else:
                sent = await self.send_sms_otp(recipient, otp_code, candidate.full_name)
            
            if sent:
                return True, f"OTP sent successfully to {self._mask_recipient(recipient)}"
            else:
                return False, "Failed to send OTP. Please try again later"
                
        except ValidationError as e:
            return False, str(e)
        except Exception as e:
            logger.error(f"Error resending OTP: {str(e)}")
            return False, "An error occurred while sending OTP"
    
    async def get_otp_status(self, candidate_id: str) -> Dict[str, any]:
        """Get OTP verification status for a candidate."""
        candidate_query = select(Candidate).where(Candidate.id == candidate_id)
        result = await self.db.execute(candidate_query)
        candidate = result.scalar_one_or_none()
        
        if not candidate:
            raise ValidationError("Candidate not found")
        
        # Get latest OTP attempts
        email_otp_query = select(OTPAttempt).where(
            and_(
                OTPAttempt.candidate_id == candidate_id,
                OTPAttempt.otp_type == "email"
            )
        ).order_by(OTPAttempt.created_at.desc())
        
        phone_otp_query = select(OTPAttempt).where(
            and_(
                OTPAttempt.candidate_id == candidate_id,
                OTPAttempt.otp_type == "phone"
            )
        ).order_by(OTPAttempt.created_at.desc())
        
        email_result = await self.db.execute(email_otp_query)
        phone_result = await self.db.execute(phone_otp_query)
        
        email_otp = email_result.scalar_one_or_none()
        phone_otp = phone_result.scalar_one_or_none()
        
        return {
            "candidate_id": candidate_id,
            "email_otp_status": self._get_otp_attempt_status(email_otp),
            "phone_otp_status": self._get_otp_attempt_status(phone_otp),
            "email_verified": candidate.is_email_verified,
            "phone_verified": candidate.is_phone_verified,
            "can_set_password": candidate.is_email_verified and candidate.is_phone_verified
        }
    
    async def _update_candidate_verification_status(self, candidate_id: str, otp_type: OTPType):
        """Update candidate verification status after successful OTP verification."""
        if otp_type == OTPType.EMAIL:
            field = "is_email_verified"
        else:
            field = "is_phone_verified"
        
        # Update the specific verification field
        query = update(Candidate).where(Candidate.id == candidate_id).values(
            **{field: True},
            updated_at=datetime.utcnow()
        )
        await self.db.execute(query)
        
        # Check if candidate is now fully verified
        candidate_query = select(Candidate).where(Candidate.id == candidate_id)
        result = await self.db.execute(candidate_query)
        candidate = result.scalar_one_or_none()
        
        if candidate and candidate.is_email_verified and candidate.is_phone_verified:
            # Update status to fully verified
            update_query = update(Candidate).where(Candidate.id == candidate_id).values(
                status="fully_verified",
                verified_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            await self.db.execute(update_query)
    
    def _get_otp_attempt_status(self, otp_attempt: Optional[OTPAttempt]) -> str:
        """Get human-readable status of an OTP attempt."""
        if not otp_attempt:
            return "not_sent"
        
        if otp_attempt.is_verified:
            return "verified"
        
        if otp_attempt.is_expired:
            return "expired"
        
        if otp_attempt.is_exhausted:
            return "exhausted"
        
        return "pending"
    
    def _mask_email(self, email: str) -> str:
        """Mask email for logging."""
        if "@" in email:
            local, domain = email.split("@", 1)
            if len(local) > 2:
                masked_local = local[0] + "*" * (len(local) - 2) + local[-1]
            else:
                masked_local = "*" * len(local)
            return f"{masked_local}@{domain}"
        return email
    
    def _mask_phone(self, phone: str) -> str:
        """Mask phone number for logging."""
        if len(phone) > 4:
            return "*" * (len(phone) - 4) + phone[-4:]
        return "*" * len(phone)
    
    def _mask_recipient(self, recipient: str) -> str:
        """Mask recipient (email or phone) for logging."""
        if "@" in recipient:
            return self._mask_email(recipient)
        else:
            return self._mask_phone(recipient)