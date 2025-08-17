"""
Registration business logic service
"""
import logging
import uuid
import base64
import os
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import get_db_session
from models import (
    Registration, Document, RegistrationRequest, RegistrationResponse, 
    RegistrationCreateResponse, VehicleCategory, RegistrationStatus,
    DocumentType
)
from services.document_service import DocumentService
from services.validation_service import ValidationService

logger = logging.getLogger(__name__)

class RegistrationService:
    """Service for handling registration business logic"""
    
    def __init__(self):
        self.document_service = DocumentService()
        self.validation_service = ValidationService()
    
    async def create_registration(
        self,
        registration_data: RegistrationRequest,
        candidate_info: Dict[str, Any]
    ) -> RegistrationCreateResponse:
        """Create a new registration with validation"""
        
        try:
            # Extract candidate information from JWT claims
            candidate_id = candidate_info.get("candidate_id")
            full_name = candidate_info.get("full_name")
            dob = candidate_info.get("dob")
            address = candidate_info.get("address")
            phone = candidate_info.get("phone")
            
            if not all([candidate_id, full_name, dob, address, phone]):
                return RegistrationCreateResponse(
                    success=False,
                    message="Missing required candidate information in JWT claims",
                    validation_errors=["candidate_id", "full_name", "dob", "address", "phone"]
                )
            
            # Parse date of birth
            if isinstance(dob, str):
                dob = datetime.fromisoformat(dob.replace('Z', '+00:00'))
            
            # Validate external dependencies
            validation_result = await self.validation_service.validate_external_dependencies(
                booking_id=registration_data.booking_id,
                receipt_no=registration_data.receipt_no,
                candidate_id=candidate_id
            )
            
            if not validation_result["valid"]:
                return RegistrationCreateResponse(
                    success=False,
                    message="External validation failed",
                    validation_errors=validation_result["errors"]
                )
            
            # Create registration record
            registration = Registration(
                candidate_id=candidate_id,
                booking_id=registration_data.booking_id,
                receipt_no=registration_data.receipt_no,
                full_name=full_name,
                dob=dob,
                address=address,
                phone=phone,
                vehicle_weight_kg=registration_data.vehicle_weight_kg,
                vehicle_category=registration_data.vehicle_category.value,
                manager_override=registration_data.manager_override or False,
                override_reason=registration_data.override_reason,
                override_by=registration_data.override_by
            )
            
            # Validate business rules
            age_valid, age_message = registration.validate_age_requirements()
            if not age_valid:
                return RegistrationCreateResponse(
                    success=False,
                    message="Age validation failed",
                    validation_errors=[age_message]
                )
            
            # Process documents
            processed_docs = []
            document_errors = []
            
            for doc in registration_data.docs:
                try:
                    doc_result = await self.document_service.process_document(
                        registration_id=registration.id,
                        document_upload=doc
                    )
                    if doc_result["success"]:
                        processed_docs.append(doc_result["document_info"])
                    else:
                        document_errors.append(f"Document {doc.filename}: {doc_result['error']}")
                except Exception as e:
                    document_errors.append(f"Document {doc.filename}: {str(e)}")
            
            if document_errors:
                return RegistrationCreateResponse(
                    success=False,
                    message="Document processing failed",
                    validation_errors=document_errors
                )
            
            # Store processed documents in registration
            registration.docs = processed_docs
            
            # Validate medical certificate requirements
            mc_valid, mc_message = registration.validate_medical_certificates()
            if not mc_valid:
                return RegistrationCreateResponse(
                    success=False,
                    message="Medical certificate validation failed",
                    validation_errors=[mc_message]
                )
            
            # Determine registration status
            if registration.manager_override:
                registration.status = RegistrationStatus.RD_REVIEW.value
            else:
                registration.status = RegistrationStatus.REGISTERED.value
            
            # Save to database
            async with get_db_session() as session:
                session.add(registration)
                await session.commit()
                await session.refresh(registration)
            
            logger.info(f"Registration created successfully: {registration.id}")
            
            # Create response
            registration_response = RegistrationResponse(
                id=registration.id,
                candidate_id=registration.candidate_id,
                booking_id=registration.booking_id,
                receipt_no=registration.receipt_no,
                full_name=registration.full_name,
                dob=registration.dob,
                address=registration.address,
                phone=registration.phone,
                vehicle_weight_kg=registration.vehicle_weight_kg,
                vehicle_category=registration.vehicle_category,
                status=registration.status,
                age_in_years=registration.age_in_years,
                required_medical_certificate=registration.required_medical_certificate,
                manager_override=registration.manager_override,
                override_reason=registration.override_reason,
                docs=registration.docs,
                registered_at=registration.registered_at,
                created_at=registration.created_at
            )
            
            return RegistrationCreateResponse(
                success=True,
                registration=registration_response,
                message=f"Registration {registration.status.lower()} successfully",
                driver_record_id=registration.id
            )
            
        except Exception as e:
            logger.error(f"Registration creation failed: {e}")
            return RegistrationCreateResponse(
                success=False,
                message="Internal server error during registration",
                validation_errors=[str(e)]
            )
    
    async def get_registration(self, registration_id: uuid.UUID) -> Optional[RegistrationResponse]:
        """Get registration by ID"""
        try:
            async with get_db_session() as session:
                result = await session.execute(
                    select(Registration).where(Registration.id == registration_id)
                )
                registration = result.scalar_one_or_none()
                
                if not registration:
                    return None
                
                return RegistrationResponse(
                    id=registration.id,
                    candidate_id=registration.candidate_id,
                    booking_id=registration.booking_id,
                    receipt_no=registration.receipt_no,
                    full_name=registration.full_name,
                    dob=registration.dob,
                    address=registration.address,
                    phone=registration.phone,
                    vehicle_weight_kg=registration.vehicle_weight_kg,
                    vehicle_category=registration.vehicle_category,
                    status=registration.status,
                    age_in_years=registration.age_in_years,
                    required_medical_certificate=registration.required_medical_certificate,
                    manager_override=registration.manager_override,
                    override_reason=registration.override_reason,
                    docs=registration.docs,
                    registered_at=registration.registered_at,
                    created_at=registration.created_at
                )
                
        except Exception as e:
            logger.error(f"Failed to get registration {registration_id}: {e}")
            return None
    
    async def get_candidate_registrations(self, candidate_id: uuid.UUID) -> List[RegistrationResponse]:
        """Get all registrations for a candidate"""
        try:
            async with get_db_session() as session:
                result = await session.execute(
                    select(Registration)
                    .where(Registration.candidate_id == candidate_id)
                    .order_by(Registration.created_at.desc())
                )
                registrations = result.scalars().all()
                
                return [
                    RegistrationResponse(
                        id=reg.id,
                        candidate_id=reg.candidate_id,
                        booking_id=reg.booking_id,
                        receipt_no=reg.receipt_no,
                        full_name=reg.full_name,
                        dob=reg.dob,
                        address=reg.address,
                        phone=reg.phone,
                        vehicle_weight_kg=reg.vehicle_weight_kg,
                        vehicle_category=reg.vehicle_category,
                        status=reg.status,
                        age_in_years=reg.age_in_years,
                        required_medical_certificate=reg.required_medical_certificate,
                        manager_override=reg.manager_override,
                        override_reason=reg.override_reason,
                        docs=reg.docs,
                        registered_at=reg.registered_at,
                        created_at=reg.created_at
                    ) for reg in registrations
                ]
                
        except Exception as e:
            logger.error(f"Failed to get candidate registrations {candidate_id}: {e}")
            return []