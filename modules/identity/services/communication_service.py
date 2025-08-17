"""
Communication service for sending emails and SMS
"""
import logging
from typing import Tuple, Optional
import aiohttp
from config import config

logger = logging.getLogger(__name__)

class CommunicationService:
    """Service for handling email and SMS communications"""
    
    def __init__(self):
        self.sendgrid_available = bool(config.sendgrid.api_key)
        self.twilio_available = bool(config.twilio.account_sid and config.twilio.auth_token)
    
    async def send_email_otp(
        self, 
        email: str, 
        otp_code: str, 
        candidate_name: str
    ) -> Tuple[bool, Optional[str]]:
        """Send OTP via email using SendGrid"""
        if not config.otp.email_enabled:
            return False, "Email OTP is disabled"
        
        if not self.sendgrid_available:
            logger.warning("SendGrid not configured, simulating email send")
            logger.info(f"[SIMULATED] Email OTP {otp_code} sent to {email}")
            return True, None
        
        try:
            import sendgrid
            from sendgrid.helpers.mail import Mail
            
            sg = sendgrid.SendGridAPIClient(api_key=config.sendgrid.api_key)
            
            # Create email content
            subject = "Your ITADIAS Verification Code"
            html_content = f"""
            <html>
                <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                    <div style="background-color: #f8f9fa; padding: 20px; text-align: center;">
                        <h1 style="color: #343a40;">ITADIAS Identity Verification</h1>
                    </div>
                    <div style="padding: 30px 20px;">
                        <p>Hello {candidate_name},</p>
                        <p>Your verification code is:</p>
                        <div style="text-align: center; margin: 30px 0;">
                            <span style="font-size: 32px; font-weight: bold; color: #007bff; 
                                         background-color: #f8f9fa; padding: 15px 30px; 
                                         border-radius: 8px; letter-spacing: 5px;">
                                {otp_code}
                            </span>
                        </div>
                        <p>This code will expire in {config.otp.otp_expiry_minutes} minutes.</p>
                        <p style="margin-top: 30px; color: #6c757d; font-size: 14px;">
                            If you didn't request this code, please ignore this email.
                        </p>
                    </div>
                    <div style="background-color: #f8f9fa; padding: 20px; text-align: center;">
                        <p style="color: #6c757d; font-size: 12px; margin: 0;">
                            © 2024 ITADIAS. All rights reserved.
                        </p>
                    </div>
                </body>
            </html>
            """
            
            message = Mail(
                from_email=(config.sendgrid.from_email, config.sendgrid.from_name),
                to_emails=email,
                subject=subject,
                html_content=html_content
            )
            
            response = sg.send(message)
            
            if response.status_code in [200, 201, 202]:
                logger.info(f"Email OTP sent successfully to {email}")
                return True, None
            else:
                error_msg = f"SendGrid returned status {response.status_code}"
                logger.error(f"Failed to send email OTP: {error_msg}")
                return False, error_msg
                
        except Exception as e:
            error_msg = f"Email sending error: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    async def send_sms_otp(
        self, 
        phone: str, 
        otp_code: str, 
        candidate_name: str
    ) -> Tuple[bool, Optional[str]]:
        """Send OTP via SMS using Twilio"""
        if not config.otp.sms_enabled:
            return False, "SMS OTP is disabled"
        
        if not self.twilio_available:
            logger.warning("Twilio not configured, simulating SMS send")
            logger.info(f"[SIMULATED] SMS OTP {otp_code} sent to {phone}")
            return True, None
        
        try:
            from twilio.rest import Client
            
            client = Client(config.twilio.account_sid, config.twilio.auth_token)
            
            # Create SMS content
            message_body = f"""
ITADIAS Verification

Hello {candidate_name},

Your verification code is: {otp_code}

This code expires in {config.otp.otp_expiry_minutes} minutes.

If you didn't request this, please ignore.
            """.strip()
            
            message = client.messages.create(
                body=message_body,
                from_=config.twilio.from_phone,
                to=phone
            )
            
            if message.sid:
                logger.info(f"SMS OTP sent successfully to {phone}")
                return True, None
            else:
                error_msg = "Failed to get SMS SID"
                logger.error(f"Failed to send SMS OTP: {error_msg}")
                return False, error_msg
                
        except Exception as e:
            error_msg = f"SMS sending error: {str(e)}"
            logger.error(error_msg)
            return False, error_msg