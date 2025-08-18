"""
Certificate service for generating PDF certificates
"""
import json
import logging
import asyncio
import uuid
import qrcode
import io
import httpx
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Tuple
from PIL import Image

from config import config
from models import CertificateMetadata, generate_verification_token, generate_qr_code_url, calculate_expiry_date

logger = logging.getLogger(__name__)

class CertificateService:
    """Service for generating PDF certificates using Handlebars templates"""
    
    def __init__(self):
        self.pdf_service_url = config.certificate.pdf_service_url
        self.qr_base_url = config.certificate.qr_base_url
        
    async def generate_certificate_pdf(
        self,
        driver_record_id: uuid.UUID,
        certificate_data: Dict[str, Any]
    ) -> Tuple[bytes, Dict[str, Any]]:
        """Generate PDF certificate and return bytes with metadata"""
        
        try:
            # Extract data from certificate_data or fetch from other services
            certificate_metadata = await self._prepare_certificate_metadata(
                driver_record_id, certificate_data
            )
            
            # Generate verification token and QR code
            verification_token = generate_verification_token()
            qr_code_url = generate_qr_code_url(verification_token, self.qr_base_url)
            
            # Generate QR code image
            qr_code_image = self._generate_qr_code_image(qr_code_url)
            
            # Prepare template context
            template_context = await self._prepare_template_context(
                certificate_metadata, verification_token, qr_code_image
            )
            
            # Determine template based on certificate type
            template_name = self._get_template_name(certificate_metadata.licence_endorsement)
            
            # Generate PDF via PDF service
            pdf_bytes = await self._generate_pdf_from_template(
                template_name, template_context
            )
            
            # Prepare metadata for database storage
            db_metadata = {
                "template_used": template_name,
                "verification_token": verification_token,
                "qr_code_url": qr_code_url,
                "generation_timestamp": datetime.now(timezone.utc).isoformat(),
                "certificate_data": certificate_metadata.dict()
            }
            
            logger.info(f"Certificate PDF generated for driver_record_id: {driver_record_id}")
            
            return pdf_bytes, db_metadata
            
        except Exception as e:
            logger.error(f"Failed to generate certificate PDF: {e}")
            raise
    
    async def _prepare_certificate_metadata(
        self, 
        driver_record_id: uuid.UUID, 
        certificate_data: Dict[str, Any]
    ) -> CertificateMetadata:
        """Prepare certificate metadata from available data"""
        
        # TODO: In a real implementation, this would fetch data from:
        # - Registration service (for candidate details)
        # - Test engine service (for test results) 
        # - Calendar service (for service hub information)
        
        # For now, use provided data or defaults
        return CertificateMetadata(
            candidate_full_name=certificate_data.get("candidate_name", "John Doe"),
            driver_record_number=str(driver_record_id),
            licence_endorsement=certificate_data.get("licence_endorsement", "Class B Driver Licence"),
            issue_date=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            expiry_date=certificate_data.get("expiry_date"),
            certificate_id=str(uuid.uuid4()),
            service_hub_name=certificate_data.get("service_hub", "Central Testing Hub"),
            test_score=certificate_data.get("test_score"),
            test_date=certificate_data.get("test_date"),
            issuing_authority="Island Traffic Authority"
        )
    
    def _generate_qr_code_image(self, qr_url: str) -> str:
        """Generate QR code image and return as base64 string"""
        try:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(qr_url)
            qr.make(fit=True)
            
            # Create QR code image
            qr_image = qr.make_image(fill_color="black", back_color="white")
            
            # Convert to base64 string
            img_buffer = io.BytesIO()
            qr_image.save(img_buffer, format='PNG')
            img_buffer.seek(0)
            
            import base64
            qr_base64 = base64.b64encode(img_buffer.getvalue()).decode()
            
            return f"data:image/png;base64,{qr_base64}"
            
        except Exception as e:
            logger.error(f"Failed to generate QR code: {e}")
            # Return empty string if QR generation fails
            return ""
    
    async def _prepare_template_context(
        self,
        metadata: CertificateMetadata,
        verification_token: str,
        qr_code_image: str
    ) -> Dict[str, Any]:
        """Prepare context data for Handlebars template"""
        
        context = {
            # Certificate content
            "candidateName": metadata.candidate_full_name,
            "driverRecordNumber": metadata.driver_record_number,
            "licenceEndorsement": metadata.licence_endorsement,
            "issueDate": metadata.issue_date,
            "expiryDate": metadata.expiry_date,
            "certificateId": metadata.certificate_id,
            "serviceHub": metadata.service_hub_name,
            "issuingAuthority": metadata.issuing_authority,
            
            # QR Code and verification
            "qrCodeImage": qr_code_image,
            "verificationToken": verification_token,
            "verificationUrl": f"{self.qr_base_url}/{verification_token}",
            
            # Branding and styling
            "brandColor": config.certificate.brand_color,
            "logoPath": config.certificate.logo_path,
            "fontFamily": config.certificate.font_family,
            
            # Optional test information
            "testScore": metadata.test_score,
            "testDate": metadata.test_date,
            
            # Formatting helpers
            "currentYear": datetime.now().year,
        }
        
        return context
    
    def _get_template_name(self, licence_endorsement: str) -> str:
        """Determine template name based on licence/endorsement type"""
        
        licence_lower = licence_endorsement.lower()
        
        if "class" in licence_lower and ("a" in licence_lower or "b" in licence_lower or "c" in licence_lower):
            return "driver-licence-certificate"
        elif any(keyword in licence_lower for keyword in ["hazmat", "endorsement", "ppv"]):
            return "endorsement-certificate"  
        else:
            # Default template
            return "driver-licence-certificate"
    
    async def _generate_pdf_from_template(
        self,
        template_name: str,
        context: Dict[str, Any]
    ) -> bytes:
        """Generate PDF using external PDF service"""
        
        try:
            request_data = {
                "templateName": template_name,
                "context": context,
                "options": {
                    "returnFormat": "base64",
                    "pageFormat": "A4",
                    "orientation": "portrait",
                    "quality": "high"
                }
            }
            
            timeout = httpx.Timeout(30.0, connect=5.0)
            
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    f"{self.pdf_service_url}/generate-pdf",
                    json=request_data
                )
                
                if response.status_code != 200:
                    error_detail = response.json().get("error", "Unknown error")
                    raise RuntimeError(f"PDF service error: {error_detail}")
                
                pdf_data = response.json()
                
                if not pdf_data.get("success"):
                    raise RuntimeError("PDF generation failed")
                
                # Decode base64 PDF data
                import base64
                pdf_base64 = pdf_data["data"]["pdf"]
                pdf_bytes = base64.b64decode(pdf_base64)
                
                logger.info(f"PDF generated successfully using template: {template_name}")
                return pdf_bytes
                
        except Exception as e:
            logger.error(f"Failed to generate PDF: {e}")
            raise
    
    async def fetch_certificate_data(self, driver_record_id: uuid.UUID) -> Dict[str, Any]:
        """Fetch certificate data from other microservices"""
        
        # TODO: Implement actual service calls
        # This is a placeholder that would make HTTP calls to:
        # - Registration service: Get candidate details
        # - Test Engine service: Get test results
        # - Calendar service: Get service hub information
        
        try:
            certificate_data = {
                "candidate_name": "John Doe",  # From registration service
                "licence_endorsement": "Class B Driver Licence",  # From test results
                "service_hub": "Central Testing Hub",  # From calendar/booking
                "test_score": 85.0,  # From test engine
                "test_date": "2024-01-15"  # From test engine
            }
            
            logger.info(f"Fetched certificate data for driver_record_id: {driver_record_id}")
            return certificate_data
            
        except Exception as e:
            logger.error(f"Failed to fetch certificate data: {e}")
            # Return minimal data to allow certificate generation
            return {
                "candidate_name": "Test Candidate",
                "licence_endorsement": "Driver Licence",
                "service_hub": "Test Hub"
            }