"""
Tests for ITADIAS Identity Microservice models
"""
import pytest
import uuid
from datetime import datetime, timezone, timedelta
from models import Candidate, OTPVerification, CandidateCreate, CandidateResponse

class TestCandidateModel:
    """Test Candidate SQLAlchemy model"""
    
    async def test_create_candidate(self, test_db_session):
        """Test creating a candidate"""
        candidate = Candidate(
            email="test@example.com",
            phone="+1234567890",
            first_name="John",
            last_name="Doe"
        )
        
        test_db_session.add(candidate)
        await test_db_session.commit()
        await test_db_session.refresh(candidate)
        
        assert candidate.id is not None
        assert candidate.email == "test@example.com"
        assert candidate.phone == "+1234567890"
        assert candidate.first_name == "John"
        assert candidate.last_name == "Doe"
        assert candidate.is_verified is False
        assert candidate.is_active is True
        assert candidate.created_at is not None
        assert candidate.updated_at is not None

    async def test_candidate_unique_email(self, test_db_session):
        """Test that email is unique"""
        candidate1 = Candidate(
            email="test@example.com",
            first_name="John",
            last_name="Doe"
        )
        
        candidate2 = Candidate(
            email="test@example.com",
            first_name="Jane",
            last_name="Smith"
        )
        
        test_db_session.add(candidate1)
        await test_db_session.commit()
        
        test_db_session.add(candidate2)
        
        with pytest.raises(Exception):  # Should raise integrity error
            await test_db_session.commit()

class TestOTPVerificationModel:
    """Test OTPVerification SQLAlchemy model"""
    
    async def test_create_otp_verification(self, test_db_session, created_candidate):
        """Test creating an OTP verification"""
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
        
        otp_verification = OTPVerification(
            candidate_id=created_candidate.id,
            otp_code="123456",
            channel="email",
            contact_info="test@example.com",
            expires_at=expires_at
        )
        
        test_db_session.add(otp_verification)
        await test_db_session.commit()
        await test_db_session.refresh(otp_verification)
        
        assert otp_verification.id is not None
        assert otp_verification.candidate_id == created_candidate.id
        assert otp_verification.otp_code == "123456"
        assert otp_verification.channel == "email"
        assert otp_verification.contact_info == "test@example.com"
        assert otp_verification.attempts == 0
        assert otp_verification.is_verified is False
        assert otp_verification.expires_at == expires_at

class TestPydanticModels:
    """Test Pydantic models for API"""
    
    def test_candidate_create_valid(self):
        """Test valid CandidateCreate model"""
        data = {
            "email": "test@example.com",
            "phone": "+1234567890",
            "first_name": "John",
            "last_name": "Doe",
            "send_otp": True,
            "otp_channel": "email"
        }
        
        candidate = CandidateCreate(**data)
        
        assert candidate.email == "test@example.com"
        assert candidate.phone == "+1234567890"
        assert candidate.first_name == "John"
        assert candidate.last_name == "Doe"
        assert candidate.send_otp is True
        assert candidate.otp_channel == "email"
    
    def test_candidate_create_invalid_email(self):
        """Test CandidateCreate with invalid email"""
        data = {
            "email": "invalid-email",
            "first_name": "John",
            "last_name": "Doe"
        }
        
        with pytest.raises(ValueError):
            CandidateCreate(**data)
    
    def test_candidate_create_invalid_phone(self):
        """Test CandidateCreate with invalid phone"""
        data = {
            "email": "test@example.com",
            "phone": "invalid-phone",
            "first_name": "John",
            "last_name": "Doe"
        }
        
        with pytest.raises(ValueError):
            CandidateCreate(**data)
    
    def test_candidate_create_invalid_otp_channel(self):
        """Test CandidateCreate with invalid OTP channel"""
        data = {
            "email": "test@example.com",
            "first_name": "John",
            "last_name": "Doe",
            "otp_channel": "invalid"
        }
        
        with pytest.raises(ValueError):
            CandidateCreate(**data)
    
    def test_candidate_response_from_orm(self, created_candidate):
        """Test CandidateResponse from ORM model"""
        response = CandidateResponse.from_orm(created_candidate)
        
        assert response.id == created_candidate.id
        assert response.email == created_candidate.email
        assert response.phone == created_candidate.phone
        assert response.first_name == created_candidate.first_name
        assert response.last_name == created_candidate.last_name
        assert response.is_verified == created_candidate.is_verified
        assert response.is_active == created_candidate.is_active