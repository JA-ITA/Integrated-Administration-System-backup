"""
Unit tests for Candidate Service
Tests for candidate creation, OTP verification, and profile management.
"""

import pytest
import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch, MagicMock

from sqlalchemy.ext.asyncio import AsyncSession
from core.exceptions import ValidationError, DatabaseError
from ..service import CandidateService
from ..schemas import CandidateCreateRequest, OTPType, PasswordSetRequest
from ..models import Candidate, OTPAttempt


class TestCandidateService:
    """Test cases for CandidateService."""
    
    @pytest.fixture
    def mock_db_session(self):
        """Mock database session."""
        mock_session = AsyncMock(spec=AsyncSession)
        return mock_session
    
    @pytest.fixture
    def candidate_service(self, mock_db_session):
        """CandidateService instance with mocked database."""
        return CandidateService(mock_db_session)
    
    @pytest.fixture
    def valid_candidate_request(self):
        """Valid candidate creation request."""
        return CandidateCreateRequest(
            email="test@example.com",
            first_name="John",
            last_name="Doe",
            phone="4411234567",
            date_of_birth="1990-01-01",
            national_id="ABC123456",
            street_address="123 Main St",
            city="Hamilton",
            postal_code="HM01",
            country="Bermuda"
        )
    
    @pytest.mark.asyncio
    async def test_create_candidate_success(self, candidate_service, valid_candidate_request, mock_db_session):
        """Test successful candidate creation."""
        # Mock database queries to return None (no existing candidate)
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = None
        
        # Mock OTP service
        with patch.object(candidate_service.otp_service, 'create_otp_attempt') as mock_create_otp:
            with patch.object(candidate_service.otp_service, 'send_email_otp') as mock_send_email:
                with patch.object(candidate_service.otp_service, 'send_sms_otp') as mock_send_sms:
                    with patch('modules.identity.service.publish_candidate_created_event') as mock_publish:
                        
                        # Configure mocks
                        mock_create_otp.side_effect = [
                            ("123456", "email-attempt-id"),  # Email OTP
                            ("654321", "phone-attempt-id")   # Phone OTP
                        ]
                        mock_send_email.return_value = True
                        mock_send_sms.return_value = True
                        mock_publish.return_value = None
                        
                        # Execute test
                        result = await candidate_service.create_candidate(
                            candidate_data=valid_candidate_request,
                            correlation_id="test-correlation-id"
                        )
                        
                        # Assertions
                        assert result.candidate.email == valid_candidate_request.email
                        assert result.candidate.first_name == valid_candidate_request.first_name
                        assert result.candidate.status.value == "pending_verification"
                        assert result.otp_sent["email"] == True
                        assert result.otp_sent["phone"] == True
                        assert len(result.next_steps) >= 2
                        
                        # Verify database operations
                        mock_db_session.add.assert_called()
                        mock_db_session.commit.assert_called()
                        
                        # Verify OTP operations
                        assert mock_create_otp.call_count == 2
                        mock_send_email.assert_called_once()
                        mock_send_sms.assert_called_once()
                        
                        # Verify event publishing
                        mock_publish.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_candidate_duplicate_email(self, candidate_service, valid_candidate_request, mock_db_session):
        """Test candidate creation with duplicate email."""
        # Mock existing candidate
        existing_candidate = Candidate(
            id="existing-id",
            email=valid_candidate_request.email,
            first_name="Existing",
            last_name="User"
        )
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = existing_candidate
        
        # Execute test and expect ValidationError
        with pytest.raises(ValidationError, match="Candidate with this email already exists"):
            await candidate_service.create_candidate(
                candidate_data=valid_candidate_request,
                correlation_id="test-correlation-id"
            )
    
    @pytest.mark.asyncio
    async def test_create_candidate_otp_send_failure(self, candidate_service, valid_candidate_request, mock_db_session):
        """Test candidate creation with OTP send failure."""
        # Mock database queries to return None (no existing candidate)
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = None
        
        # Mock OTP service with send failures
        with patch.object(candidate_service.otp_service, 'create_otp_attempt') as mock_create_otp:
            with patch.object(candidate_service.otp_service, 'send_email_otp') as mock_send_email:
                with patch.object(candidate_service.otp_service, 'send_sms_otp') as mock_send_sms:
                    with patch('modules.identity.service.publish_candidate_created_event') as mock_publish:
                        
                        # Configure mocks - OTP creation succeeds, but sending fails
                        mock_create_otp.side_effect = [
                            ("123456", "email-attempt-id"),
                            ("654321", "phone-attempt-id")
                        ]
                        mock_send_email.return_value = False  # Email send fails
                        mock_send_sms.return_value = True     # SMS send succeeds
                        mock_publish.return_value = None
                        
                        # Execute test
                        result = await candidate_service.create_candidate(
                            candidate_data=valid_candidate_request,
                            correlation_id="test-correlation-id"
                        )
                        
                        # Assertions
                        assert result.candidate.email == valid_candidate_request.email
                        assert result.otp_sent["email"] == False  # Failed
                        assert result.otp_sent["phone"] == True   # Succeeded
                        
                        # Should still create candidate even if OTP sending fails
                        mock_db_session.add.assert_called()
                        mock_db_session.commit.assert_called()
    
    @pytest.mark.asyncio
    async def test_get_candidate_by_id_success(self, candidate_service, mock_db_session):
        """Test successful candidate retrieval by ID."""
        candidate_id = str(uuid.uuid4())
        mock_candidate = Candidate(
            id=candidate_id,
            email="test@example.com",
            first_name="John",
            last_name="Doe",
            phone="4411234567",
            status="active"
        )
        
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = mock_candidate
        
        result = await candidate_service.get_candidate_by_id(candidate_id)
        
        assert result == mock_candidate
        mock_db_session.execute.assert_called()
    
    @pytest.mark.asyncio
    async def test_get_candidate_by_id_not_found(self, candidate_service, mock_db_session):
        """Test candidate retrieval with non-existent ID."""
        candidate_id = str(uuid.uuid4())
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = None
        
        result = await candidate_service.get_candidate_by_id(candidate_id)
        
        assert result is None
        mock_db_session.execute.assert_called()
    
    @pytest.mark.asyncio
    async def test_verify_candidate_otp_success(self, candidate_service):
        """Test successful OTP verification."""
        candidate_id = str(uuid.uuid4())
        otp_type = OTPType.EMAIL
        otp_code = "123456"
        
        # Mock OTP service
        with patch.object(candidate_service.otp_service, 'verify_otp') as mock_verify_otp:
            with patch('modules.identity.service.publish_candidate_verified_event') as mock_publish:
                
                mock_verify_otp.return_value = (True, "OTP verified successfully")
                mock_publish.return_value = None
                
                success, message = await candidate_service.verify_candidate_otp(
                    candidate_id=candidate_id,
                    otp_type=otp_type,
                    otp_code=otp_code
                )
                
                assert success == True
                assert message == "OTP verified successfully"
                mock_verify_otp.assert_called_once_with(
                    candidate_id=candidate_id,
                    otp_type=otp_type,
                    otp_code=otp_code
                )
                mock_publish.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_verify_candidate_otp_failure(self, candidate_service):
        """Test failed OTP verification."""
        candidate_id = str(uuid.uuid4())
        otp_type = OTPType.EMAIL
        otp_code = "wrong-code"
        
        # Mock OTP service
        with patch.object(candidate_service.otp_service, 'verify_otp') as mock_verify_otp:
            
            mock_verify_otp.return_value = (False, "Invalid OTP code")
            
            success, message = await candidate_service.verify_candidate_otp(
                candidate_id=candidate_id,
                otp_type=otp_type,
                otp_code=otp_code
            )
            
            assert success == False
            assert message == "Invalid OTP code"
            mock_verify_otp.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_set_candidate_password_success(self, candidate_service, mock_db_session):
        """Test successful password setting."""
        candidate_id = str(uuid.uuid4())
        password = "SecurePass123!"
        
        # Mock candidate that is fully verified
        mock_candidate = Candidate(
            id=candidate_id,
            email="test@example.com",
            first_name="John",
            last_name="Doe",
            is_email_verified=True,
            is_phone_verified=True,
            hashed_password=None  # No password set yet
        )
        
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = mock_candidate
        
        result = await candidate_service.set_candidate_password(
            candidate_id=candidate_id,
            password=password
        )
        
        assert result == True
        mock_db_session.execute.assert_called()
        mock_db_session.commit.assert_called()
    
    @pytest.mark.asyncio
    async def test_set_candidate_password_not_verified(self, candidate_service, mock_db_session):
        """Test password setting for unverified candidate."""
        candidate_id = str(uuid.uuid4())
        password = "SecurePass123!"
        
        # Mock candidate that is NOT fully verified
        mock_candidate = Candidate(
            id=candidate_id,
            email="test@example.com",
            first_name="John",
            last_name="Doe",
            is_email_verified=True,
            is_phone_verified=False,  # Phone not verified
            hashed_password=None
        )
        
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = mock_candidate
        
        with pytest.raises(ValidationError, match="Candidate must complete email and phone verification first"):
            await candidate_service.set_candidate_password(
                candidate_id=candidate_id,
                password=password
            )
    
    @pytest.mark.asyncio
    async def test_set_candidate_password_already_set(self, candidate_service, mock_db_session):
        """Test password setting when password already exists."""
        candidate_id = str(uuid.uuid4())
        password = "SecurePass123!"
        
        # Mock candidate with password already set
        mock_candidate = Candidate(
            id=candidate_id,
            email="test@example.com",
            first_name="John",
            last_name="Doe",
            is_email_verified=True,
            is_phone_verified=True,
            hashed_password="already-hashed-password"  # Password already set
        )
        
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = mock_candidate
        
        with pytest.raises(ValidationError, match="Password already set for this candidate"):
            await candidate_service.set_candidate_password(
                candidate_id=candidate_id,
                password=password
            )
    
    @pytest.mark.asyncio
    async def test_resend_otp_success(self, candidate_service):
        """Test successful OTP resend."""
        candidate_id = str(uuid.uuid4())
        otp_type = OTPType.EMAIL
        
        # Mock OTP service
        with patch.object(candidate_service.otp_service, 'resend_otp') as mock_resend_otp:
            
            mock_resend_otp.return_value = (True, "OTP sent successfully")
            
            success, message = await candidate_service.resend_otp(
                candidate_id=candidate_id,
                otp_type=otp_type
            )
            
            assert success == True
            assert message == "OTP sent successfully"
            mock_resend_otp.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_list_candidates_with_pagination(self, candidate_service, mock_db_session):
        """Test candidate listing with pagination."""
        # Mock candidate list
        mock_candidates = [
            Candidate(id=f"candidate-{i}", email=f"test{i}@example.com", first_name=f"John{i}", last_name="Doe")
            for i in range(5)
        ]
        
        # Mock database responses
        mock_db_session.execute.side_effect = [
            # First call for candidates
            AsyncMock(scalars=lambda: AsyncMock(all=lambda: mock_candidates)),
            # Second call for count
            AsyncMock(scalar=lambda: 10)
        ]
        
        candidates, total_count = await candidate_service.list_candidates(
            page=1,
            limit=5
        )
        
        assert len(candidates) == 5
        assert total_count == 10
        assert mock_db_session.execute.call_count == 2
    
    @pytest.mark.asyncio
    async def test_get_otp_status(self, candidate_service):
        """Test OTP status retrieval."""
        candidate_id = str(uuid.uuid4())
        
        expected_status = {
            "candidate_id": candidate_id,
            "email_otp_status": "verified",
            "phone_otp_status": "pending",
            "email_verified": True,
            "phone_verified": False,
            "can_set_password": False
        }
        
        # Mock OTP service
        with patch.object(candidate_service.otp_service, 'get_otp_status') as mock_get_status:
            
            mock_get_status.return_value = expected_status
            
            result = await candidate_service.get_otp_status(candidate_id)
            
            assert result == expected_status
            mock_get_status.assert_called_once_with(candidate_id)


class TestCandidateValidation:
    """Test cases for candidate data validation."""
    
    def test_valid_candidate_request(self):
        """Test valid candidate request creation."""
        request = CandidateCreateRequest(
            email="john.doe@example.com",
            first_name="John",
            last_name="Doe",
            phone="4411234567",
            date_of_birth="1990-01-01"
        )
        
        assert request.email == "john.doe@example.com"
        assert request.first_name == "John"
        assert request.phone == "4411234567"
    
    def test_invalid_email(self):
        """Test invalid email validation."""
        with pytest.raises(ValueError):
            CandidateCreateRequest(
                email="invalid-email",
                first_name="John",
                last_name="Doe",
                phone="4411234567"
            )
    
    def test_invalid_phone_number(self):
        """Test invalid phone number validation."""
        with pytest.raises(ValueError, match="Invalid Bermuda phone number format"):
            CandidateCreateRequest(
                email="john@example.com",
                first_name="John",
                last_name="Doe",
                phone="123"  # Invalid format
            )
    
    def test_underage_candidate(self):
        """Test underage candidate validation."""
        # Calculate a date that would make the candidate under 16
        today = datetime.now().date()
        underage_date = today.replace(year=today.year - 15)
        
        with pytest.raises(ValueError, match="Candidate must be at least 16 years old"):
            CandidateCreateRequest(
                email="john@example.com",
                first_name="John",
                last_name="Doe",
                phone="4411234567",
                date_of_birth=underage_date
            )
    
    def test_valid_bermuda_phone_formats(self):
        """Test various valid Bermuda phone formats."""
        valid_formats = [
            "+14414411234",
            "14414411234",
            "4414411234",
            "2921234"  # Local 7-digit format
        ]
        
        for phone in valid_formats:
            request = CandidateCreateRequest(
                email="john@example.com",
                first_name="John",
                last_name="Doe",
                phone=phone
            )
            assert request.phone == phone


class TestPasswordValidation:
    """Test cases for password validation."""
    
    def test_valid_password(self):
        """Test valid password requirements."""
        request = PasswordSetRequest(
            candidate_id="test-id",
            password="SecurePass123!",
            confirm_password="SecurePass123!"
        )
        
        assert request.password == "SecurePass123!"
    
    def test_password_too_short(self):
        """Test password length validation."""
        with pytest.raises(ValueError, match="Password must be at least 8 characters long"):
            PasswordSetRequest(
                candidate_id="test-id",
                password="Short1!",
                confirm_password="Short1!"
            )
    
    def test_password_missing_uppercase(self):
        """Test password uppercase requirement."""
        with pytest.raises(ValueError, match="Password must contain at least one uppercase letter"):
            PasswordSetRequest(
                candidate_id="test-id",
                password="lowercase123!",
                confirm_password="lowercase123!"
            )
    
    def test_password_missing_lowercase(self):
        """Test password lowercase requirement."""
        with pytest.raises(ValueError, match="Password must contain at least one lowercase letter"):
            PasswordSetRequest(
                candidate_id="test-id",
                password="UPPERCASE123!",
                confirm_password="UPPERCASE123!"
            )
    
    def test_password_missing_digit(self):
        """Test password digit requirement."""
        with pytest.raises(ValueError, match="Password must contain at least one digit"):
            PasswordSetRequest(
                candidate_id="test-id",
                password="SecurePass!",
                confirm_password="SecurePass!"
            )
    
    def test_password_missing_special_char(self):
        """Test password special character requirement."""
        with pytest.raises(ValueError, match="Password must contain at least one special character"):
            PasswordSetRequest(
                candidate_id="test-id",
                password="SecurePass123",
                confirm_password="SecurePass123"
            )
    
    def test_passwords_dont_match(self):
        """Test password confirmation mismatch."""
        with pytest.raises(ValueError, match="Passwords do not match"):
            PasswordSetRequest(
                candidate_id="test-id",
                password="SecurePass123!",
                confirm_password="DifferentPass123!"
            )