"""
Candidate API routes for ITADIAS Identity Microservice
"""
import uuid
import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import get_db
from models import Candidate, CandidateCreate, CandidateResponse, CandidateCreateResponse
from services.candidate_service import CandidateService
from services.otp_service import OTPService
from services.event_service import EventService

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/candidates", response_model=CandidateCreateResponse, status_code=201)
async def create_candidate(
    candidate_data: CandidateCreate,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new candidate with optional OTP verification
    
    - **email**: Candidate's email address (required, unique)
    - **phone**: Candidate's phone number (optional, unique if provided)
    - **first_name**: Candidate's first name (required)
    - **last_name**: Candidate's last name (required)
    - **send_otp**: Whether to send OTP for verification (default: true)
    - **otp_channel**: OTP delivery channel - email, sms, or both (default: email)
    """
    try:
        logger.info(f"Creating candidate with email: {candidate_data.email}")
        
        # Check if database is available
        if db is None:
            # Simulate candidate creation without database
            from datetime import datetime, timezone
            import uuid
            
            candidate_id = uuid.uuid4()
            mock_candidate = {
                "id": candidate_id,
                "email": candidate_data.email,
                "phone": candidate_data.phone,
                "first_name": candidate_data.first_name,
                "last_name": candidate_data.last_name,
                "is_verified": False,
                "is_active": True,
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc)
            }
            
            # Simulate OTP sending
            otp_sent = candidate_data.send_otp
            otp_channels = []
            if candidate_data.send_otp:
                if candidate_data.otp_channel in ["email", "both"]:
                    otp_channels.append("email")
                if candidate_data.otp_channel in ["sms", "both"] and candidate_data.phone:
                    otp_channels.append("sms")
            
            message = "Candidate created successfully (simulated - no database)"
            if otp_sent and otp_channels:
                message += f". OTP sent via {', '.join(otp_channels)} (simulated)"
            
            # Simulate event publishing
            event_service = getattr(request.app.state, 'event_service', None)
            if event_service:
                try:
                    # Create a mock candidate object for event publishing
                    class MockCandidate:
                        def __init__(self, data):
                            for key, value in data.items():
                                setattr(self, key, value)
                    
                    mock_candidate_obj = MockCandidate(mock_candidate)
                    await event_service.publish_candidate_created(mock_candidate_obj)
                    logger.info(f"CandidateCreated event published for {candidate_id} (simulated)")
                except Exception as e:
                    logger.error(f"Failed to publish CandidateCreated event: {e}")
            
            return CandidateCreateResponse(
                candidate=mock_candidate,
                otp_sent=otp_sent,
                otp_channels=otp_channels,
                message=message
            )
        
        # Normal database flow (when database is available)
        # Initialize services
        candidate_service = CandidateService(db)
        otp_service = OTPService()
        event_service = getattr(request.app.state, 'event_service', None)
        
        # Check if candidate already exists
        existing = await candidate_service.get_by_email(candidate_data.email)
        if existing:
            raise HTTPException(
                status_code=409,
                detail=f"Candidate with email {candidate_data.email} already exists"
            )
        
        # Check phone uniqueness if provided
        if candidate_data.phone:
            existing_phone = await candidate_service.get_by_phone(candidate_data.phone)
            if existing_phone:
                raise HTTPException(
                    status_code=409,
                    detail=f"Candidate with phone {candidate_data.phone} already exists"
                )
        
        # Create candidate
        candidate = await candidate_service.create(candidate_data)
        logger.info(f"Candidate created with ID: {candidate.id}")
        
        # Prepare response
        otp_sent = False
        otp_channels = []
        message = "Candidate created successfully"
        
        # Send OTP if requested
        if candidate_data.send_otp:
            try:
                channels = []
                if candidate_data.otp_channel in ["email", "both"]:
                    channels.append("email")
                if candidate_data.otp_channel in ["sms", "both"] and candidate_data.phone:
                    channels.append("sms")
                
                if channels:
                    otp_results = await otp_service.send_otp(candidate, channels)
                    otp_sent = any(result["success"] for result in otp_results)
                    otp_channels = [result["channel"] for result in otp_results if result["success"]]
                    
                    if otp_sent:
                        message += f". OTP sent via {', '.join(otp_channels)}"
                    else:
                        message += ". Failed to send OTP"
                        logger.warning(f"Failed to send OTP for candidate {candidate.id}")
                else:
                    message += ". No valid OTP channels available"
                    
            except Exception as e:
                logger.error(f"Error sending OTP for candidate {candidate.id}: {e}")
                message += ". OTP sending failed"
        
        # Publish CandidateCreated event
        if event_service:
            try:
                await event_service.publish_candidate_created(candidate)
                logger.info(f"CandidateCreated event published for {candidate.id}")
            except Exception as e:
                logger.error(f"Failed to publish CandidateCreated event: {e}")
        
        return CandidateCreateResponse(
            candidate=CandidateResponse.from_orm(candidate),
            otp_sent=otp_sent,
            otp_channels=otp_channels,
            message=message
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating candidate: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/candidates/{candidate_id}", response_model=CandidateResponse)
async def get_candidate(
    candidate_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve a candidate by ID
    
    - **candidate_id**: UUID of the candidate to retrieve
    """
    try:
        logger.info(f"Retrieving candidate with ID: {candidate_id}")
        
        candidate_service = CandidateService(db)
        candidate = await candidate_service.get_by_id(candidate_id)
        
        if not candidate:
            raise HTTPException(
                status_code=404,
                detail=f"Candidate with ID {candidate_id} not found"
            )
        
        return CandidateResponse.from_orm(candidate)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving candidate {candidate_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/candidates", response_model=List[CandidateResponse])
async def list_candidates(
    skip: int = 0,
    limit: int = 100,
    active_only: bool = True,
    db: AsyncSession = Depends(get_db)
):
    """
    List candidates with pagination
    
    - **skip**: Number of candidates to skip (default: 0)
    - **limit**: Maximum number of candidates to return (default: 100, max: 1000)
    - **active_only**: Filter for active candidates only (default: true)
    """
    try:
        if limit > 1000:
            limit = 1000
            
        logger.info(f"Listing candidates: skip={skip}, limit={limit}, active_only={active_only}")
        
        candidate_service = CandidateService(db)
        candidates = await candidate_service.list_candidates(skip=skip, limit=limit, active_only=active_only)
        
        return [CandidateResponse.from_orm(candidate) for candidate in candidates]
        
    except Exception as e:
        logger.error(f"Error listing candidates: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")