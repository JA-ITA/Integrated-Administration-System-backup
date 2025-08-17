"""
Unit tests for OTP Service
Tests for OTP generation, sending, and verification functionality.
"""

import pytest
import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch, MagicMock

from sqlalchemy.ext.asyncio import AsyncSession
from core.exceptions import ValidationError
from ..otp_service import OTPService
from ..schemas import OTPType
from ..models import Candidate, OTPAttempt


class TestOTPService:
    """Test cases for OTPService."""
    
    @pytest.fixture
    def mock_db_session(self):
        """Mock database session."""
        mock_session = AsyncMock(spec=AsyncSession)
        return mock_session
    
    @pytest.fixture
    def otp_service(self, mock_db_session):
        """OTPService instance with mocked database."""
        return OTPService(mock_db_session)
    
    @pytest.fixture
    def mock_candidate(self):
        """Mock candidate for testing."""
        return Candidate(
            id="test-candidate-id",
            email="test@example.com",
            first_name="John",
            last_name="Doe",
            phone="4411234567",
            is_email_verified=False,
            is_phone_verified=False
        )
    
    def test_generate_otp_default_length(self, otp_service):
        """Test OTP generation with default length."""
        otp = otp_service.generate_otp()
        
        assert len(otp) == 6
        assert otp.isdigit()
    
    def test_generate_otp_custom_length(self, otp_service):
        """Test OTP generation with custom length."""
        otp = otp_service.generate_otp(length=4)
        
        assert len(otp) == 4
        assert otp.isdigit()
    
    @pytest.mark.asyncio
    async def test_create_otp_attempt_success(self, otp_service, mock_db_session):
        """Test successful OTP attempt creation."""
        candidate_id = "test-candidate-id"
        otp_type = OTPType.EMAIL
        recipient = "test@example.com"
        
        # Mock no existing OTP attempts
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = None
        
        otp_code, attempt_id = await otp_service.create_otp_attempt(
            candidate_id=candidate_id,
            otp_type=otp_type,
            recipient=recipient,
            ip_address="127.0.0.1",
            user_agent="Test Agent"
        )
        
        # Assertions
        assert len(otp_code) == 6
        assert otp_code.isdigit()
        assert attempt_id is not None
        
        # Verify database operations
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_otp_attempt_cooldown(self, otp_service, mock_db_session):
        """Test OTP attempt creation during cooldown period."""
        candidate_id = "test-candidate-id"
        otp_type = OTPType.EMAIL
        recipient = "test@example.com"
        
        # Mock existing recent OTP attempt
        recent_attempt = OTPAttempt(
            id="recent-attempt-id",
            candidate_id=candidate_id,
            otp_type=otp_type.value,
            otp_code="123456",
            recipient=recipient,
            created_at=datetime.utcnow() - timedelta(seconds=30),  # 30 seconds ago
            expires_at=datetime.utcnow() + timedelta(minutes=5),
            is_verified=False
        )
        
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = recent_attempt
        
        # Expect ValidationError due to cooldown
        with pytest.raises(ValidationError, match="Please wait .* seconds before requesting another OTP"):
            await otp_service.create_otp_attempt(
                candidate_id=candidate_id,
                otp_type=otp_type,
                recipient=recipient
            )
    
    @pytest.mark.asyncio
    async def test_send_email_otp_development(self, otp_service):
        """Test email OTP sending in development mode."""
        with patch('modules.identity.otp_service.settings') as mock_settings:
            mock_settings.ENVIRONMENT = "development"
            mock_settings.SMTP_HOST = "localhost"
            mock_settings.SMTP_PORT = 1025
            mock_settings.FROM_EMAIL = "test@ita.gov"
            
            # Mock SMTP
            with patch('modules.identity.otp_service.smtplib.SMTP') as mock_smtp:
                mock_server = MagicMock()
                mock_smtp.return_value = mock_server
                
                result = await otp_service.send_email_otp(
                    email="test@example.com",
                    otp_code="123456",
                    candidate_name="John Doe"
                )
                
                assert result == True
                mock_smtp.assert_called_once()
                mock_server.send_message.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_email_otp_failure(self, otp_service):
        """Test email OTP sending failure."""
        with patch('modules.identity.otp_service.settings') as mock_settings:
            mock_settings.ENVIRONMENT = "production"
            mock_settings.SMTP_HOST = "smtp.example.com"
            mock_settings.SMTP_PORT = 587
            mock_settings.SMTP_USERNAME = "user"
            mock_settings.SMTP_PASSWORD = "pass"
            mock_settings.FROM_EMAIL = "test@ita.gov"
            
            # Mock SMTP failure
            with patch('modules.identity.otp_service.smtplib.SMTP') as mock_smtp:
                mock_smtp.side_effect = Exception("SMTP connection failed")
                
                result = await otp_service.send_email_otp(
                    email="test@example.com",
                    otp_code="123456",
                    candidate_name="John Doe"
                )
                
                assert result == False
    
    @pytest.mark.asyncio
    async def test_send_sms_otp_development(self, otp_service):
        """Test SMS OTP sending in development mode."""
        with patch('modules.identity.otp_service.settings') as mock_settings:
            mock_settings.ENVIRONMENT = "development"
            
            result = await otp_service.send_sms_otp(
                phone="4411234567",
                otp_code="123456",
                candidate_name="John Doe"
            )
            
            # In development, should return True and log the OTP
            assert result == True
    
    @pytest.mark.asyncio
    async def test_verify_otp_success(self, otp_service, mock_db_session):
        """Test successful OTP verification."""
        candidate_id = "test-candidate-id"
        otp_type = OTPType.EMAIL
        correct_otp = "123456"
        
        # Mock OTP attempt
        mock_attempt = OTPAttempt(
            id="attempt-id",
            candidate_id=candidate_id,
            otp_type=otp_type.value,
            otp_code=correct_otp,
            recipient="test@example.com",
            created_at=datetime.utcnow() - timedelta(minutes=2),
            expires_at=datetime.utcnow() + timedelta(minutes=8),
            attempts_count=0,
            max_attempts=3,
            is_verified=False
        )
        
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = mock_attempt
        
        # Mock candidate update method
        with patch.object(otp_service, '_update_candidate_verification_status') as mock_update:
            mock_update.return_value = None
            
            success, message = await otp_service.verify_otp(
                candidate_id=candidate_id,
                otp_type=otp_type,
                otp_code=correct_otp
            )
            
            assert success == True
            assert message == "OTP verified successfully"
            assert mock_attempt.is_verified == True
            assert mock_attempt.attempts_count == 1
            mock_update.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_verify_otp_wrong_code(self, otp_service, mock_db_session):
        """Test OTP verification with wrong code."""
        candidate_id = "test-candidate-id"
        otp_type = OTPType.EMAIL
        wrong_otp = "654321"
        
        # Mock OTP attempt
        mock_attempt = OTPAttempt(
            id="attempt-id",
            candidate_id=candidate_id,
            otp_type=otp_type.value,
            otp_code="123456",  # Correct code
            recipient="test@example.com",
            created_at=datetime.utcnow() - timedelta(minutes=2),
            expires_at=datetime.utcnow() + timedelta(minutes=8),
            attempts_count=0,
            max_attempts=3,
            is_verified=False
        )
        
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = mock_attempt
        
        success, message = await otp_service.verify_otp(
            candidate_id=candidate_id,
            otp_type=otp_type,
            otp_code=wrong_otp
        )
        
        assert success == False
        assert "Invalid OTP code" in message
        assert "2 attempts remaining" in message
        assert mock_attempt.is_verified == False
        assert mock_attempt.attempts_count == 1
    
    @pytest.mark.asyncio
    async def test_verify_otp_expired(self, otp_service, mock_db_session):
        """Test OTP verification with expired code."""
        candidate_id = "test-candidate-id"
        otp_type = OTPType.EMAIL
        
        # Mock expired OTP attempt
        mock_attempt = OTPAttempt(
            id="attempt-id",
            candidate_id=candidate_id,
            otp_type=otp_type.value,
            otp_code="123456",
            recipient="test@example.com",
            created_at=datetime.utcnow() - timedelta(minutes=15),
            expires_at=datetime.utcnow() - timedelta(minutes=5),  # Expired 5 minutes ago
            attempts_count=0,
            max_attempts=3,
            is_verified=False
        )
        
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = mock_attempt
        
        success, message = await otp_service.verify_otp(
            candidate_id=candidate_id,
            otp_type=otp_type,
            otp_code="123456"
        )
        
        assert success == False
        assert message == "OTP has expired. Please request a new one"
    
    @pytest.mark.asyncio
    async def test_verify_otp_exhausted_attempts(self, otp_service, mock_db_session):
        """Test OTP verification with exhausted attempts."""
        candidate_id = "test-candidate-id"
        otp_type = OTPType.EMAIL
        
        # Mock OTP attempt with exhausted attempts
        mock_attempt = OTPAttempt(
            id="attempt-id",
            candidate_id=candidate_id,
            otp_type=otp_type.value,
            otp_code="123456",
            recipient="test@example.com",
            created_at=datetime.utcnow() - timedelta(minutes=2),
            expires_at=datetime.utcnow() + timedelta(minutes=8),
            attempts_count=3,  # Already at max
            max_attempts=3,
            is_verified=False
        )
        
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = mock_attempt
        
        success, message = await otp_service.verify_otp(
            candidate_id=candidate_id,
            otp_type=otp_type,
            otp_code="123456"
        )
        
        assert success == False
        assert message == "Maximum verification attempts reached. Please request a new OTP"
    
    @pytest.mark.asyncio
    async def test_verify_otp_no_attempt_found(self, otp_service, mock_db_session):
        """Test OTP verification with no attempt found."""
        candidate_id = "test-candidate-id"
        otp_type = OTPType.EMAIL
        
        # Mock no OTP attempt found
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = None
        
        success, message = await otp_service.verify_otp(
            candidate_id=candidate_id,
            otp_type=otp_type,
            otp_code="123456"
        )
        
        assert success == False
        assert message == "No OTP found for this candidate"
    
    @pytest.mark.asyncio
    async def test_resend_otp_success(self, otp_service, mock_db_session, mock_candidate):
        """Test successful OTP resend."""
        candidate_id = mock_candidate.id
        otp_type = OTPType.EMAIL
        
        # Mock candidate retrieval
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = mock_candidate
        
        with patch.object(otp_service, 'create_otp_attempt') as mock_create:
            with patch.object(otp_service, 'send_email_otp') as mock_send:
                
                mock_create.return_value = ("123456", "attempt-id")
                mock_send.return_value = True
                
                success, message = await otp_service.resend_otp(
                    candidate_id=candidate_id,
                    otp_type=otp_type
                )
                
                assert success == True
                assert "OTP sent successfully" in message
                mock_create.assert_called_once()
                mock_send.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_resend_otp_candidate_not_found(self, otp_service, mock_db_session):
        """Test OTP resend with candidate not found."""
        candidate_id = "nonexistent-id"
        otp_type = OTPType.EMAIL
        
        # Mock no candidate found
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = None
        
        success, message = await otp_service.resend_otp(
            candidate_id=candidate_id,
            otp_type=otp_type
        )
        
        assert success == False
        assert message == "Candidate not found"
    
    @pytest.mark.asyncio
    async def test_get_otp_status_success(self, otp_service, mock_db_session, mock_candidate):
        """Test successful OTP status retrieval."""
        candidate_id = mock_candidate.id
        
        # Mock candidate retrieval
        mock_db_session.execute.side_effect = [
            # Candidate query
            AsyncMock(scalar_one_or_none=lambda: mock_candidate),
            # Email OTP query
            AsyncMock(scalar_one_or_none=lambda: None),
            # Phone OTP query  
            AsyncMock(scalar_one_or_none=lambda: None)
        ]
        
        result = await otp_service.get_otp_status(candidate_id)
        
        assert result["candidate_id"] == candidate_id
        assert result["email_otp_status"] == "not_sent"
        assert result["phone_otp_status"] == "not_sent"
        assert result["email_verified"] == False
        assert result["phone_verified"] == False
        assert result["can_set_password"] == False
    
    @pytest.mark.asyncio
    async def test_get_otp_status_candidate_not_found(self, otp_service, mock_db_session):
        """Test OTP status retrieval with candidate not found."""
        candidate_id = "nonexistent-id"
        
        # Mock no candidate found
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = None
        
        with pytest.raises(ValidationError, match="Candidate not found"):
            await otp_service.get_otp_status(candidate_id)
    
    def test_mask_email(self, otp_service):
        """Test email masking for logging."""
        email = "john.doe@example.com"
        masked = otp_service._mask_email(email)
        
        assert masked == "j******e@example.com"
    
    def test_mask_phone(self, otp_service):
        """Test phone number masking for logging."""
        phone = "4411234567"
        masked = otp_service._mask_phone(phone)
        
        assert masked == "******4567"
    
    def test_mask_recipient_email(self, otp_service):
        """Test recipient masking for email."""
        email = "test@example.com"
        masked = otp_service._mask_recipient(email)
        
        assert masked == "t**t@example.com"
    
    def test_mask_recipient_phone(self, otp_service):
        """Test recipient masking for phone."""
        phone = "4411234567"
        masked = otp_service._mask_recipient(phone)
        
        assert masked == "******4567"


class TestOTPAttemptModel:
    """Test cases for OTPAttempt model properties."""
    
    def test_otp_attempt_not_expired(self):
        """Test OTP attempt that is not expired."""
        attempt = OTPAttempt(
            id="test-id",
            candidate_id="candidate-id",
            otp_type="email",
            otp_code="123456",
            recipient="test@example.com",
            expires_at=datetime.utcnow() + timedelta(minutes=5),
            attempts_count=0,
            max_attempts=3,
            is_verified=False
        )
        
        assert not attempt.is_expired
        assert not attempt.is_exhausted
        assert attempt.can_attempt
    
    def test_otp_attempt_expired(self):
        """Test expired OTP attempt."""
        attempt = OTPAttempt(
            id="test-id",
            candidate_id="candidate-id",
            otp_type="email",
            otp_code="123456",
            recipient="test@example.com",
            expires_at=datetime.utcnow() - timedelta(minutes=5),
            attempts_count=0,
            max_attempts=3,
            is_verified=False
        )
        
        assert attempt.is_expired
        assert not attempt.can_attempt
    
    def test_otp_attempt_exhausted(self):
        """Test OTP attempt with exhausted attempts."""
        attempt = OTPAttempt(
            id="test-id",
            candidate_id="candidate-id",
            otp_type="email",
            otp_code="123456",
            recipient="test@example.com",
            expires_at=datetime.utcnow() + timedelta(minutes=5),
            attempts_count=3,
            max_attempts=3,
            is_verified=False
        )
        
        assert not attempt.is_expired
        assert attempt.is_exhausted
        assert not attempt.can_attempt
    
    def test_otp_attempt_verified(self):
        """Test verified OTP attempt."""
        attempt = OTPAttempt(
            id="test-id",
            candidate_id="candidate-id",
            otp_type="email",
            otp_code="123456",
            recipient="test@example.com",
            expires_at=datetime.utcnow() + timedelta(minutes=5),
            attempts_count=1,
            max_attempts=3,
            is_verified=True
        )
        
        assert not attempt.is_expired
        assert not attempt.is_exhausted
        assert not attempt.can_attempt  # Can't attempt because already verified