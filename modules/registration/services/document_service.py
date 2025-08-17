"""
Document processing service for Registration microservice
Handles file uploads, validation, and storage
"""
import logging
import uuid
import base64
import os
import hashlib
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from pathlib import Path
from models import DocumentUpload, DocumentType
from config import config

logger = logging.getLogger(__name__)

class DocumentService:
    """Service for handling document uploads and storage"""
    
    def __init__(self):
        # Create local storage directory
        self.storage_path = Path("/app/storage/registration/documents")
        self.storage_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Document storage initialized: {self.storage_path}")
    
    async def process_document(
        self,
        registration_id: uuid.UUID,
        document_upload: DocumentUpload
    ) -> Dict[str, Any]:
        """Process and store a document upload"""
        
        try:
            # Validate document
            validation_result = self._validate_document(document_upload)
            if not validation_result["valid"]:
                return {
                    "success": False,
                    "error": validation_result["error"]
                }
            
            # Decode base64 content
            try:
                file_content = base64.b64decode(document_upload.content)
            except Exception as e:
                return {
                    "success": False,
                    "error": f"Invalid base64 content: {str(e)}"
                }
            
            # Generate unique filename
            file_hash = hashlib.md5(file_content).hexdigest()[:8]
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_extension = self._get_file_extension(document_upload.filename, document_upload.mime_type)
            
            unique_filename = f"{registration_id}_{document_upload.type.value}_{timestamp}_{file_hash}{file_extension}"
            
            # Create storage path for this registration
            registration_storage_path = self.storage_path / str(registration_id)
            registration_storage_path.mkdir(exist_ok=True)
            
            # Save file
            file_path = registration_storage_path / unique_filename
            with open(file_path, 'wb') as f:
                f.write(file_content)
            
            # Create document info for storage in registration.docs JSONB
            document_info = {
                "id": str(uuid.uuid4()),
                "type": document_upload.type.value,
                "original_filename": document_upload.filename,
                "stored_filename": unique_filename,
                "file_size_bytes": len(file_content),
                "mime_type": document_upload.mime_type,
                "storage_url": f"local://{file_path}",
                "storage_provider": "local",
                "file_hash": file_hash,
                "uploaded_at": datetime.now(timezone.utc).isoformat(),
                "is_processed": True
            }
            
            logger.info(f"Document processed successfully: {unique_filename}")
            
            return {
                "success": True,
                "document_info": document_info,
                "file_path": str(file_path)
            }
            
        except Exception as e:
            logger.error(f"Document processing failed: {e}")
            return {
                "success": False,
                "error": f"Document processing error: {str(e)}"
            }
    
    def _validate_document(self, document_upload: DocumentUpload) -> Dict[str, Any]:
        """Validate document upload"""
        
        try:
            # Check file size (estimated from base64)
            estimated_size = (len(document_upload.content) * 3) // 4
            if estimated_size > config.registration.max_document_size:
                return {
                    "valid": False,
                    "error": f"File size ({estimated_size // (1024*1024)}MB) exceeds maximum allowed size ({config.registration.max_document_size // (1024*1024)}MB)"
                }
            
            # Validate format based on document type
            allowed_formats = self._get_allowed_formats(document_upload.type)
            file_extension = self._get_file_extension(document_upload.filename, document_upload.mime_type)
            
            if file_extension.lstrip('.').lower() not in allowed_formats:
                return {
                    "valid": False,
                    "error": f"File format '{file_extension}' not allowed for document type '{document_upload.type.value}'. Allowed formats: {allowed_formats}"
                }
            
            # Validate MIME type
            if not self._validate_mime_type(document_upload.mime_type, document_upload.type):
                return {
                    "valid": False,
                    "error": f"Invalid MIME type '{document_upload.mime_type}' for document type '{document_upload.type.value}'"
                }
            
            return {"valid": True}
            
        except Exception as e:
            return {
                "valid": False,
                "error": f"Validation error: {str(e)}"
            }
    
    def _get_allowed_formats(self, document_type: DocumentType) -> list:
        """Get allowed formats for document type"""
        
        if document_type == DocumentType.PHOTO:
            return config.registration.allowed_photo_formats
        elif document_type == DocumentType.ID_PROOF:
            return config.registration.allowed_id_proof_formats
        elif document_type in [DocumentType.MC1, DocumentType.MC2]:
            return config.registration.allowed_medical_formats
        elif document_type == DocumentType.OTHER:
            return config.registration.allowed_other_formats
        else:
            return []
    
    def _get_file_extension(self, filename: str, mime_type: str) -> str:
        """Extract file extension from filename or mime type"""
        
        # Try filename first
        if '.' in filename:
            return '.' + filename.split('.')[-1].lower()
        
        # Fall back to mime type
        mime_extensions = {
            'image/jpeg': '.jpg',
            'image/jpg': '.jpg',
            'image/png': '.png',
            'application/pdf': '.pdf'
        }
        
        return mime_extensions.get(mime_type.lower(), '')
    
    def _validate_mime_type(self, mime_type: str, document_type: DocumentType) -> bool:
        """Validate MIME type for document type"""
        
        allowed_mime_types = {
            DocumentType.PHOTO: ['image/jpeg', 'image/jpg', 'image/png'],
            DocumentType.ID_PROOF: ['image/jpeg', 'image/jpg', 'image/png', 'application/pdf'],
            DocumentType.MC1: ['application/pdf'],
            DocumentType.MC2: ['application/pdf'],
            DocumentType.OTHER: ['application/pdf']
        }
        
        allowed = allowed_mime_types.get(document_type, [])
        return mime_type.lower() in allowed
    
    async def get_document(self, registration_id: uuid.UUID, document_id: str) -> Optional[Dict[str, Any]]:
        """Get document information"""
        try:
            # This would typically query the database for document metadata
            # For now, we'll return basic file info if file exists
            registration_path = self.storage_path / str(registration_id)
            if registration_path.exists():
                for file_path in registration_path.glob("*"):
                    if document_id in file_path.name:
                        return {
                            "document_id": document_id,
                            "file_path": str(file_path),
                            "exists": True
                        }
            return None
        except Exception as e:
            logger.error(f"Failed to get document {document_id}: {e}")
            return None
    
    async def delete_document(self, registration_id: uuid.UUID, document_id: str) -> bool:
        """Delete a document"""
        try:
            registration_path = self.storage_path / str(registration_id)
            if registration_path.exists():
                for file_path in registration_path.glob("*"):
                    if document_id in file_path.name:
                        os.remove(file_path)
                        logger.info(f"Document deleted: {file_path}")
                        return True
            return False
        except Exception as e:
            logger.error(f"Failed to delete document {document_id}: {e}")
            return False