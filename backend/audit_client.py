"""
Audit Service Client for Main Backend Integration
"""
import httpx
import logging
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from datetime import datetime

logger = logging.getLogger(__name__)

class AuditHealthResponse(BaseModel):
    status: str
    service: str
    version: str
    database: Dict[str, Any]
    events: Dict[str, Any]

class OverrideRequest(BaseModel):
    resource_type: str
    resource_id: str
    new_status: str
    reason: str
    old_status: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class OverrideResponse(BaseModel):
    success: bool
    audit_id: Optional[str] = None
    message: str
    resource_type: str
    resource_id: str
    new_status: str

class AuditLogResponse(BaseModel):
    id: str
    actor_id: str
    actor_role: str
    action: str
    resource_type: str
    resource_id: str
    old_val: Optional[Dict[str, Any]]
    new_val: Optional[Dict[str, Any]]
    reason: str
    created_at: datetime

class AuditClient:
    """Client for interacting with Audit microservice"""
    
    def __init__(self, base_url: str = "http://localhost:8008"):
        self.base_url = base_url
        self.timeout = httpx.Timeout(30.0)
    
    async def health_check(self) -> Optional[AuditHealthResponse]:
        """Check audit service health"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/health")
                
                if response.status_code == 200:
                    data = response.json()
                    return AuditHealthResponse(**data)
                else:
                    logger.warning(f"Audit service health check failed: {response.status_code}")
                    return None
                    
        except httpx.TimeoutException:
            logger.warning("Audit service health check timeout")
            return None
        except Exception as e:
            logger.error(f"Error during audit service health check: {e}")
            return None
    
    async def create_override(
        self, 
        override_data: OverrideRequest, 
        rd_token: str
    ) -> Optional[OverrideResponse]:
        """Create an override with RD authentication"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                headers = {
                    "Authorization": f"Bearer {rd_token}",
                    "Content-Type": "application/json"
                }
                
                response = await client.post(
                    f"{self.base_url}/api/v1/overrides/",
                    json=override_data.dict(),
                    headers=headers
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return OverrideResponse(**data)
                else:
                    logger.warning(f"Override creation failed: {response.status_code} - {response.text}")
                    return None
                    
        except httpx.TimeoutException:
            logger.warning("Override creation timeout")
            return None
        except Exception as e:
            logger.error(f"Error creating override: {e}")
            return None
    
    async def get_resource_audit_history(
        self, 
        resource_type: str, 
        resource_id: str, 
        rd_token: str
    ) -> List[AuditLogResponse]:
        """Get audit history for a specific resource"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                headers = {"Authorization": f"Bearer {rd_token}"}
                
                response = await client.get(
                    f"{self.base_url}/api/v1/overrides/audit/{resource_type}/{resource_id}",
                    headers=headers
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return [AuditLogResponse(**log) for log in data]
                else:
                    logger.warning(f"Failed to get audit history: {response.status_code}")
                    return []
                    
        except httpx.TimeoutException:
            logger.warning("Get audit history timeout")
            return []
        except Exception as e:
            logger.error(f"Error getting audit history: {e}")
            return []
    
    async def get_actor_audit_history(
        self, 
        actor_id: str, 
        rd_token: str,
        action: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[AuditLogResponse]:
        """Get audit history for a specific actor"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                headers = {"Authorization": f"Bearer {rd_token}"}
                
                params = {
                    "limit": limit,
                    "offset": offset
                }
                if action:
                    params["action"] = action
                
                response = await client.get(
                    f"{self.base_url}/api/v1/overrides/audit/actor/{actor_id}",
                    headers=headers,
                    params=params
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return [AuditLogResponse(**log) for log in data]
                else:
                    logger.warning(f"Failed to get actor audit history: {response.status_code}")
                    return []
                    
        except httpx.TimeoutException:
            logger.warning("Get actor audit history timeout")
            return []
        except Exception as e:
            logger.error(f"Error getting actor audit history: {e}")
            return []
    
    async def get_audit_logs(
        self, 
        rd_token: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        actor_id: Optional[str] = None,
        action: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[AuditLogResponse]:
        """Get audit logs with filters"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                headers = {"Authorization": f"Bearer {rd_token}"}
                
                params = {
                    "limit": limit,
                    "offset": offset
                }
                
                if resource_type:
                    params["resource_type"] = resource_type
                if resource_id:
                    params["resource_id"] = resource_id
                if actor_id:
                    params["actor_id"] = actor_id
                if action:
                    params["action"] = action
                
                response = await client.get(
                    f"{self.base_url}/api/v1/audit-logs/",
                    headers=headers,
                    params=params
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return [AuditLogResponse(**log) for log in data]
                else:
                    logger.warning(f"Failed to get audit logs: {response.status_code}")
                    return []
                    
        except httpx.TimeoutException:
            logger.warning("Get audit logs timeout")
            return []
        except Exception as e:
            logger.error(f"Error getting audit logs: {e}")
            return []
    
    async def get_audit_statistics(self, rd_token: str) -> Optional[Dict[str, Any]]:
        """Get audit statistics"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                headers = {"Authorization": f"Bearer {rd_token}"}
                
                response = await client.get(
                    f"{self.base_url}/api/v1/audit-logs/statistics",
                    headers=headers
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.warning(f"Failed to get audit statistics: {response.status_code}")
                    return None
                    
        except httpx.TimeoutException:
            logger.warning("Get audit statistics timeout")
            return None
        except Exception as e:
            logger.error(f"Error getting audit statistics: {e}")
            return None

# Global client instance
audit_client = AuditClient()