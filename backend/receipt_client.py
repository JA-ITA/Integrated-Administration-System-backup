"""
Receipt service client for main backend integration
"""
import logging
import httpx
from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Pydantic models for client communication
class ReceiptValidationRequest(BaseModel):
    """Request model for receipt validation"""
    receipt_no: str = Field(..., min_length=8, max_length=20)
    issue_date: datetime
    location: str
    amount: float = Field(..., ge=0)

class ReceiptValidationResponse(BaseModel):
    """Response model from receipt validation"""
    success: bool
    receipt_no: str
    message: str
    receipt: Optional[Dict[str, Any]] = None
    validation_timestamp: datetime

class ReceiptServiceClient:
    """Client for communicating with receipt microservice"""
    
    def __init__(self, base_url: str = "http://localhost:8003"):
        self.base_url = base_url.rstrip('/')
        self.timeout = httpx.Timeout(30.0)
    
    async def health_check(self) -> Optional[Dict[str, Any]]:
        """Check if receipt service is healthy"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/health")
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Receipt service health check failed: {e}")
            return None
    
    async def validate_receipt(self, validation_data: ReceiptValidationRequest) -> Optional[ReceiptValidationResponse]:
        """Validate a receipt via receipt service"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/v1/receipts/validate",
                    json=validation_data.dict()
                )
                
                # Handle different status codes
                if response.status_code in [200, 409]:
                    data = response.json()
                    return ReceiptValidationResponse(**data)
                else:
                    response.raise_for_status()
                    
        except httpx.HTTPStatusError as e:
            logger.error(f"Receipt validation HTTP error: {e.response.status_code} - {e.response.text}")
            return None
        except Exception as e:
            logger.error(f"Receipt validation failed: {e}")
            return None
    
    async def get_receipt(self, receipt_no: str) -> Optional[Dict[str, Any]]:
        """Get receipt details by receipt number"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/api/v1/receipts/{receipt_no}")
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 404:
                    return None
                else:
                    response.raise_for_status()
                    
        except httpx.HTTPStatusError as e:
            logger.error(f"Get receipt HTTP error: {e.response.status_code} - {e.response.text}")
            return None
        except Exception as e:
            logger.error(f"Get receipt failed: {e}")
            return None
    
    async def get_statistics(self) -> Optional[Dict[str, Any]]:
        """Get receipt validation statistics"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/api/v1/receipts")
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Get receipt statistics failed: {e}")
            return None

# Global client instance
receipt_client = ReceiptServiceClient()