"""
Certificate routes for ITADIAS Certificate Microservice
"""
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import get_db
from models import (
    Certificate, CertificateGenerateRequest, CertificateGenerateResponse,
    CertificateVerificationResponse, CertificateMetadata, ErrorResponse,
    calculate_expiry_date, CertificateStatus
)
from services.certificate_service import CertificateService
from services.storage_service import StorageService
from services.event_service import EventService
from services.fallback_storage import fallback_storage

logger = logging.getLogger(__name__)

router = APIRouter()

def get_certificate_service(request: Request) -> CertificateService:
    """Dependency to get certificate service"""
    return request.app.state.certificate_service

def get_storage_service(request: Request) -> StorageService:
    """Dependency to get storage service"""
    return request.app.state.storage_service

def get_event_service(request: Request) -> EventService:
    """Dependency to get event service"""
    return request.app.state.event_service

@router.post("/certificates/generate", response_model=CertificateGenerateResponse)
async def generate_certificate(
    request: CertificateGenerateRequest,
    db: AsyncSession = Depends(get_db),
    certificate_service: CertificateService = Depends(get_certificate_service),
    storage_service: StorageService = Depends(get_storage_service),
    event_service: EventService = Depends(get_event_service)
):
    """Generate a new certificate for a driver record"""
    
    request_id = str(uuid.uuid4())
    logger.info(f"Certificate generation request received", extra={
        "request_id": request_id,
        "driver_record_id": str(request.driver_record_id)
    })
    
    try:
        # Check if certificate already exists (database or fallback)
        existing_cert = None
        existing_cert_data = None
        
        if db:
            # Try database first
            existing_cert_query = select(Certificate).where(
                Certificate.driver_record_id == request.driver_record_id,
                Certificate.status == CertificateStatus.ACTIVE
            )
            result = await db.execute(existing_cert_query)
            existing_cert = result.scalar_one_or_none()
            
            if existing_cert and existing_cert.is_valid():
                logger.info(f"Active certificate already exists in database for driver_record_id: {request.driver_record_id}")
                
                # Generate fresh download URL
                file_name = existing_cert.file_url.split('/')[-1]
                download_url = await storage_service.generate_download_url(file_name)
                
                return CertificateGenerateResponse(
                    certificate_id=existing_cert.id,
                    download_url=download_url,
                    verification_token=existing_cert.verification_token,
                    qr_code=existing_cert.qr_code,
                    issue_date=existing_cert.issue_date,
                    expiry_date=existing_cert.expiry_date,
                    metadata=existing_cert.certificate_metadata or {}
                )
        else:
            # Use fallback storage
            logger.info("Database unavailable, using fallback storage")
            existing_cert_data = fallback_storage.find_certificate_by_driver_record(request.driver_record_id)
            
            if existing_cert_data:
                logger.info(f"Active certificate already exists in fallback storage for driver_record_id: {request.driver_record_id}")
                
                # Generate fresh download URL
                file_name = existing_cert_data["file_url"].split('/')[-1]
                download_url = await storage_service.generate_download_url(file_name)
                
                return CertificateGenerateResponse(
                    certificate_id=uuid.UUID(existing_cert_data["id"]),
                    download_url=download_url,
                    verification_token=existing_cert_data["verification_token"],
                    qr_code=existing_cert_data["qr_code"],
                    issue_date=datetime.fromisoformat(existing_cert_data["issue_date"].replace('Z', '+00:00')),
                    expiry_date=datetime.fromisoformat(existing_cert_data["expiry_date"].replace('Z', '+00:00')) if existing_cert_data["expiry_date"] else None,
                    metadata=existing_cert_data["certificate_metadata"] or {}
                )
        
        # Fetch certificate data from other services
        cert_data = await certificate_service.fetch_certificate_data(
            request.driver_record_id
        )
        
        # Generate PDF certificate
        pdf_bytes, pdf_metadata = await certificate_service.generate_certificate_pdf(
            request.driver_record_id, cert_data
        )
        
        # Generate file name
        certificate_id = uuid.uuid4()
        file_name = f"certificate-{certificate_id}.pdf"
        
        # Upload to storage
        upload_result = await storage_service.upload_file(
            file_data=pdf_bytes,
            file_name=file_name,
            content_type="application/pdf",
            metadata={
                "certificate-id": str(certificate_id),
                "driver-record-id": str(request.driver_record_id)
            }
        )
        
        # Determine certificate type and expiry
        licence_endorsement = cert_data.get("licence_endorsement", "Driver Licence")
        issue_date = datetime.now(timezone.utc)
        
        if "class" in licence_endorsement.lower():
            cert_type = "driver_licence"
        elif any(keyword in licence_endorsement.lower() for keyword in ["hazmat", "endorsement", "ppv"]):
            cert_type = "endorsement"
        else:
            cert_type = "completion"
        
        expiry_date = calculate_expiry_date(cert_type, issue_date)
        
        # Store certificate record (database or fallback)
        certificate = None
        certificate_data = None
        
        if db:
            # Create database record
            certificate = Certificate(
                id=certificate_id,
                driver_record_id=request.driver_record_id,
                certificate_type=cert_type,
                licence_endorsement=licence_endorsement,
                candidate_name=cert_data.get("candidate_name", "Unknown"),
                service_hub=cert_data.get("service_hub", "Unknown Hub"),
                issue_date=issue_date,
                expiry_date=expiry_date,
                file_url=upload_result["file_url"],
                file_size=upload_result["file_size"],
                file_hash=upload_result["file_hash"],
                qr_code=pdf_metadata.get("qr_code_url"),
                verification_token=pdf_metadata.get("verification_token"),
                certificate_metadata=pdf_metadata,
                template_used=pdf_metadata.get("template_used"),
                status=CertificateStatus.ACTIVE
            )
            
            db.add(certificate)
            await db.commit()
            await db.refresh(certificate)
            
            logger.info(f"Certificate saved to database: {certificate_id}")
            
        else:
            # Use fallback storage
            certificate_data = fallback_storage.create_certificate(
                certificate_id=certificate_id,
                driver_record_id=request.driver_record_id,
                certificate_type=cert_type,
                licence_endorsement=licence_endorsement,
                candidate_name=cert_data.get("candidate_name", "Unknown"),
                service_hub=cert_data.get("service_hub", "Unknown Hub"),
                file_url=upload_result["file_url"],
                file_size=upload_result["file_size"],
                file_hash=upload_result["file_hash"],
                qr_code=pdf_metadata.get("qr_code_url"),
                verification_token=pdf_metadata.get("verification_token"),
                certificate_metadata=pdf_metadata,
                template_used=pdf_metadata.get("template_used")
            )
            
            logger.info(f"Certificate saved to fallback storage: {certificate_id}")
        
        # Generate download URL
        download_url = await storage_service.generate_download_url(file_name)
        
        # Publish CertificateGenerated event
        candidate_name = certificate.candidate_name if certificate else certificate_data["candidate_name"]
        service_hub = certificate.service_hub if certificate else certificate_data["service_hub"]
        
        await event_service.publish_certificate_generated(
            driver_record_id=str(request.driver_record_id),
            certificate_id=str(certificate_id),
            candidate_name=candidate_name,
            licence_endorsement=licence_endorsement,
            issue_date=issue_date,
            expiry_date=expiry_date,
            download_url=download_url,
            service_hub=service_hub,
            additional_data={
                "certificate_type": cert_type,
                "file_size": upload_result["file_size"],
                "template_used": pdf_metadata.get("template_used"),
                "storage_mode": "database" if certificate else "fallback"
            }
        )
        
        logger.info(f"Certificate generated successfully", extra={
            "request_id": request_id,
            "certificate_id": str(certificate.id),
            "file_size": upload_result["file_size"]
        })
        
        return CertificateGenerateResponse(
            certificate_id=certificate_id,
            download_url=download_url,
            verification_token=certificate.verification_token if certificate else certificate_data["verification_token"],
            qr_code=certificate.qr_code if certificate else certificate_data["qr_code"],
            issue_date=certificate.issue_date if certificate else datetime.fromisoformat(certificate_data["issue_date"].replace('Z', '+00:00')),
            expiry_date=certificate.expiry_date if certificate else (datetime.fromisoformat(certificate_data["expiry_date"].replace('Z', '+00:00')) if certificate_data["expiry_date"] else None),
            metadata=certificate.certificate_metadata if certificate else certificate_data["certificate_metadata"] or {}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Certificate generation failed", extra={
            "request_id": request_id,
            "error": str(e),
            "driver_record_id": str(request.driver_record_id)
        })
        
        # Rollback database transaction if applicable
        if db:
            await db.rollback()
        
        raise HTTPException(
            status_code=500,
            detail=f"Certificate generation failed: {str(e)}"
        )

@router.get("/certificates/{certificate_id}/download")
async def download_certificate(
    certificate_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    storage_service: StorageService = Depends(get_storage_service),
    event_service: EventService = Depends(get_event_service)
):
    """Download certificate PDF via redirect to pre-signed URL"""
    
    logger.info(f"Certificate download requested", extra={
        "certificate_id": str(certificate_id)
    })
    
    try:
        certificate = None
        certificate_data = None
        
        if db:
            # Try database first
            cert_query = select(Certificate).where(Certificate.id == certificate_id)
            result = await db.execute(cert_query)
            certificate = result.scalar_one_or_none()
            
            if not certificate:
                logger.warning(f"Certificate not found in database: {certificate_id}")
                # Fall back to fallback storage
                certificate_data = fallback_storage.find_certificate_by_id(certificate_id)
        else:
            # Use fallback storage
            logger.info("Database unavailable, using fallback storage")
            certificate_data = fallback_storage.find_certificate_by_id(certificate_id)
        
        # Check if certificate exists
        if not certificate and not certificate_data:
            logger.warning(f"Certificate not found: {certificate_id}")
            raise HTTPException(status_code=404, detail="Certificate not found")
        
        # Check validity
        if certificate:
            if not certificate.is_valid():
                logger.warning(f"Certificate is not valid: {certificate_id}")
                raise HTTPException(
                    status_code=410, 
                    detail=f"Certificate is {certificate.status}"
                )
            file_url = certificate.file_url
        else:
            # Using fallback storage
            if not fallback_storage._is_certificate_valid(certificate_data):
                logger.warning(f"Certificate is not valid: {certificate_id}")
                raise HTTPException(
                    status_code=410, 
                    detail=f"Certificate is {certificate_data['status']}"
                )
            file_url = certificate_data["file_url"]
        
        # Extract file name from storage URL
        file_name = file_url.split('/')[-1]
        
        # Check if file exists in storage
        file_exists = await storage_service.file_exists(file_name)
        if not file_exists:
            logger.error(f"Certificate file not found in storage: {file_name}")
            raise HTTPException(
                status_code=404, 
                detail="Certificate file not found"
            )
        
        # Generate pre-signed download URL
        download_url = await storage_service.generate_download_url(file_name)
        
        # Publish CertificateDownloaded event
        cert_id = str(certificate.id) if certificate else certificate_data["id"]
        await event_service.publish_certificate_downloaded(
            certificate_id=cert_id,
            download_timestamp=datetime.now(timezone.utc)
        )
        
        logger.info(f"Certificate download URL generated", extra={
            "certificate_id": cert_id,
            "file_name": file_name
        })
        
        # Return redirect to pre-signed URL
        return RedirectResponse(url=download_url, status_code=302)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Certificate download failed", extra={
            "certificate_id": str(certificate_id),
            "error": str(e)
        })
        
        raise HTTPException(
            status_code=500,
            detail="Certificate download failed"
        )

@router.get("/certificates/{driver_record_id}/download")
async def download_certificate_by_driver_record(
    driver_record_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    storage_service: StorageService = Depends(get_storage_service),
    event_service: EventService = Depends(get_event_service)
):
    """Download certificate PDF by driver record ID via redirect to pre-signed URL"""
    
    logger.info(f"Certificate download requested for driver record", extra={
        "driver_record_id": str(driver_record_id)
    })
    
    try:
        certificate = None
        certificate_data = None
        
        if db:
            # Try database first
            cert_query = select(Certificate).where(
                Certificate.driver_record_id == driver_record_id,
                Certificate.status == CertificateStatus.ACTIVE
            ).order_by(Certificate.created_at.desc())
            
            result = await db.execute(cert_query)
            certificate = result.scalar_one_or_none()
            
            if not certificate:
                logger.warning(f"No certificate found in database for driver record: {driver_record_id}")
                # Fall back to fallback storage
                certificate_data = fallback_storage.find_certificate_by_driver_record(driver_record_id)
        else:
            # Use fallback storage
            logger.info("Database unavailable, using fallback storage")
            certificate_data = fallback_storage.find_certificate_by_driver_record(driver_record_id)
        
        # Check if certificate exists
        if not certificate and not certificate_data:
            logger.warning(f"No active certificate found for driver record: {driver_record_id}")
            raise HTTPException(status_code=404, detail="No active certificate found for this driver record")
        
        # Check validity
        if certificate:
            if not certificate.is_valid():
                logger.warning(f"Certificate is not valid: {certificate.id}")
                raise HTTPException(
                    status_code=410, 
                    detail=f"Certificate is {certificate.status}"
                )
            file_url = certificate.file_url
            cert_id = certificate.id
        else:
            # Using fallback storage
            if not fallback_storage._is_certificate_valid(certificate_data):
                logger.warning(f"Certificate is not valid: {certificate_data['id']}")
                raise HTTPException(
                    status_code=410, 
                    detail=f"Certificate is {certificate_data['status']}"
                )
            file_url = certificate_data["file_url"]
            cert_id = certificate_data["id"]
        
        # Extract file name from storage URL
        file_name = file_url.split('/')[-1]
        
        # Check if file exists in storage
        file_exists = await storage_service.file_exists(file_name)
        if not file_exists:
            logger.error(f"Certificate file not found in storage: {file_name}")
            raise HTTPException(
                status_code=404, 
                detail="Certificate file not found"
            )
        
        # Generate pre-signed download URL
        download_url = await storage_service.generate_download_url(file_name)
        
        # Publish CertificateDownloaded event
        await event_service.publish_certificate_downloaded(
            certificate_id=str(certificate.id),
            download_timestamp=datetime.now(timezone.utc)
        )
        
        logger.info(f"Certificate download URL generated for driver record", extra={
            "certificate_id": str(certificate.id),
            "driver_record_id": str(driver_record_id),
            "file_name": file_name
        })
        
        # Return redirect to pre-signed URL
        return RedirectResponse(url=download_url, status_code=302)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Certificate download failed for driver record", extra={
            "driver_record_id": str(driver_record_id),
            "error": str(e)
        })
        
        raise HTTPException(
            status_code=500,
            detail="Certificate download failed"
        )

@router.get("/certificates/verify/{verification_token}", response_model=CertificateVerificationResponse)
async def verify_certificate(
    verification_token: str,
    db: AsyncSession = Depends(get_db),
    event_service: EventService = Depends(get_event_service)
):
    """Verify certificate authenticity using QR code token"""
    
    logger.info(f"Certificate verification requested", extra={
        "verification_token": verification_token
    })
    
    try:
        if not db:
            raise HTTPException(status_code=503, detail="Database service unavailable")
        
        # Find certificate by verification token
        cert_query = select(Certificate).where(
            Certificate.verification_token == verification_token
        )
        result = await db.execute(cert_query)
        certificate = result.scalar_one_or_none()
        
        verification_timestamp = datetime.now(timezone.utc)
        
        if not certificate:
            # Publish verification event (failed)
            await event_service.publish_certificate_verified(
                certificate_id="unknown",
                verification_token=verification_token,
                verification_result=False,
                verification_timestamp=verification_timestamp
            )
            
            return CertificateVerificationResponse(
                valid=False,
                message="Invalid verification token"
            )
        
        is_valid = certificate.is_valid()
        
        # Publish verification event
        await event_service.publish_certificate_verified(
            certificate_id=str(certificate.id),
            verification_token=verification_token,
            verification_result=is_valid,
            verification_timestamp=verification_timestamp
        )
        
        if is_valid:
            logger.info(f"Certificate verification successful", extra={
                "certificate_id": str(certificate.id),
                "verification_token": verification_token
            })
            
            return CertificateVerificationResponse(
                valid=True,
                certificate_id=certificate.id,
                candidate_name=certificate.candidate_name,
                licence_endorsement=certificate.licence_endorsement,
                issue_date=certificate.issue_date,
                expiry_date=certificate.expiry_date,
                status=certificate.status,
                service_hub=certificate.service_hub,
                message="Certificate is valid and authentic"
            )
        else:
            logger.info(f"Certificate verification failed - invalid status", extra={
                "certificate_id": str(certificate.id),
                "status": certificate.status,
                "verification_token": verification_token
            })
            
            return CertificateVerificationResponse(
                valid=False,
                certificate_id=certificate.id,
                status=certificate.status,
                message=f"Certificate is {certificate.status}"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Certificate verification failed", extra={
            "verification_token": verification_token,
            "error": str(e)
        })
        
        raise HTTPException(
            status_code=500,
            detail="Certificate verification failed"
        )

@router.get("/certificates/{certificate_id}/status")
async def get_certificate_status(
    certificate_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get certificate status and metadata"""
    
    try:
        if not db:
            raise HTTPException(status_code=503, detail="Database service unavailable")
        
        # Find certificate
        cert_query = select(Certificate).where(Certificate.id == certificate_id)
        result = await db.execute(cert_query)
        certificate = result.scalar_one_or_none()
        
        if not certificate:
            raise HTTPException(status_code=404, detail="Certificate not found")
        
        return certificate.to_dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get certificate status: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to get certificate status"
        )

@router.get("/certificates/driver/{driver_record_id}")
async def get_driver_certificates(
    driver_record_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get all certificates for a driver record"""
    
    try:
        if not db:
            raise HTTPException(status_code=503, detail="Database service unavailable")
        
        # Find all certificates for driver
        certs_query = select(Certificate).where(
            Certificate.driver_record_id == driver_record_id
        ).order_by(Certificate.created_at.desc())
        
        result = await db.execute(certs_query)
        certificates = result.scalars().all()
        
        return {
            "driver_record_id": str(driver_record_id),
            "certificates": [cert.to_dict() for cert in certificates],
            "total_count": len(certificates),
            "active_count": len([cert for cert in certificates if cert.is_valid()])
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get driver certificates: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to get driver certificates"
        )