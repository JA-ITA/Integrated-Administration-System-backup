"""
Fallback storage service for certificate metadata when database is unavailable
"""
import json
import os
import uuid
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from models import Certificate, CertificateStatus, calculate_expiry_date

logger = logging.getLogger(__name__)

class FallbackStorage:
    """In-memory and file-based storage for certificate metadata when database is unavailable"""
    
    def __init__(self):
        self.certificates = {}  # In-memory storage
        self.fallback_dir = "/tmp/certificate-fallback"
        self.fallback_file = os.path.join(self.fallback_dir, "certificates.json")
        
        # Create fallback directory
        os.makedirs(self.fallback_dir, exist_ok=True)
        
        # Load existing data
        self._load_fallback_data()
    
    def _load_fallback_data(self):
        """Load certificate data from fallback file"""
        try:
            if os.path.exists(self.fallback_file):
                with open(self.fallback_file, 'r') as f:
                    data = json.load(f)
                    self.certificates = data
                    logger.info(f"Loaded {len(self.certificates)} certificates from fallback storage")
            else:
                logger.info("No existing fallback data found")
        except Exception as e:
            logger.error(f"Failed to load fallback data: {e}")
            self.certificates = {}
    
    def _save_fallback_data(self):
        """Save certificate data to fallback file"""
        try:
            with open(self.fallback_file, 'w') as f:
                json.dump(self.certificates, f, indent=2, default=str)
            logger.info(f"Saved {len(self.certificates)} certificates to fallback storage")
        except Exception as e:
            logger.error(f"Failed to save fallback data: {e}")
    
    def create_certificate(
        self,
        certificate_id: uuid.UUID,
        driver_record_id: uuid.UUID,
        certificate_type: str,
        licence_endorsement: str,
        candidate_name: str,
        service_hub: str,
        file_url: str,
        file_size: int,
        file_hash: str,
        qr_code: Optional[str] = None,
        verification_token: Optional[str] = None,
        certificate_metadata: Optional[Dict[str, Any]] = None,
        template_used: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new certificate record in fallback storage"""
        
        issue_date = datetime.now(timezone.utc)
        expiry_date = calculate_expiry_date(certificate_type, issue_date)
        
        certificate_data = {
            "id": str(certificate_id),
            "driver_record_id": str(driver_record_id),
            "certificate_type": certificate_type,
            "licence_endorsement": licence_endorsement,
            "candidate_name": candidate_name,
            "service_hub": service_hub,
            "issue_date": issue_date.isoformat(),
            "expiry_date": expiry_date.isoformat() if expiry_date else None,
            "status": CertificateStatus.ACTIVE,
            "file_url": file_url,
            "file_size": file_size,
            "file_hash": file_hash,
            "qr_code": qr_code,
            "verification_token": verification_token,
            "certificate_metadata": certificate_metadata or {},
            "template_used": template_used,
            "created_at": issue_date.isoformat(),
            "updated_at": issue_date.isoformat()
        }
        
        self.certificates[str(certificate_id)] = certificate_data
        self._save_fallback_data()
        
        logger.info(f"Certificate created in fallback storage: {certificate_id}")
        return certificate_data
    
    def find_certificate_by_id(self, certificate_id: uuid.UUID) -> Optional[Dict[str, Any]]:
        """Find certificate by ID in fallback storage"""
        cert_data = self.certificates.get(str(certificate_id))
        if cert_data:
            logger.info(f"Certificate found in fallback storage: {certificate_id}")
        return cert_data
    
    def find_certificate_by_driver_record(self, driver_record_id: uuid.UUID) -> Optional[Dict[str, Any]]:
        """Find most recent active certificate by driver record ID"""
        driver_certs = []
        
        for cert_data in self.certificates.values():
            if cert_data["driver_record_id"] == str(driver_record_id):
                if cert_data["status"] == CertificateStatus.ACTIVE:
                    # Check if valid (not expired)
                    if self._is_certificate_valid(cert_data):
                        driver_certs.append(cert_data)
        
        if driver_certs:
            # Return most recent
            driver_certs.sort(key=lambda x: x["created_at"], reverse=True)
            cert_data = driver_certs[0]
            logger.info(f"Certificate found for driver record in fallback storage: {driver_record_id}")
            return cert_data
        
        return None
    
    def find_certificate_by_verification_token(self, verification_token: str) -> Optional[Dict[str, Any]]:
        """Find certificate by verification token"""
        for cert_data in self.certificates.values():
            if cert_data.get("verification_token") == verification_token:
                logger.info(f"Certificate found by verification token in fallback storage")
                return cert_data
        
        return None
    
    def get_driver_certificates(self, driver_record_id: uuid.UUID) -> List[Dict[str, Any]]:
        """Get all certificates for a driver record"""
        driver_certs = []
        
        for cert_data in self.certificates.values():
            if cert_data["driver_record_id"] == str(driver_record_id):
                driver_certs.append(cert_data)
        
        # Sort by creation date (newest first)
        driver_certs.sort(key=lambda x: x["created_at"], reverse=True)
        
        logger.info(f"Found {len(driver_certs)} certificates for driver record in fallback storage: {driver_record_id}")
        return driver_certs
    
    def _is_certificate_valid(self, cert_data: Dict[str, Any]) -> bool:
        """Check if certificate is currently valid"""
        if cert_data["status"] != CertificateStatus.ACTIVE:
            return False
        
        if cert_data["expiry_date"]:
            try:
                expiry_date = datetime.fromisoformat(cert_data["expiry_date"].replace('Z', '+00:00'))
                if expiry_date < datetime.now(timezone.utc):
                    return False
            except Exception:
                pass
        
        return True
    
    def certificate_to_dict(self, cert_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert certificate data to API response format"""
        result = cert_data.copy()
        result["is_valid"] = self._is_certificate_valid(cert_data)
        return result
    
    def get_status(self) -> Dict[str, Any]:
        """Get fallback storage status"""
        return {
            "storage_type": "fallback",
            "certificates_count": len(self.certificates),
            "fallback_file": self.fallback_file,
            "file_exists": os.path.exists(self.fallback_file)
        }

# Global instance
fallback_storage = FallbackStorage()