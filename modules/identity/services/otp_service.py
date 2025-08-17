"""
OTP service for ITADIAS Identity Microservice
"""
import random
import string
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from models import Candidate, OTPVerification
from config import config
from services.communication_service import CommunicationService

logger = logging.getLogger(__name__)

class OTPService:
    """Service for managing OTP operations"""
    
    def __init__(self):
        self.communication_service = CommunicationService()
    
    def generate_otp(self, length: int = None) -> str:
        """Generate a random OTP code"""
        length = length or config.otp.otp_length
        return ''.join(random.choices(string.digits, k=length))
    
    async def send_otp(
        self, 
        candidate: Candidate, 
        channels: List[str],
        db: AsyncSession = None
    ) -> List[Dict[str, Any]]:
        """Send OTP via specified channels"""
        results = []
        
        for channel in channels:
            try:
                # Generate OTP
                otp_code = self.generate_otp()
                expires_at = datetime.now(timezone.utc) + timedelta(minutes=config.otp.otp_expiry_minutes)
                
                # Determine contact info
                if channel == "email":
                    if not candidate.email:
                        results.append({
                            "channel": channel,
                            "success": False,
                            "error": "Email not available"
                        })
                        continue
                    contact_info = candidate.email
                    
                elif channel == "sms":
                    if not candidate.phone:
                        results.append({
                            "channel": channel,
                            "success": False,
                            "error": "Phone number not available"
                        })
                        continue
                    contact_info = candidate.phone
                    
                    if not config.otp.sms_enabled:
                        results.append({
                            "channel": channel,
                            "success": False,
                            "error": "SMS OTP is disabled"
                        })
                        continue
                else:
                    results.append({
                        "channel": channel,
                        "success": False,
                        "error": f"Unsupported channel: {channel}"
                    })
                    continue
                
                # Send OTP via communication service
                success = False
                error_message = None
                
                if channel == "email":
                    success, error_message = await self.communication_service.send_email_otp(
                        email=contact_info,
                        otp_code=otp_code,
                        candidate_name=f"{candidate.first_name} {candidate.last_name}"
                    )
                elif channel == "sms":
                    success, error_message = await self.communication_service.send_sms_otp(
                        phone=contact_info,
                        otp_code=otp_code,
                        candidate_name=f"{candidate.first_name} {candidate.last_name}"
                    )
                
                # Store OTP verification record if we have database access
                if db and success:
                    try:
                        otp_verification = OTPVerification(
                            candidate_id=candidate.id,
                            otp_code=otp_code,
                            channel=channel,
                            contact_info=contact_info,
                            expires_at=expires_at
                        )
                        db.add(otp_verification)
                        await db.commit()
                        logger.info(f"OTP stored for candidate {candidate.id} via {channel}")
                    except Exception as e:
                        logger.error(f"Failed to store OTP verification: {e}")
                        await db.rollback()
                
                results.append({
                    "channel": channel,
                    "success": success,
                    "error": error_message if not success else None,
                    "expires_at": expires_at.isoformat() if success else None
                })
                
                if success:
                    logger.info(f"OTP sent to candidate {candidate.id} via {channel}")
                else:
                    logger.warning(f"Failed to send OTP to candidate {candidate.id} via {channel}: {error_message}")
                    
            except Exception as e:
                logger.error(f"Error sending OTP via {channel}: {e}")
                results.append({
                    "channel": channel,
                    "success": False,
                    "error": str(e)
                })
        
        return results
    
    async def verify_otp(
        self,
        candidate_id: str,
        otp_code: str,
        channel: str,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Verify OTP code"""
        try:
            from sqlalchemy import select, and_
            
            # Find the OTP verification record
            result = await db.execute(
                select(OTPVerification).where(
                    and_(
                        OTPVerification.candidate_id == candidate_id,
                        OTPVerification.channel == channel,
                        OTPVerification.is_verified == False,
                        OTPVerification.expires_at > datetime.now(timezone.utc)
                    )
                ).order_by(OTPVerification.created_at.desc())
            )
            
            otp_verification = result.scalar_one_or_none()
            
            if not otp_verification:
                return {
                    "success": False,
                    "message": "No valid OTP found or OTP expired"
                }
            
            # Check attempts
            if otp_verification.attempts >= config.otp.max_attempts:
                return {
                    "success": False,
                    "message": "Maximum OTP attempts exceeded"
                }
            
            # Increment attempts
            otp_verification.attempts += 1
            
            # Verify OTP code
            if otp_verification.otp_code != otp_code:
                await db.commit()
                return {
                    "success": False,
                    "message": "Invalid OTP code",
                    "attempts_remaining": config.otp.max_attempts - otp_verification.attempts
                }
            
            # Mark as verified
            otp_verification.is_verified = True
            otp_verification.verified_at = datetime.now(timezone.utc)
            
            # Update candidate verification status
            candidate = await db.get(Candidate, candidate_id)
            if candidate:
                candidate.is_verified = True
            
            await db.commit()
            
            logger.info(f"OTP verified for candidate {candidate_id} via {channel}")
            
            return {
                "success": True,
                "message": "OTP verified successfully",
                "candidate_verified": True
            }
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Error verifying OTP: {e}")
            return {
                "success": False,
                "message": "Internal server error"
            }