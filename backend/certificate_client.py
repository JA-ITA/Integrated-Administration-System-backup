"""
Certificate service client for main backend integration
"""
import os
import logging
import uuid
from typing import Dict, Any, Optional
import httpx
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

class CertificateClient:
    """Client for communicating with Certificate microservice"""
    
    def __init__(self):
        self.service_url = os.getenv("CERTIFICATE_SERVICE_URL", "http://localhost:8006")
        self.timeout = httpx.Timeout(30.0, connect=5.0)
        
    async def health_check(self) -> Dict[str, Any]:
        """Check certificate service health"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.service_url}/health")
                
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(f"Certificate service health check failed: {response.status_code}")
                    return {"status": "unhealthy", "error": f"HTTP {response.status_code}"}
                    
        except Exception as e:
            logger.error(f"Certificate service health check error: {e}")
            return {"status": "unreachable", "error": str(e)}
    
    async def generate_certificate(self, driver_record_id: uuid.UUID) -> Dict[str, Any]:
        """Generate a new certificate for driver record"""
        try:
            request_data = {
                "driver_record_id": str(driver_record_id)
            }
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.service_url}/api/v1/certificates/generate",
                    json=request_data
                )
                
                if response.status_code == 200:
                    result = response.json()
                    logger.info(f"Certificate generated successfully for driver_record_id: {driver_record_id}")
                    return {
                        "success": True,
                        "data": result
                    }
                else:
                    error_detail = response.json().get("detail", "Unknown error")
                    logger.error(f"Certificate generation failed: {response.status_code} - {error_detail}")
                    return {
                        "success": False,
                        "error": error_detail,
                        "status_code": response.status_code
                    }
                    
        except Exception as e:
            logger.error(f"Certificate generation request failed: {e}")
            return {
                "success": False,
                "error": f"Service communication error: {str(e)}"
            }
    
    async def download_certificate_by_driver_record(self, driver_record_id: uuid.UUID) -> Dict[str, Any]:
        """Get download URL for certificate by driver record ID"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=False) as client:
                response = await client.get(
                    f"{self.service_url}/api/v1/certificates/{driver_record_id}/download"
                )
                
                if response.status_code == 302:
                    # Successfully got redirect to pre-signed URL
                    download_url = response.headers.get("Location")
                    logger.info(f"Certificate download URL obtained for driver_record_id: {driver_record_id}")
                    return {
                        "success": True,
                        "download_url": download_url
                    }
                elif response.status_code == 404:
                    logger.warning(f"No certificate found for driver_record_id: {driver_record_id}")
                    return {
                        "success": False,
                        "error": "No certificate found for this driver record",
                        "status_code": 404
                    }
                elif response.status_code == 410:
                    logger.warning(f"Certificate expired/invalid for driver_record_id: {driver_record_id}")
                    return {
                        "success": False,
                        "error": "Certificate is expired or invalid",
                        "status_code": 410
                    }
                else:
                    error_detail = response.json().get("detail", "Unknown error")
                    logger.error(f"Certificate download failed: {response.status_code} - {error_detail}")
                    return {
                        "success": False,
                        "error": error_detail,
                        "status_code": response.status_code
                    }
                    
        except Exception as e:
            logger.error(f"Certificate download request failed: {e}")
            return {
                "success": False,
                "error": f"Service communication error: {str(e)}"
            }
    
    async def download_certificate_by_id(self, certificate_id: uuid.UUID) -> Dict[str, Any]:
        """Get download URL for certificate by certificate ID"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=False) as client:
                response = await client.get(
                    f"{self.service_url}/api/v1/certificates/by-id/{certificate_id}/download"
                )
                
                if response.status_code == 302:
                    # Successfully got redirect to pre-signed URL
                    download_url = response.headers.get("Location")
                    logger.info(f"Certificate download URL obtained for certificate_id: {certificate_id}")
                    return {
                        "success": True,
                        "download_url": download_url
                    }
                elif response.status_code == 404:
                    logger.warning(f"Certificate not found: {certificate_id}")
                    return {
                        "success": False,
                        "error": "Certificate not found",
                        "status_code": 404
                    }
                elif response.status_code == 410:
                    logger.warning(f"Certificate expired/invalid: {certificate_id}")
                    return {
                        "success": False,
                        "error": "Certificate is expired or invalid",
                        "status_code": 410
                    }
                else:
                    error_detail = response.json().get("detail", "Unknown error")
                    logger.error(f"Certificate download failed: {response.status_code} - {error_detail}")
                    return {
                        "success": False,
                        "error": error_detail,
                        "status_code": response.status_code
                    }
                    
        except Exception as e:
            logger.error(f"Certificate download request failed: {e}")
            return {
                "success": False,
                "error": f"Service communication error: {str(e)}"
            }
    
    async def verify_certificate(self, verification_token: str) -> Dict[str, Any]:
        """Verify certificate authenticity using verification token"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.service_url}/api/v1/certificates/verify/{verification_token}"
                )
                
                if response.status_code == 200:
                    result = response.json()
                    logger.info(f"Certificate verification completed for token: {verification_token}")
                    return {
                        "success": True,
                        "data": result
                    }
                else:
                    error_detail = response.json().get("detail", "Unknown error")
                    logger.error(f"Certificate verification failed: {response.status_code} - {error_detail}")
                    return {
                        "success": False,
                        "error": error_detail,
                        "status_code": response.status_code
                    }
                    
        except Exception as e:
            logger.error(f"Certificate verification request failed: {e}")
            return {
                "success": False,
                "error": f"Service communication error: {str(e)}"
            }
    
    async def get_certificate_status(self, certificate_id: uuid.UUID) -> Dict[str, Any]:
        """Get certificate status and metadata"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.service_url}/api/v1/certificates/{certificate_id}/status"
                )
                
                if response.status_code == 200:
                    result = response.json()
                    logger.info(f"Certificate status retrieved for: {certificate_id}")
                    return {
                        "success": True,
                        "data": result
                    }
                elif response.status_code == 404:
                    return {
                        "success": False,
                        "error": "Certificate not found",
                        "status_code": 404
                    }
                else:
                    error_detail = response.json().get("detail", "Unknown error")
                    logger.error(f"Certificate status request failed: {response.status_code} - {error_detail}")
                    return {
                        "success": False,
                        "error": error_detail,
                        "status_code": response.status_code
                    }
                    
        except Exception as e:
            logger.error(f"Certificate status request failed: {e}")
            return {
                "success": False,
                "error": f"Service communication error: {str(e)}"
            }
    
    async def get_driver_certificates(self, driver_record_id: uuid.UUID) -> Dict[str, Any]:
        """Get all certificates for a driver record"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.service_url}/api/v1/certificates/driver/{driver_record_id}"
                )
                
                if response.status_code == 200:
                    result = response.json()
                    logger.info(f"Driver certificates retrieved for: {driver_record_id}")
                    return {
                        "success": True,
                        "data": result
                    }
                else:
                    error_detail = response.json().get("detail", "Unknown error")
                    logger.error(f"Driver certificates request failed: {response.status_code} - {error_detail}")
                    return {
                        "success": False,
                        "error": error_detail,
                        "status_code": response.status_code
                    }
                    
        except Exception as e:
            logger.error(f"Driver certificates request failed: {e}")
            return {
                "success": False,
                "error": f"Service communication error: {str(e)}"
            }

# Global client instance
certificate_client = CertificateClient()