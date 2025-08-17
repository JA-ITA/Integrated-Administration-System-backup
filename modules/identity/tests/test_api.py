"""
Tests for ITADIAS Identity Microservice API endpoints
"""
import pytest
import uuid
from fastapi import status

class TestHealthEndpoint:
    """Test health check endpoint"""
    
    def test_health_check(self, test_client):
        """Test health endpoint"""
        response = test_client.get("/health")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "ITADIAS Identity Microservice"
        assert data["version"] == "1.0.0"

class TestCandidateEndpoints:
    """Test candidate API endpoints"""
    
    @pytest.mark.asyncio
    async def test_create_candidate_success(self, async_test_client, override_dependencies, sample_candidate_data):
        """Test successful candidate creation"""
        response = await async_test_client.post("/api/v1/candidates", json=sample_candidate_data)
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        
        assert "candidate" in data
        assert "otp_sent" in data
        assert "otp_channels" in data
        assert "message" in data
        
        candidate = data["candidate"]
        assert candidate["email"] == sample_candidate_data["email"]
        assert candidate["phone"] == sample_candidate_data["phone"]
        assert candidate["first_name"] == sample_candidate_data["first_name"]
        assert candidate["last_name"] == sample_candidate_data["last_name"]
        assert candidate["is_verified"] is False
        assert candidate["is_active"] is True
        assert "id" in candidate
    
    @pytest.mark.asyncio
    async def test_create_candidate_duplicate_email(self, async_test_client, override_dependencies, sample_candidate_data):
        """Test creating candidate with duplicate email"""
        # Create first candidate
        response1 = await async_test_client.post("/api/v1/candidates", json=sample_candidate_data)
        assert response1.status_code == status.HTTP_201_CREATED
        
        # Try to create second candidate with same email
        response2 = await async_test_client.post("/api/v1/candidates", json=sample_candidate_data)
        assert response2.status_code == status.HTTP_409_CONFLICT
        
        data = response2.json()
        assert "already exists" in data["detail"]
    
    @pytest.mark.asyncio
    async def test_create_candidate_invalid_email(self, async_test_client, override_dependencies):
        """Test creating candidate with invalid email"""
        invalid_data = {
            "email": "invalid-email",
            "first_name": "John",
            "last_name": "Doe"
        }
        
        response = await async_test_client.post("/api/v1/candidates", json=invalid_data)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    @pytest.mark.asyncio
    async def test_create_candidate_without_otp(self, async_test_client, override_dependencies, sample_candidate_data):
        """Test creating candidate without sending OTP"""
        data = {**sample_candidate_data, "send_otp": False}
        
        response = await async_test_client.post("/api/v1/candidates", json=data)
        
        assert response.status_code == status.HTTP_201_CREATED
        response_data = response.json()
        assert response_data["otp_sent"] is False
        assert response_data["otp_channels"] == []
    
    @pytest.mark.asyncio
    async def test_get_candidate_success(self, async_test_client, override_dependencies, sample_candidate_data):
        """Test successful candidate retrieval"""
        # Create candidate first
        create_response = await async_test_client.post("/api/v1/candidates", json=sample_candidate_data)
        assert create_response.status_code == status.HTTP_201_CREATED
        created_candidate = create_response.json()["candidate"]
        
        # Get candidate
        candidate_id = created_candidate["id"]
        response = await async_test_client.get(f"/api/v1/candidates/{candidate_id}")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["id"] == candidate_id
        assert data["email"] == sample_candidate_data["email"]
        assert data["first_name"] == sample_candidate_data["first_name"]
        assert data["last_name"] == sample_candidate_data["last_name"]
    
    @pytest.mark.asyncio
    async def test_get_candidate_not_found(self, async_test_client, override_dependencies):
        """Test getting non-existent candidate"""
        fake_id = str(uuid.uuid4())
        response = await async_test_client.get(f"/api/v1/candidates/{fake_id}")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert "not found" in data["detail"]
    
    @pytest.mark.asyncio
    async def test_get_candidate_invalid_uuid(self, async_test_client, override_dependencies):
        """Test getting candidate with invalid UUID"""
        response = await async_test_client.get("/api/v1/candidates/invalid-uuid")
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    @pytest.mark.asyncio
    async def test_list_candidates(self, async_test_client, override_dependencies):
        """Test listing candidates"""
        # Create multiple candidates
        candidates_data = [
            {
                "email": f"test{i}@example.com",
                "first_name": f"John{i}",
                "last_name": f"Doe{i}",
                "send_otp": False
            }
            for i in range(3)
        ]
        
        for data in candidates_data:
            response = await async_test_client.post("/api/v1/candidates", json=data)
            assert response.status_code == status.HTTP_201_CREATED
        
        # List candidates
        response = await async_test_client.get("/api/v1/candidates")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert isinstance(data, list)
        assert len(data) == 3
        
        # Check pagination
        response_limited = await async_test_client.get("/api/v1/candidates?limit=2")
        assert response_limited.status_code == status.HTTP_200_OK
        limited_data = response_limited.json()
        assert len(limited_data) == 2

class TestRootEndpoint:
    """Test root endpoint"""
    
    def test_root_endpoint(self, test_client):
        """Test root endpoint"""
        response = test_client.get("/")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["message"] == "ITADIAS Identity Microservice"
        assert data["version"] == "1.0.0"
        assert data["docs"] == "/docs"