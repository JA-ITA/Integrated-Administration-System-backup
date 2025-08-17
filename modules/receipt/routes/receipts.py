"""
Receipt validation endpoints
"""
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import (
    ReceiptValidationRequest, 
    ReceiptValidationResponse, 
    ErrorResponse,
    ReceiptResponse
)
from services.receipt_service import ReceiptService
from services.event_service import EventService

logger = logging.getLogger(__name__)
router = APIRouter()

# Dependencies
def get_receipt_service(request: Request) -> ReceiptService:
    """Get receipt service instance"""
    event_service = getattr(request.app.state, 'event_service', None)
    if not event_service:
        raise HTTPException(status_code=500, detail="Event service not available")
    return ReceiptService(event_service)

@router.post("/receipts/validate", response_model=ReceiptValidationResponse)
async def validate_receipt(
    validation_request: ReceiptValidationRequest,
    receipt_service: ReceiptService = Depends(get_receipt_service),
    session: AsyncSession = Depends(get_db)
) -> JSONResponse:
    """
    Validate a receipt according to business rules
    
    - **receipt_no**: Alphanumeric 8-20 characters (A-Z, 0-9)
    - **issue_date**: Receipt issue date (must be ≤ 365 days old)
    - **location**: TAJ office location or 'TAJ Online'
    - **amount**: Receipt amount (informational)
    
    Returns:
    - **200 OK**: Receipt validated successfully
    - **409 Duplicate**: Receipt already used
    - **400 Bad Request**: Validation errors
    """
    if not session:
        logger.error("Database session not available")
        return JSONResponse(
            status_code=503,
            content=ErrorResponse(
                error="Service temporarily unavailable",
                detail="Database connection not available",
                code="DB_UNAVAILABLE"
            ).dict()
        )
    
    try:
        logger.info(f"Validating receipt: {validation_request.receipt_no}")
        
        # Perform validation
        response, status_code = await receipt_service.validate_receipt(
            session, validation_request
        )
        
        logger.info(f"Receipt validation completed: {validation_request.receipt_no}, status: {status_code}")
        
        return JSONResponse(
            status_code=status_code,
            content=response.dict()
        )
        
    except ValidationError as e:
        logger.warning(f"Validation error for receipt {validation_request.receipt_no}: {e}")
        
        error_response = ErrorResponse(
            error="Validation failed",
            detail=str(e),
            code="VALIDATION_ERROR"
        )
        
        return JSONResponse(
            status_code=400,
            content=error_response.dict()
        )
        
    except Exception as e:
        logger.error(f"Unexpected error validating receipt {validation_request.receipt_no}: {e}")
        
        error_response = ErrorResponse(
            error="Internal server error",
            detail=str(e),
            code="INTERNAL_ERROR"
        )
        
        return JSONResponse(
            status_code=500,
            content=error_response.dict()
        )

@router.get("/receipts/{receipt_no}", response_model=ReceiptResponse)
async def get_receipt(
    receipt_no: str,
    receipt_service: ReceiptService = Depends(get_receipt_service),
    session: AsyncSession = Depends(get_db)
):
    """
    Get receipt details by receipt number
    """
    if not session:
        raise HTTPException(
            status_code=503,
            detail="Database connection not available"
        )
    
    try:
        receipt = await receipt_service.get_receipt_by_number(session, receipt_no.upper())
        
        if not receipt:
            raise HTTPException(
                status_code=404,
                detail=f"Receipt {receipt_no} not found"
            )
        
        return ReceiptResponse.from_orm(receipt)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching receipt {receipt_no}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )

@router.get("/receipts")
async def get_receipt_statistics(
    receipt_service: ReceiptService = Depends(get_receipt_service),
    session: AsyncSession = Depends(get_db)
):
    """
    Get receipt validation statistics
    """
    if not session:
        raise HTTPException(
            status_code=503,
            detail="Database connection not available"
        )
    
    try:
        stats = await receipt_service.get_receipt_statistics(session)
        return {
            "status": "success",
            "statistics": stats,
            "message": "Receipt statistics retrieved successfully"
        }
        
    except Exception as e:
        logger.error(f"Error fetching receipt statistics: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )

@router.get("/health/receipts")
async def receipt_health_check():
    """Receipt service specific health check"""
    return {
        "status": "healthy",
        "component": "receipt-validation",
        "version": "1.0.0"
    }