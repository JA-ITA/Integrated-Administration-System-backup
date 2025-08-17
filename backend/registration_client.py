"""
Registration service client for main backend integration
"""
import logging
import httpx
import uuid
from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Pydantic models for client communication
class DocumentUpload(BaseModel):
    """Document upload model for registration"""
    type: str = Field(..., description="Document type: photo, id_proof, mc1, mc2, other")
    filename: str = Field(..., description="Original filename")
    content: str = Field(..., description="Base64 encoded file content")
    mime_type: str = Field(..., description="MIME type of the file")

class RegistrationRequest(BaseModel):
    """Request model for registration creation"""
    booking_id: uuid.UUID
    receipt_no: str
    vehicle_weight_kg: int = Field(..., gt=0)
    vehicle_category: str = Field(..., description="Vehicle category: B, C, PPV, SPECIAL")
    docs: List[DocumentUpload] = Field(..., min_items=2)
    manager_override: Optional[bool] = False
    override_reason: Optional[str] = None
    override_by: Optional[str] = None

class RegistrationResponse(BaseModel):
    """Response model from registration service"""
    success: bool
    registration: Optional[Dict[str, Any]] = None
    message: str
    validation_errors: Optional[List[str]] = None
    driver_record_id: Optional[uuid.UUID] = None

class RegistrationServiceClient:
    """Client for communicating with registration microservice"""
    
    def __init__(self, base_url: str = "http://localhost:8004"):
        self.base_url = base_url.rstrip('/')
        self.timeout = httpx.Timeout(60.0)  # Longer timeout for file uploads
    
    async def health_check(self) -> Optional[Dict[str, Any]]:
        """Check if registration service is healthy"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/health")
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Registration service health check failed: {e}")
            return None
    
    async def create_registration(
        self, 
        registration_data: RegistrationRequest, 
        jwt_token: str
    ) -> Optional[RegistrationResponse]:
        """Create a new registration"""
        try:
            headers = {
                "Authorization": f"Bearer {jwt_token}",
                "Content-Type": "application/json"
            }
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/v1/registrations",
                    json=registration_data.dict(),
                    headers=headers
                )
                
                # Handle different status codes
                if response.status_code in [200, 201]:
                    data = response.json()
                    return RegistrationResponse(**data)
                elif response.status_code == 400:
                    # Validation errors
                    data = response.json()
                    return RegistrationResponse(
                        success=False,
                        message=data.get("message", "Validation failed"),
                        validation_errors=data.get("validation_errors", [str(data)])
                    )
                elif response.status_code == 401:
                    return RegistrationResponse(
                        success=False,
                        message="Authentication failed",
                        validation_errors=["Invalid or expired JWT token"]
                    )
                else:
                    response.raise_for_status()
                    
        except httpx.HTTPStatusError as e:
            logger.error(f"Registration creation HTTP error: {e.response.status_code} - {e.response.text}")
            return RegistrationResponse(
                success=False,
                message=f"HTTP error: {e.response.status_code}",
                validation_errors=[e.response.text]
            )
        except httpx.TimeoutException:
            logger.error("Registration creation timeout")
            return RegistrationResponse(
                success=False,
                message="Request timeout",
                validation_errors=["Service request timed out"]
            )
        except Exception as e:
            logger.error(f"Registration creation failed: {e}")
            return RegistrationResponse(
                success=False,
                message="Service unavailable",
                validation_errors=[str(e)]
            )
    
    async def get_registration(self, registration_id: uuid.UUID) -> Optional[Dict[str, Any]]:
        """Get registration by ID"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/api/v1/registrations/{registration_id}")
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 404:
                    return None
                else:
                    response.raise_for_status()
                    
        except httpx.HTTPStatusError as e:
            logger.error(f"Get registration HTTP error: {e.response.status_code} - {e.response.text}")
            return None
        except Exception as e:
            logger.error(f"Get registration failed: {e}")
            return None
    
    async def get_candidate_registrations(self, candidate_id: uuid.UUID) -> List[Dict[str, Any]]:
        """Get all registrations for a candidate"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/api/v1/candidates/{candidate_id}/registrations"
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    response.raise_for_status()
                    
        except httpx.HTTPStatusError as e:
            logger.error(f"Get candidate registrations HTTP error: {e.response.status_code} - {e.response.text}")
            return []
        except Exception as e:
            logger.error(f"Get candidate registrations failed: {e}")
            return []
    
    async def get_statistics(self) -> Optional[Dict[str, Any]]:
        """Get registration statistics"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/api/v1/registrations")
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Get registration statistics failed: {e}")
            return None
    
    async def check_dependencies(self) -> Optional[Dict[str, Any]]:
        """Check registration service dependencies"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/api/v1/health/dependencies")
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Check registration dependencies failed: {e}")
            return None
    
    async def get_events_status(self) -> Optional[Dict[str, Any]]:
        """Get event publishing status"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/events/status")
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Get registration events status failed: {e}")
            return None

# Global client instance
registration_client = RegistrationServiceClient()