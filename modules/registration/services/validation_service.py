"""
Validation service for external dependencies (Calendar, Receipt services)
"""
import logging
import httpx
import uuid
from typing import Dict, Any, List
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

class ValidationService:
    """Service for validating external dependencies"""
    
    def __init__(self):
        self.calendar_service_url = "http://localhost:8002"
        self.receipt_service_url = "http://localhost:8003"
        self.timeout = httpx.Timeout(10.0)
    
    async def validate_external_dependencies(
        self,
        booking_id: uuid.UUID,
        receipt_no: str,
        candidate_id: uuid.UUID
    ) -> Dict[str, Any]:
        """Validate booking and receipt exist and are valid for registration"""
        
        errors = []
        
        # Validate booking
        booking_valid = await self._validate_booking(booking_id, candidate_id)
        if not booking_valid["valid"]:
            errors.extend(booking_valid["errors"])
        
        # Validate receipt
        receipt_valid = await self._validate_receipt(receipt_no)
        if not receipt_valid["valid"]:
            errors.extend(receipt_valid["errors"])
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "booking_info": booking_valid.get("booking_info"),
            "receipt_info": receipt_valid.get("receipt_info")
        }
    
    async def _validate_booking(self, booking_id: uuid.UUID, candidate_id: uuid.UUID) -> Dict[str, Any]:
        """Validate booking exists and belongs to candidate"""
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Get booking details from calendar service
                response = await client.get(f"{self.calendar_service_url}/api/v1/bookings/{booking_id}")
                
                if response.status_code == 404:
                    return {
                        "valid": False,
                        "errors": [f"Booking {booking_id} not found"]
                    }
                elif response.status_code != 200:
                    return {
                        "valid": False,
                        "errors": [f"Failed to validate booking: HTTP {response.status_code}"]
                    }
                
                booking_data = response.json()
                booking_candidate_id = booking_data.get("candidate_id")
                booking_status = booking_data.get("status")
                
                # Validate booking belongs to candidate
                if str(booking_candidate_id) != str(candidate_id):
                    return {
                        "valid": False,
                        "errors": [f"Booking {booking_id} does not belong to candidate {candidate_id}"]
                    }
                
                # Validate booking status (should be confirmed)
                if booking_status not in ["confirmed", "pending"]:
                    return {
                        "valid": False,
                        "errors": [f"Booking {booking_id} has invalid status: {booking_status}"]
                    }
                
                return {
                    "valid": True,
                    "booking_info": booking_data
                }
                
        except httpx.TimeoutException:
            return {
                "valid": False,
                "errors": ["Booking validation timeout - Calendar service unavailable"]
            }
        except Exception as e:
            logger.error(f"Booking validation error: {e}")
            return {
                "valid": False,
                "errors": [f"Booking validation error: {str(e)}"]
            }
    
    async def _validate_receipt(self, receipt_no: str) -> Dict[str, Any]:
        """Validate receipt exists and is unused"""
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Get receipt details from receipt service
                response = await client.get(f"{self.receipt_service_url}/api/v1/receipts/{receipt_no}")
                
                if response.status_code == 404:
                    return {
                        "valid": False,
                        "errors": [f"Receipt {receipt_no} not found"]
                    }
                elif response.status_code != 200:
                    return {
                        "valid": False,
                        "errors": [f"Failed to validate receipt: HTTP {response.status_code}"]
                    }
                
                receipt_data = response.json()
                receipt_info = receipt_data.get("receipt", {})
                used_flag = receipt_info.get("used_flag", False)
                
                # Validate receipt is not already used
                if used_flag:
                    return {
                        "valid": False,
                        "errors": [f"Receipt {receipt_no} has already been used"]
                    }
                
                return {
                    "valid": True,
                    "receipt_info": receipt_info
                }
                
        except httpx.TimeoutException:
            return {
                "valid": False,
                "errors": ["Receipt validation timeout - Receipt service unavailable"]
            }
        except Exception as e:
            logger.error(f"Receipt validation error: {e}")
            return {
                "valid": False,
                "errors": [f"Receipt validation error: {str(e)}"]
            }
    
    async def health_check_dependencies(self) -> Dict[str, Any]:
        """Check health of dependent services"""
        
        services_status = {}
        
        # Check Calendar service
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.calendar_service_url}/health")
                services_status["calendar"] = {
                    "available": response.status_code == 200,
                    "status": response.json() if response.status_code == 200 else None
                }
        except Exception as e:
            services_status["calendar"] = {
                "available": False,
                "error": str(e)
            }
        
        # Check Receipt service
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.receipt_service_url}/health")
                services_status["receipt"] = {
                    "available": response.status_code == 200,
                    "status": response.json() if response.status_code == 200 else None
                }
        except Exception as e:
            services_status["receipt"] = {
                "available": False,
                "error": str(e)
            }
        
        all_available = all(service["available"] for service in services_status.values())
        
        return {
            "all_dependencies_available": all_available,
            "services": services_status
        }