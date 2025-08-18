"""
Special Admin service client for main backend integration
Communicates with Special Admin microservice on port 8007
"""
import httpx
import logging
import uuid
from typing import Dict, Any, Optional, List
from pydantic import BaseModel
from datetime import datetime

logger = logging.getLogger(__name__)

class SpecialAdminClient:
    """Client for communicating with Special Admin microservice"""
    
    def __init__(self, base_url: str = "http://localhost:8007"):
        self.base_url = base_url.rstrip('/')
        self.timeout = 30.0
        
    async def health_check(self) -> Optional[Dict[str, Any]]:
        """Check if special admin service is healthy"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/health")
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.warning(f"Special admin health check failed: {response.status_code}")
                    return None
        except Exception as e:
            logger.error(f"Special admin health check error: {e}")
            return None
    
    # Special Test Types
    async def get_special_types(self) -> Optional[List[Dict[str, Any]]]:
        """Get all special test types"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/api/v1/special-types")
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(f"Failed to get special types: {response.status_code} - {response.text}")
                    return None
        except Exception as e:
            logger.error(f"Error getting special types: {e}")
            return None
    
    async def create_special_type(self, type_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new special test type"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/v1/special-types",
                    json=type_data,
                    headers={"Content-Type": "application/json"}
                )
                if response.status_code == 201:
                    return {"success": True, "data": response.json()}
                else:
                    return {"success": False, "error": response.text, "status_code": response.status_code}
        except Exception as e:
            logger.error(f"Error creating special type: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_special_type(self, type_id: uuid.UUID) -> Optional[Dict[str, Any]]:
        """Get a specific special test type"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/api/v1/special-types/{type_id}")
                if response.status_code == 200:
                    return {"success": True, "data": response.json()}
                elif response.status_code == 404:
                    return {"success": False, "error": "Special type not found"}
                else:
                    return {"success": False, "error": response.text, "status_code": response.status_code}
        except Exception as e:
            logger.error(f"Error getting special type: {e}")
            return {"success": False, "error": str(e)}
    
    # Certificate Templates
    async def get_templates(self, template_type: Optional[str] = None) -> Optional[List[Dict[str, Any]]]:
        """Get certificate templates"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                params = {"template_type": template_type} if template_type else {}
                response = await client.get(f"{self.base_url}/api/v1/templates", params=params)
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(f"Failed to get templates: {response.status_code} - {response.text}")
                    return None
        except Exception as e:
            logger.error(f"Error getting templates: {e}")
            return None
    
    async def create_template(self, template_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new certificate template"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/v1/templates",
                    json=template_data,
                    headers={"Content-Type": "application/json"}
                )
                if response.status_code == 201:
                    return {"success": True, "data": response.json()}
                else:
                    return {"success": False, "error": response.text, "status_code": response.status_code}
        except Exception as e:
            logger.error(f"Error creating template: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_template_preview(self, template_id: uuid.UUID) -> Optional[Dict[str, Any]]:
        """Get template preview HTML"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/api/v1/templates/{template_id}/preview")
                if response.status_code == 200:
                    return {"success": True, "data": response.json()}
                else:
                    return {"success": False, "error": response.text, "status_code": response.status_code}
        except Exception as e:
            logger.error(f"Error getting template preview: {e}")
            return {"success": False, "error": str(e)}
    
    async def preview_template_content(self, preview_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Generate preview for template content"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/v1/templates/preview",
                    json=preview_data,
                    headers={"Content-Type": "application/json"}
                )
                if response.status_code == 200:
                    return {"success": True, "data": response.json()}
                else:
                    return {"success": False, "error": response.text, "status_code": response.status_code}
        except Exception as e:
            logger.error(f"Error generating preview: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_default_template_config(self) -> Optional[Dict[str, Any]]:
        """Get default template configuration for the designer"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/api/v1/templates/config/default")
                if response.status_code == 200:
                    return {"success": True, "data": response.json()}
                else:
                    return {"success": False, "error": response.text, "status_code": response.status_code}
        except Exception as e:
            logger.error(f"Error getting default template config: {e}")
            return {"success": False, "error": str(e)}
    
    # Question Modules
    async def get_modules(self) -> Optional[List[Dict[str, Any]]]:
        """Get all question modules"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/api/v1/modules")
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(f"Failed to get modules: {response.status_code} - {response.text}")
                    return None
        except Exception as e:
            logger.error(f"Error getting modules: {e}")
            return None
    
    async def create_module(self, module_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new question module"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/v1/modules",
                    json=module_data,
                    headers={"Content-Type": "application/json"}
                )
                if response.status_code == 201:
                    return {"success": True, "data": response.json()}
                else:
                    return {"success": False, "error": response.text, "status_code": response.status_code}
        except Exception as e:
            logger.error(f"Error creating module: {e}")
            return {"success": False, "error": str(e)}
    
    async def upload_questions_csv(self, module_code: str, created_by: str, 
                                  csv_content: str) -> Optional[Dict[str, Any]]:
        """Upload questions from CSV content"""
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:  # Longer timeout for uploads
                upload_data = {
                    "module_code": module_code,
                    "csv_data": csv_content,
                    "created_by": created_by
                }
                response = await client.post(
                    f"{self.base_url}/api/v1/questions/upload-text",
                    json=upload_data,
                    headers={"Content-Type": "application/json"}
                )
                if response.status_code == 200:
                    return {"success": True, "data": response.json()}
                else:
                    return {"success": False, "error": response.text, "status_code": response.status_code}
        except Exception as e:
            logger.error(f"Error uploading questions: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_csv_template(self) -> Optional[Dict[str, Any]]:
        """Get CSV template for question upload"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/api/v1/questions/template")
                if response.status_code == 200:
                    return {"success": True, "data": response.json()}
                else:
                    return {"success": False, "error": response.text, "status_code": response.status_code}
        except Exception as e:
            logger.error(f"Error getting CSV template: {e}")
            return {"success": False, "error": str(e)}
    
    # Service Info
    async def get_config(self) -> Optional[Dict[str, Any]]:
        """Get service configuration"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/config")
                if response.status_code == 200:
                    return response.json()
                else:
                    return None
        except Exception as e:
            logger.error(f"Error getting config: {e}")
            return None
    
    async def get_statistics(self) -> Optional[Dict[str, Any]]:
        """Get service statistics"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/stats")
                if response.status_code == 200:
                    return response.json()
                else:
                    return None
        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return None

# Global client instance
special_admin_client = SpecialAdminClient()

# Pydantic models for request/response validation
class SpecialTypeRequest(BaseModel):
    name: str
    description: Optional[str] = None
    fee: float
    validity_months: int
    required_docs: List[str] = []
    pass_percentage: int = 75
    time_limit_minutes: int = 25
    questions_count: int = 20
    created_by: str

class TemplateRequest(BaseModel):
    name: str
    type: str
    description: Optional[str] = None
    hbs_content: str
    css_content: Optional[str] = None
    json_config: Dict[str, Any] = {}
    created_by: str

class QuestionUploadRequest(BaseModel):
    module_code: str
    created_by: str
    csv_data: str