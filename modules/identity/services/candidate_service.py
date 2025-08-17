"""
Candidate service for ITADIAS Identity Microservice
"""
import uuid
import logging
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models import Candidate, CandidateCreate

logger = logging.getLogger(__name__)

class CandidateService:
    """Service for managing candidate operations"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create(self, candidate_data: CandidateCreate) -> Candidate:
        """Create a new candidate"""
        try:
            candidate = Candidate(
                email=candidate_data.email,
                phone=candidate_data.phone,
                first_name=candidate_data.first_name,
                last_name=candidate_data.last_name
            )
            
            self.db.add(candidate)
            await self.db.commit()
            await self.db.refresh(candidate)
            
            logger.info(f"Created candidate: {candidate.id}")
            return candidate
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error creating candidate: {e}")
            raise
    
    async def get_by_id(self, candidate_id: uuid.UUID) -> Optional[Candidate]:
        """Get candidate by ID"""
        try:
            result = await self.db.execute(
                select(Candidate).where(Candidate.id == candidate_id)
            )
            return result.scalar_one_or_none()
            
        except Exception as e:
            logger.error(f"Error getting candidate by ID {candidate_id}: {e}")
            raise
    
    async def get_by_email(self, email: str) -> Optional[Candidate]:
        """Get candidate by email"""
        try:
            result = await self.db.execute(
                select(Candidate).where(Candidate.email == email)
            )
            return result.scalar_one_or_none()
            
        except Exception as e:
            logger.error(f"Error getting candidate by email {email}: {e}")
            raise
    
    async def get_by_phone(self, phone: str) -> Optional[Candidate]:
        """Get candidate by phone"""
        try:
            result = await self.db.execute(
                select(Candidate).where(Candidate.phone == phone)
            )
            return result.scalar_one_or_none()
            
        except Exception as e:
            logger.error(f"Error getting candidate by phone {phone}: {e}")
            raise
    
    async def list_candidates(
        self, 
        skip: int = 0, 
        limit: int = 100, 
        active_only: bool = True
    ) -> List[Candidate]:
        """List candidates with pagination"""
        try:
            query = select(Candidate)
            
            if active_only:
                query = query.where(Candidate.is_active == True)
            
            query = query.offset(skip).limit(limit).order_by(Candidate.created_at.desc())
            
            result = await self.db.execute(query)
            return result.scalars().all()
            
        except Exception as e:
            logger.error(f"Error listing candidates: {e}")
            raise
    
    async def update_verification_status(self, candidate_id: uuid.UUID, is_verified: bool) -> Optional[Candidate]:
        """Update candidate verification status"""
        try:
            candidate = await self.get_by_id(candidate_id)
            if not candidate:
                return None
            
            candidate.is_verified = is_verified
            await self.db.commit()
            await self.db.refresh(candidate)
            
            logger.info(f"Updated verification status for candidate {candidate_id}: {is_verified}")
            return candidate
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error updating verification status for candidate {candidate_id}: {e}")
            raise