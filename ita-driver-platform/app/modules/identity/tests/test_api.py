"""
API Integration Tests for Identity Module
Tests for the REST API endpoints with realistic request/response flows.
"""

import pytest
import json
import uuid
from datetime import datetime, date
from unittest.mock import AsyncMock, patch, MagicMock

from fastapi.testclient import TestClient
from httpx import AsyncClient

# We'll mock the app for testing
from ..router import router
from ..schemas import CandidateCreateRequest, OTPType


class TestCandidateAPI:
    """Test cases for candidate API endpoints."""
    
    @pytest.fixture
    def test_client(self):
        """Test client for FastAPI."""
        from fastapi import FastAPI
        app = FastAPI()
        app.include_router(router, prefix="/api")
        return TestClient(app)
    
    @pytest.fixture
    def valid_candidate_data(self):
        """Valid candidate creation data."""
        return {
            "email": "john.doe@example.com",
            "first_name": "John", 
            "last_name": "Doe",
            "phone": "4411234567",
            "date_of_birth": "1990-01-01",
            "national_id": "ABC123456",
            "street_address": "123 Main St",
            "city": "Hamilton",
            "postal_code": "HM01",
            "country": "Bermuda"
        }
    
    @pytest.fixture
    def mock_candidate_service(self):
        """Mock candidate service."""
        with patch('modules.identity.router.CandidateService') as mock_service:
            yield mock_service
    
    def test_create_candidate_success(self, test_client, valid_candidate_data, mock_candidate_service):
        """Test successful candidate creation."""
        # Mock service response
        mock_response = {
            "candidate": {
                "id": "test-candidate-id",
                "email": valid_candidate_data["email"],
                "first_name": valid_candidate_data["first_name"],
                "last_name": valid_candidate_data["last_name"],
                "full_name": "John Doe",
                "phone": valid_candidate_data["phone"],
                "status": "pending_verification",
                "is_active": False,
                "is_phone_verified": False,
                "is_email_verified": False,
                "is_identity_verified": False,
                "is_fully_verified": False,
                "profile_completion_percentage": 70,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
                "verified_at": None,
                "preferred_language": "en",
                "timezone": "Atlantic/Bermuda",
                "national_id": "***3456",
                "passport_number": None,
                "street_address": "123 Main St",
                "city": "Hamilton",
                "postal_code": "HM01",
                "country": "Bermuda",
                "date_of_birth": "1990-01-01"
            },
            "otp_sent": {
                "email": True,
                "phone": True
            },
            "message": "Candidate created successfully. Please verify your email and phone number.",
            "next_steps": [
                "Verify your email address using the OTP sent to your email",
                "Verify your phone number using the OTP sent via SMS"
            ]
        }
        
        mock_service_instance = mock_candidate_service.return_value
        mock_service_instance.create_candidate.return_value = type('obj', (object,), mock_response)
        
        # Make request
        response = test_client.post(
            "/api/v1/candidates",
            json=valid_candidate_data,
            headers={"X-Correlation-ID": "test-correlation-id"}
        )
        
        # Assertions
        assert response.status_code == 201
        response_data = response.json()
        
        assert response_data["candidate"]["email"] == valid_candidate_data["email"]
        assert response_data["candidate"]["status"] == "pending_verification"
        assert response_data["otp_sent"]["email"] == True
        assert response_data["otp_sent"]["phone"] == True
        assert len(response_data["next_steps"]) == 2
        
        # Verify service was called
        mock_service_instance.create_candidate.assert_called_once()
    
    def test_create_candidate_invalid_email(self, test_client, valid_candidate_data):
        """Test candidate creation with invalid email."""
        invalid_data = valid_candidate_data.copy()
        invalid_data["email"] = "invalid-email"
        
        response = test_client.post(
            "/api/v1/candidates",
            json=invalid_data
        )
        
        # Should return 422 for validation error
        assert response.status_code == 422
        response_data = response.json()
        assert "detail" in response_data
    
    def test_create_candidate_invalid_phone(self, test_client, valid_candidate_data):
        """Test candidate creation with invalid phone number."""
        invalid_data = valid_candidate_data.copy()
        invalid_data["phone"] = "123"  # Too short and invalid format
        
        response = test_client.post(
            "/api/v1/candidates",
            json=invalid_data
        )
        
        # Should return 422 for validation error
        assert response.status_code == 422
        response_data = response.json()
        assert "detail" in response_data
    
    def test_create_candidate_underage(self, test_client, valid_candidate_data):
        """Test candidate creation with underage date of birth."""
        invalid_data = valid_candidate_data.copy()
        today = date.today()
        underage_date = today.replace(year=today.year - 15)  # 15 years old
        invalid_data["date_of_birth"] = underage_date.isoformat()
        
        response = test_client.post(
            "/api/v1/candidates",
            json=invalid_data
        )
        
        # Should return 422 for validation error
        assert response.status_code == 422
        response_data = response.json()
        assert "detail" in response_data
    
    def test_create_candidate_duplicate_email(self, test_client, valid_candidate_data, mock_candidate_service):
        """Test candidate creation with duplicate email."""
        # Mock service to raise ValidationError
        mock_service_instance = mock_candidate_service.return_value
        mock_service_instance.create_candidate.side_effect = ValueError("Candidate with this email already exists")
        
        response = test_client.post(
            "/api/v1/candidates",
            json=valid_candidate_data
        )
        
        # Should return 400 for business logic error
        assert response.status_code == 400
        response_data = response.json()
        assert response_data["detail"]["error"] == "validation_error"
        assert "already exists" in response_data["detail"]["message"]
    
    def test_get_candidate_success(self, test_client, mock_candidate_service):
        """Test successful candidate retrieval."""
        candidate_id = "test-candidate-id"
        
        # Mock service response
        mock_candidate = type('obj', (object,), {
            "id": candidate_id,
            "email": "john.doe@example.com",
            "first_name": "John",
            "last_name": "Doe",
            "full_name": "John Doe",
            "phone": "4411234567",
            "status": "active",
            "is_active": True,
            "is_phone_verified": True,
            "is_email_verified": True,
            "is_identity_verified": True,
            "is_fully_verified": True,
            "profile_completion_percentage": 100,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "verified_at": datetime.utcnow(),
            "preferred_language": "en",
            "timezone": "Atlantic/Bermuda"
        })
        
        mock_service_instance = mock_candidate_service.return_value
        mock_service_instance.get_candidate_by_id.return_value = mock_candidate
        mock_service_instance._candidate_to_response.return_value = mock_candidate
        
        response = test_client.get(f"/api/v1/candidates/{candidate_id}")
        
        # Assertions
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["id"] == candidate_id
        assert response_data["email"] == "john.doe@example.com"
        assert response_data["status"] == "active"
        assert response_data["is_fully_verified"] == True
    
    def test_get_candidate_not_found(self, test_client, mock_candidate_service):
        """Test candidate retrieval with non-existent ID."""
        candidate_id = "nonexistent-id"
        
        mock_service_instance = mock_candidate_service.return_value
        mock_service_instance.get_candidate_by_id.return_value = None
        
        response = test_client.get(f"/api/v1/candidates/{candidate_id}")
        
        # Should return 404
        assert response.status_code == 404
        response_data = response.json()
        assert response_data["detail"]["error"] == "not_found"
    
    def test_verify_otp_success(self, test_client, mock_candidate_service):
        """Test successful OTP verification."""
        candidate_id = "test-candidate-id"
        otp_data = {
            "candidate_id": candidate_id,
            "otp_type": "email",
            "otp_code": "123456"
        }
        
        # Mock service response
        mock_service_instance = mock_candidate_service.return_value
        mock_service_instance.verify_candidate_otp.return_value = (True, "OTP verified successfully")
        
        # Mock candidate to check if password can be set
        mock_candidate = type('obj', (object,), {
            "is_fully_verified": True,
            "hashed_password": None
        })
        mock_service_instance.get_candidate_by_id.return_value = mock_candidate
        
        response = test_client.post(
            f"/api/v1/candidates/{candidate_id}/verify-otp",
            json=otp_data
        )
        
        # Assertions
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["success"] == True
        assert response_data["message"] == "OTP verified successfully"
        assert response_data["next_step"] == "set_password"
    
    def test_verify_otp_invalid_code(self, test_client, mock_candidate_service):
        """Test OTP verification with invalid code."""
        candidate_id = "test-candidate-id"
        otp_data = {
            "candidate_id": candidate_id,
            "otp_type": "email",
            "otp_code": "wrong-code"
        }
        
        # Mock service response
        mock_service_instance = mock_candidate_service.return_value
        mock_service_instance.verify_candidate_otp.return_value = (False, "Invalid OTP code. 2 attempts remaining")
        
        response = test_client.post(
            f"/api/v1/candidates/{candidate_id}/verify-otp",
            json=otp_data
        )
        
        # Assertions
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["success"] == False
        assert "Invalid OTP code" in response_data["message"]
    
    def test_verify_otp_candidate_id_mismatch(self, test_client):
        """Test OTP verification with mismatched candidate IDs."""
        candidate_id = "test-candidate-id"
        otp_data = {
            "candidate_id": "different-candidate-id",  # Mismatch
            "otp_type": "email",
            "otp_code": "123456"
        }
        
        response = test_client.post(
            f"/api/v1/candidates/{candidate_id}/verify-otp",
            json=otp_data
        )
        
        # Should return 400 for validation error
        assert response.status_code == 400
        response_data = response.json()
        assert response_data["detail"]["error"] == "validation_error"
        assert "mismatch" in response_data["detail"]["message"]
    
    def test_resend_otp_success(self, test_client, mock_candidate_service):
        """Test successful OTP resend."""
        candidate_id = "test-candidate-id"
        resend_data = {
            "candidate_id": candidate_id,
            "otp_type": "email"
        }
        
        # Mock service response
        mock_service_instance = mock_candidate_service.return_value
        mock_service_instance.resend_otp.return_value = (True, "OTP sent successfully to t***t@example.com")
        
        response = test_client.post(
            f"/api/v1/candidates/{candidate_id}/resend-otp",
            json=resend_data
        )
        
        # Assertions
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["success"] == True
        assert "sent successfully" in response_data["message"]
    
    def test_resend_otp_cooldown(self, test_client, mock_candidate_service):
        """Test OTP resend during cooldown period."""
        candidate_id = "test-candidate-id"
        resend_data = {
            "candidate_id": candidate_id,
            "otp_type": "email"
        }
        
        # Mock service response
        mock_service_instance = mock_candidate_service.return_value
        mock_service_instance.resend_otp.return_value = (False, "Please wait 90 seconds before requesting another OTP")
        
        response = test_client.post(
            f"/api/v1/candidates/{candidate_id}/resend-otp",
            json=resend_data
        )
        
        # Should return 400 for business logic error
        assert response.status_code == 400
        response_data = response.json()
        assert response_data["detail"]["error"] == "resend_error"
        assert "wait" in response_data["detail"]["message"]
    
    def test_set_password_success(self, test_client, mock_candidate_service):
        """Test successful password setting."""
        candidate_id = "test-candidate-id"
        password_data = {
            "candidate_id": candidate_id,
            "password": "SecurePass123!",
            "confirm_password": "SecurePass123!"
        }
        
        # Mock service response
        mock_service_instance = mock_candidate_service.return_value
        mock_service_instance.set_candidate_password.return_value = True
        
        response = test_client.post(
            f"/api/v1/candidates/{candidate_id}/set-password",
            json=password_data
        )
        
        # Assertions
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["success"] == True
        assert response_data["status"] == "active"
        assert "Password set successfully" in response_data["message"]
    
    def test_set_password_validation_error(self, test_client, mock_candidate_service):
        """Test password setting with validation error."""
        candidate_id = "test-candidate-id"
        password_data = {
            "candidate_id": candidate_id,
            "password": "weak",  # Too weak
            "confirm_password": "weak"
        }
        
        # Should fail validation before reaching service
        response = test_client.post(
            f"/api/v1/candidates/{candidate_id}/set-password",
            json=password_data
        )
        
        # Should return 422 for validation error
        assert response.status_code == 422
        response_data = response.json()
        assert "detail" in response_data
    
    def test_set_password_not_verified(self, test_client, mock_candidate_service):
        """Test password setting for unverified candidate."""
        candidate_id = "test-candidate-id"
        password_data = {
            "candidate_id": candidate_id,
            "password": "SecurePass123!",
            "confirm_password": "SecurePass123!"
        }
        
        # Mock service to raise ValidationError
        mock_service_instance = mock_candidate_service.return_value
        mock_service_instance.set_candidate_password.side_effect = ValueError("Candidate must complete email and phone verification first")
        
        response = test_client.post(
            f"/api/v1/candidates/{candidate_id}/set-password",
            json=password_data
        )
        
        # Should return 400 for business logic error
        assert response.status_code == 400
        response_data = response.json()
        assert response_data["detail"]["error"] == "validation_error"
        assert "verification" in response_data["detail"]["message"]
    
    def test_get_otp_status_success(self, test_client, mock_candidate_service):
        """Test successful OTP status retrieval."""
        candidate_id = "test-candidate-id"
        
        # Mock service response
        mock_status = {
            "candidate_id": candidate_id,
            "email_otp_status": "verified",
            "phone_otp_status": "pending",
            "email_verified": True,
            "phone_verified": False,
            "can_set_password": False
        }
        
        mock_service_instance = mock_candidate_service.return_value
        mock_service_instance.get_otp_status.return_value = mock_status
        
        response = test_client.get(f"/api/v1/candidates/{candidate_id}/otp-status")
        
        # Assertions
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["candidate_id"] == candidate_id
        assert response_data["email_otp_status"] == "verified"
        assert response_data["phone_otp_status"] == "pending"
        assert response_data["email_verified"] == True
        assert response_data["phone_verified"] == False
        assert response_data["can_set_password"] == False
    
    def test_health_check(self, test_client):
        """Test identity module health check."""
        response = test_client.get("/api/v1/health")
        
        # Assertions
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["module"] == "Identity & Profile Management"
        assert response_data["status"] == "healthy"
        assert "features" in response_data
        assert "endpoints" in response_data
    
    def test_correlation_id_header(self, test_client, valid_candidate_data, mock_candidate_service):
        """Test that correlation ID is properly handled."""
        correlation_id = "test-correlation-123"
        
        # Mock service response
        mock_response = {
            "candidate": {"id": "test-id", "email": valid_candidate_data["email"]},
            "otp_sent": {"email": True, "phone": True},
            "message": "Success",
            "next_steps": []
        }
        
        mock_service_instance = mock_candidate_service.return_value
        mock_service_instance.create_candidate.return_value = type('obj', (object,), mock_response)
        
        response = test_client.post(
            "/api/v1/candidates",
            json=valid_candidate_data,
            headers={"X-Correlation-ID": correlation_id}
        )
        
        # Service should be called with correlation ID
        call_args = mock_service_instance.create_candidate.call_args
        assert call_args.kwargs["correlation_id"] == correlation_id
    
    def test_missing_correlation_id_generates_one(self, test_client, valid_candidate_data, mock_candidate_service):
        """Test that missing correlation ID generates a new one."""
        mock_response = {
            "candidate": {"id": "test-id", "email": valid_candidate_data["email"]},
            "otp_sent": {"email": True, "phone": True},
            "message": "Success",
            "next_steps": []
        }
        
        mock_service_instance = mock_candidate_service.return_value
        mock_service_instance.create_candidate.return_value = type('obj', (object,), mock_response)
        
        response = test_client.post(
            "/api/v1/candidates",
            json=valid_candidate_data
            # No X-Correlation-ID header
        )
        
        # Service should be called with generated correlation ID
        call_args = mock_service_instance.create_candidate.call_args
        correlation_id = call_args.kwargs["correlation_id"]
        assert correlation_id is not None
        assert len(correlation_id) == 36  # UUID length