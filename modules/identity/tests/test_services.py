"""
Tests for ITADIAS Identity Microservice services
"""
import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime, timezone, timedelta

from services.candidate_service import CandidateService
from services.otp_service import OTPService
from services.event_service import EventService
from services.communication_service import CommunicationService
from models import Candidate, CandidateCreate, OTPVerification

class TestCandidateService:
    """Test CandidateService"""
    
    @pytest.mark.asyncio
    async def test_create_candidate(self, test_db_session):
        """Test creating a candidate"""
        service = CandidateService(test_db_session)
        
        candidate_data = CandidateCreate(
            email="test@example.com",
            phone="+1234567890",
            first_name="John",
            last_name="Doe"
        )
        
        candidate = await service.create(candidate_data)
        
        assert candidate.id is not None
        assert candidate.email == "test@example.com"
        assert candidate.phone == "+1234567890"
        assert candidate.first_name == "John"
        assert candidate.last_name == "Doe"
    
    @pytest.mark.asyncio
    async def test_get_candidate_by_id(self, test_db_session, created_candidate):
        """Test getting candidate by ID"""
        service = CandidateService(test_db_session)
        
        result = await service.get_by_id(created_candidate.id)
        
        assert result is not None
        assert result.id == created_candidate.id
        assert result.email == created_candidate.email
    
    @pytest.mark.asyncio
    async def test_get_candidate_by_email(self, test_db_session, created_candidate):
        """Test getting candidate by email"""
        service = CandidateService(test_db_session)
        
        result = await service.get_by_email(created_candidate.email)
        
        assert result is not None
        assert result.id == created_candidate.id
        assert result.email == created_candidate.email
    
    @pytest.mark.asyncio
    async def test_update_verification_status(self, test_db_session, created_candidate):
        """Test updating candidate verification status"""
        service = CandidateService(test_db_session)
        
        result = await service.update_verification_status(created_candidate.id, True)
        
        assert result is not None
        assert result.is_verified is True

class TestOTPService:
    """Test OTPService"""
    
    def test_generate_otp(self):
        """Test OTP generation"""
        service = OTPService()
        
        otp = service.generate_otp()
        
        assert len(otp) == 6
        assert otp.isdigit()
        
        # Test custom length
        otp_custom = service.generate_otp(length=8)
        assert len(otp_custom) == 8
        assert otp_custom.isdigit()
    
    @pytest.mark.asyncio
    async def test_send_otp_email_success(self, created_candidate):
        """Test successful email OTP sending"""
        service = OTPService()
        
        with patch.object(service.communication_service, 'send_email_otp', return_value=(True, None)):
            results = await service.send_otp(created_candidate, ["email"])
            
            assert len(results) == 1
            assert results[0]["channel"] == "email"
            assert results[0]["success"] is True
            assert "expires_at" in results[0]
    
    @pytest.mark.asyncio
    async def test_send_otp_email_failure(self, created_candidate):
        """Test failed email OTP sending"""
        service = OTPService()
        
        with patch.object(service.communication_service, 'send_email_otp', return_value=(False, "SendGrid error")):
            results = await service.send_otp(created_candidate, ["email"])
            
            assert len(results) == 1
            assert results[0]["channel"] == "email"
            assert results[0]["success"] is False
            assert results[0]["error"] == "SendGrid error"
    
    @pytest.mark.asyncio
    async def test_send_otp_sms_disabled(self, created_candidate):
        """Test SMS OTP when SMS is disabled"""
        service = OTPService()
        
        results = await service.send_otp(created_candidate, ["sms"])
        
        assert len(results) == 1
        assert results[0]["channel"] == "sms"
        assert results[0]["success"] is False
        assert "disabled" in results[0]["error"]

class TestEventService:
    """Test EventService"""
    
    @pytest.mark.asyncio
    async def test_initialize_without_rabbitmq(self):
        """Test initializing event service without RabbitMQ"""
        service = EventService()
        
        # Should not raise exception even if RabbitMQ is not available
        await service.initialize()
        
        # Should fall back to in-memory storage
        assert service.connection is None
        assert service.channel is None
        assert service.exchange is None
    
    @pytest.mark.asyncio
    async def test_publish_event_fallback(self, created_candidate):
        """Test event publishing with fallback storage"""
        service = EventService()
        await service.initialize()  # This will fail to connect to RabbitMQ
        
        result = await service.publish_candidate_created(created_candidate)
        
        assert result is True
        
        # Check fallback storage
        events = service.get_fallback_events()
        assert len(events) == 1
        assert events[0]["event_type"] == "CandidateCreated"
        assert events[0]["entity_id"] == str(created_candidate.id)
    
    @pytest.mark.asyncio
    async def test_clear_fallback_events(self):
        """Test clearing fallback events"""
        service = EventService()
        
        # Add some events
        service.fallback_events.append({"test": "event"})
        assert len(service.get_fallback_events()) == 1
        
        # Clear events
        service.clear_fallback_events()
        assert len(service.get_fallback_events()) == 0

class TestCommunicationService:
    """Test CommunicationService"""
    
    @pytest.mark.asyncio
    async def test_send_email_otp_no_config(self):
        """Test email OTP without SendGrid configuration"""
        service = CommunicationService()
        
        # Should simulate sending since no API key is configured
        success, error = await service.send_email_otp(
            email="test@example.com",
            otp_code="123456",
            candidate_name="John Doe"
        )
        
        assert success is True
        assert error is None
    
    @pytest.mark.asyncio
    async def test_send_sms_otp_disabled(self):
        """Test SMS OTP when disabled"""
        service = CommunicationService()
        
        success, error = await service.send_sms_otp(
            phone="+1234567890",
            otp_code="123456",
            candidate_name="John Doe"
        )
        
        assert success is False
        assert "disabled" in error