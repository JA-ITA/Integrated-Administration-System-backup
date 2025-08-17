"""
Identity Module Service Layer - Enhanced for Candidate Management
Business logic for candidate management, OTP verification, and profile management.
"""

import uuid
from datetime import datetime, timedelta
from typing import List, Optional, Tuple, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func, and_, or_
from sqlalchemy.orm import selectinload
from passlib.context import CryptContext

from core.config import settings
from core.exceptions import ValidationError, AuthenticationError, DatabaseError
from core.logging_config import get_logger
from .models import Candidate, OTPAttempt, CandidateDocument, CandidateEvent
from .schemas import (
    CandidateCreateRequest, 
    CandidateResponse,
    CandidateCreateResponse,
    OTPType,
    CandidateStatus,
    PasswordSetRequest
)
from .otp_service import OTPService
from .events import publish_candidate_created_event, publish_candidate_verified_event

logger = get_logger("identity.service")


class CandidateService:
    """Service class for candidate management operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        self.otp_service = OTPService(db)
    
    # Candidate Management
    async def create_candidate(
        self,
        candidate_data: CandidateCreateRequest,
        correlation_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> CandidateCreateResponse:
        """
        Create a new candidate with OTP verification.
        
        Args:
            candidate_data: Candidate creation request data
            correlation_id: Optional correlation ID for tracing
            ip_address: Client IP address
            user_agent: Client user agent
            
        Returns:
            CandidateCreateResponse with candidate info and OTP status
        """
        logger.info(f"Creating candidate: {candidate_data.email}")
        
        # Check if candidate already exists
        existing_candidate = await self.get_candidate_by_email(candidate_data.email)
        if existing_candidate:
            raise ValidationError("Candidate with this email already exists")
        
        # Check for duplicate phone number
        phone_query = select(Candidate).where(Candidate.phone == candidate_data.phone)
        phone_result = await self.db.execute(phone_query)
        if phone_result.scalar_one_or_none():
            raise ValidationError("Candidate with this phone number already exists")
        
        # Check for duplicate national ID if provided
        if candidate_data.national_id:
            national_id_query = select(Candidate).where(Candidate.national_id == candidate_data.national_id)
            national_id_result = await self.db.execute(national_id_query)
            if national_id_result.scalar_one_or_none():
                raise ValidationError("Candidate with this national ID already exists")
        
        try:
            # Create candidate record
            candidate_id = str(uuid.uuid4())
            candidate = Candidate(
                id=candidate_id,
                email=candidate_data.email,
                first_name=candidate_data.first_name,
                last_name=candidate_data.last_name,
                phone=candidate_data.phone,
                date_of_birth=candidate_data.date_of_birth,
                national_id=candidate_data.national_id,
                passport_number=candidate_data.passport_number,
                street_address=candidate_data.street_address,
                city=candidate_data.city,
                postal_code=candidate_data.postal_code,
                country=candidate_data.country,
                preferred_language=candidate_data.preferred_language,
                timezone=candidate_data.timezone,
                status=CandidateStatus.PENDING_VERIFICATION.value,
                is_active=False,  # Will be activated after verification
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            
            # Calculate initial profile completion
            candidate.calculate_profile_completion()
            
            self.db.add(candidate)
            await self.db.commit()
            await self.db.refresh(candidate)
            
            # Send OTP codes
            otp_sent_status = {
                "email": False,
                "phone": False
            }
            
            # Send Email OTP
            try:
                email_otp_code, email_attempt_id = await self.otp_service.create_otp_attempt(
                    candidate_id=candidate.id,
                    otp_type=OTPType.EMAIL,
                    recipient=candidate.email,
                    ip_address=ip_address,
                    user_agent=user_agent
                )
                
                email_sent = await self.otp_service.send_email_otp(
                    email=candidate.email,
                    otp_code=email_otp_code,
                    candidate_name=candidate.full_name
                )
                
                otp_sent_status["email"] = email_sent
                
            except Exception as e:
                logger.error(f"Failed to send email OTP: {str(e)}")
            
            # Send Phone OTP
            try:
                phone_otp_code, phone_attempt_id = await self.otp_service.create_otp_attempt(
                    candidate_id=candidate.id,
                    otp_type=OTPType.PHONE,
                    recipient=candidate.phone,
                    ip_address=ip_address,
                    user_agent=user_agent
                )
                
                phone_sent = await self.otp_service.send_sms_otp(
                    phone=candidate.phone,
                    otp_code=phone_otp_code,
                    candidate_name=candidate.full_name
                )
                
                otp_sent_status["phone"] = phone_sent
                
            except Exception as e:
                logger.error(f"Failed to send phone OTP: {str(e)}")
            
            # Log candidate creation event
            await self._log_candidate_event(
                candidate_id=candidate.id,
                event_type="CandidateCreated",
                event_data={
                    "email": candidate.email,
                    "phone": self._mask_phone(candidate.phone),
                    "full_name": candidate.full_name,
                    "otp_sent": otp_sent_status
                },
                correlation_id=correlation_id,
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            # Publish CandidateCreated event
            await publish_candidate_created_event(
                candidate_id=candidate.id,
                candidate_data={
                    "email": candidate.email,
                    "full_name": candidate.full_name,
                    "phone": candidate.phone,
                    "status": candidate.status,
                    "created_at": candidate.created_at.isoformat()
                },
                correlation_id=correlation_id
            )
            
            # Prepare response
            candidate_response = await self._candidate_to_response(candidate)
            
            next_steps = []
            if otp_sent_status["email"]:
                next_steps.append("Verify your email address using the OTP sent to your email")
            if otp_sent_status["phone"]:
                next_steps.append("Verify your phone number using the OTP sent via SMS")
            if not any(otp_sent_status.values()):
                next_steps.append("Contact support for assistance with verification")
            
            logger.info(f"Candidate created successfully: {candidate.email}")
            
            return CandidateCreateResponse(
                candidate=candidate_response,
                otp_sent=otp_sent_status,
                message="Candidate created successfully. Please verify your email and phone number.",
                next_steps=next_steps
            )
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error creating candidate: {str(e)}")
            raise DatabaseError(f"Failed to create candidate: {str(e)}")
    
    async def get_candidate_by_id(self, candidate_id: str) -> Optional[Candidate]:
        """Get candidate by ID with related data."""
        query = select(Candidate).where(Candidate.id == candidate_id).options(
            selectinload(Candidate.otp_attempts),
            selectinload(Candidate.profile_documents)
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_candidate_by_email(self, email: str) -> Optional[Candidate]:
        """Get candidate by email."""
        query = select(Candidate).where(Candidate.email == email)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_candidate_by_phone(self, phone: str) -> Optional[Candidate]:
        """Get candidate by phone number."""
        query = select(Candidate).where(Candidate.phone == phone)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def verify_candidate_otp(
        self,
        candidate_id: str,
        otp_type: OTPType,
        otp_code: str,
        correlation_id: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Verify OTP for candidate.
        
        Returns:
            Tuple of (success, message)
        """
        success, message = await self.otp_service.verify_otp(
            candidate_id=candidate_id,
            otp_type=otp_type,
            otp_code=otp_code
        )
        
        if success:
            # Publish verification event
            await publish_candidate_verified_event(
                candidate_id=candidate_id,
                verification_type=otp_type.value,
                correlation_id=correlation_id
            )
            
            # Log event
            await self._log_candidate_event(
                candidate_id=candidate_id,
                event_type=f"OTPVerified",
                event_data={
                    "otp_type": otp_type.value,
                    "verified_at": datetime.utcnow().isoformat()
                },
                correlation_id=correlation_id
            )
        
        return success, message
    
    async def resend_otp(
        self,
        candidate_id: str,
        otp_type: OTPType,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Tuple[bool, str]:
        """Resend OTP to candidate."""
        return await self.otp_service.resend_otp(
            candidate_id=candidate_id,
            otp_type=otp_type,
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    async def set_candidate_password(
        self,
        candidate_id: str,
        password: str,
        correlation_id: Optional[str] = None
    ) -> bool:
        """
        Set password for candidate after full verification.
        
        Returns:
            True if password was set successfully
        """
        candidate = await self.get_candidate_by_id(candidate_id)
        if not candidate:
            raise ValidationError("Candidate not found")
        
        if not candidate.is_fully_verified:
            raise ValidationError("Candidate must complete email and phone verification first")
        
        if candidate.hashed_password:
            raise ValidationError("Password already set for this candidate")
        
        # Hash password
        hashed_password = self.pwd_context.hash(password)
        
        # Update candidate
        query = update(Candidate).where(Candidate.id == candidate_id).values(
            hashed_password=hashed_password,
            is_active=True,
            status=CandidateStatus.ACTIVE.value,
            updated_at=datetime.utcnow()
        )
        await self.db.execute(query)
        await self.db.commit()
        
        # Log event
        await self._log_candidate_event(
            candidate_id=candidate_id,
            event_type="PasswordSet",
            event_data={
                "password_set_at": datetime.utcnow().isoformat()
            },
            correlation_id=correlation_id
        )
        
        logger.info(f"Password set for candidate: {candidate_id}")
        return True
    
    async def get_otp_status(self, candidate_id: str) -> Dict[str, Any]:
        """Get OTP verification status for candidate."""
        return await self.otp_service.get_otp_status(candidate_id)
    
    async def list_candidates(
        self,
        page: int = 1,
        limit: int = 20,
        status_filter: Optional[str] = None,
        verified_filter: Optional[bool] = None
    ) -> Tuple[List[Candidate], int]:
        """
        List candidates with pagination and filtering.
        
        Returns:
            Tuple of (candidates, total_count)
        """
        offset = (page - 1) * limit
        
        # Base query
        query = select(Candidate)
        count_query = select(func.count(Candidate.id))
        
        # Apply filters
        if status_filter:
            query = query.where(Candidate.status == status_filter)
            count_query = count_query.where(Candidate.status == status_filter)
        
        if verified_filter is not None:
            if verified_filter:
                # Fully verified candidates
                query = query.where(
                    and_(
                        Candidate.is_email_verified == True,
                        Candidate.is_phone_verified == True
                    )
                )
                count_query = count_query.where(
                    and_(
                        Candidate.is_email_verified == True,
                        Candidate.is_phone_verified == True
                    )
                )
            else:
                # Not fully verified candidates
                query = query.where(
                    or_(
                        Candidate.is_email_verified == False,
                        Candidate.is_phone_verified == False
                    )
                )
                count_query = count_query.where(
                    or_(
                        Candidate.is_email_verified == False,
                        Candidate.is_phone_verified == False
                    )
                )
        
        # Apply pagination and execute
        query = query.offset(offset).limit(limit).order_by(Candidate.created_at.desc())
        
        candidates_result = await self.db.execute(query)
        count_result = await self.db.execute(count_query)
        
        candidates = candidates_result.scalars().all()
        total_count = count_result.scalar()
        
        return list(candidates), total_count
    
    # Helper Methods
    async def _candidate_to_response(self, candidate: Candidate) -> CandidateResponse:
        """Convert Candidate model to CandidateResponse."""
        return CandidateResponse(
            id=candidate.id,
            email=candidate.email,
            first_name=candidate.first_name,
            last_name=candidate.last_name,
            full_name=candidate.full_name,
            phone=candidate.phone,
            date_of_birth=candidate.date_of_birth,
            national_id=self._mask_national_id(candidate.national_id),
            passport_number=self._mask_passport(candidate.passport_number),
            street_address=candidate.street_address,
            city=candidate.city,
            postal_code=candidate.postal_code,
            country=candidate.country,
            status=CandidateStatus(candidate.status),
            is_active=candidate.is_active,
            is_phone_verified=candidate.is_phone_verified,
            is_email_verified=candidate.is_email_verified,
            is_identity_verified=candidate.is_identity_verified,
            is_fully_verified=candidate.is_fully_verified,
            profile_completion_percentage=candidate.profile_completion_percentage,
            created_at=candidate.created_at,
            updated_at=candidate.updated_at,
            verified_at=candidate.verified_at,
            preferred_language=candidate.preferred_language,
            timezone=candidate.timezone
        )
    
    async def _log_candidate_event(
        self,
        candidate_id: str,
        event_type: str,
        event_data: Dict[str, Any],
        correlation_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ):
        """Log candidate event to database."""
        try:
            event = CandidateEvent(
                id=str(uuid.uuid4()),
                candidate_id=candidate_id,
                event_type=event_type,
                event_data=str(event_data),  # Convert to JSON string
                event_source="candidate_service",
                ip_address=ip_address,
                user_agent=user_agent,
                correlation_id=correlation_id,
                created_at=datetime.utcnow()
            )
            
            self.db.add(event)
            await self.db.commit()
            
        except Exception as e:
            logger.error(f"Failed to log candidate event: {str(e)}")
    
    def _mask_national_id(self, national_id: Optional[str]) -> Optional[str]:
        """Mask national ID for response."""
        if not national_id:
            return None
        if len(national_id) > 4:
            return "*" * (len(national_id) - 4) + national_id[-4:]
        return "*" * len(national_id)
    
    def _mask_passport(self, passport: Optional[str]) -> Optional[str]:
        """Mask passport number for response."""
        if not passport:
            return None
        if len(passport) > 3:
            return "*" * (len(passport) - 3) + passport[-3:]
        return "*" * len(passport)
    
    def _mask_phone(self, phone: str) -> str:
        """Mask phone number for logging."""
        if len(phone) > 4:
            return "*" * (len(phone) - 4) + phone[-4:]
        return "*" * len(phone)