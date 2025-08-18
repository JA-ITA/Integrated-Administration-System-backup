"""
Test Engine client for main backend integration
Handles communication with Test Engine microservice
"""
import logging
import uuid
from typing import Dict, Any, Optional, List
import httpx
from fastapi import HTTPException

logger = logging.getLogger(__name__)

class TestEngineClient:
    """Client for Test Engine microservice communication"""
    
    def __init__(self, base_url: str = "http://localhost:8005"):
        self.base_url = base_url.rstrip('/')
        self.timeout = 30.0
        
    async def health_check(self) -> Dict[str, Any]:
        """Check Test Engine service health"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/health")
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Test Engine health check failed: {e}")
            return {"status": "error", "detail": str(e)}
    
    async def get_config(self) -> Dict[str, Any]:
        """Get test configuration"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/config")
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Failed to get test config: {e}")
            raise HTTPException(status_code=503, detail="Test Engine service unavailable")
    
    async def start_test(self, driver_record_id: uuid.UUID, module: str) -> Dict[str, Any]:
        """Start a new test"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/v1/tests/start",
                    json={
                        "driver_record_id": str(driver_record_id),
                        "module": module
                    }
                )
                
                if response.status_code == 409:
                    error_detail = response.json().get("detail", "Test conflict")
                    raise HTTPException(status_code=409, detail=error_detail)
                elif response.status_code == 400:
                    error_detail = response.json().get("detail", "Invalid request")
                    raise HTTPException(status_code=400, detail=error_detail)
                
                response.raise_for_status()
                return response.json()
                
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error starting test: {e.response.status_code} - {e.response.text}")
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Failed to start test: {e.response.text}"
            )
        except Exception as e:
            logger.error(f"Failed to start test: {e}")
            raise HTTPException(status_code=503, detail="Test Engine service unavailable")
    
    async def submit_test(self, test_id: uuid.UUID, answers: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Submit test answers"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/v1/tests/{test_id}/submit",
                    json={"answers": answers}
                )
                
                if response.status_code == 404:
                    raise HTTPException(status_code=404, detail="Test not found")
                elif response.status_code == 400:
                    error_detail = response.json().get("detail", "Invalid submission")
                    raise HTTPException(status_code=400, detail=error_detail)
                elif response.status_code == 410:
                    raise HTTPException(status_code=410, detail="Test has expired")
                
                response.raise_for_status()
                return response.json()
                
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error submitting test: {e.response.status_code} - {e.response.text}")
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Failed to submit test: {e.response.text}"
            )
        except Exception as e:
            logger.error(f"Failed to submit test: {e}")
            raise HTTPException(status_code=503, detail="Test Engine service unavailable")
    
    async def get_test_status(self, test_id: uuid.UUID) -> Dict[str, Any]:
        """Get test status and time remaining"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/api/v1/tests/{test_id}/status")
                
                if response.status_code == 404:
                    raise HTTPException(status_code=404, detail="Test not found")
                
                response.raise_for_status()
                return response.json()
                
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error getting test status: {e.response.status_code}")
            raise HTTPException(
                status_code=e.response.status_code,
                detail="Failed to get test status"
            )
        except Exception as e:
            logger.error(f"Failed to get test status: {e}")
            raise HTTPException(status_code=503, detail="Test Engine service unavailable")
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get test statistics"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/stats")
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Failed to get test statistics: {e}")
            return {"error": "Failed to get statistics", "detail": str(e)}

# Global client instance
test_engine_client = TestEngineClient()