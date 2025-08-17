"""
Receipt service for business logic
"""
import logging
from datetime import datetime, timezone
from typing import Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from models import Receipt, ReceiptValidationRequest, ReceiptValidationResponse, ReceiptResponse
from services.event_service import EventService

logger = logging.getLogger(__name__)

class ReceiptService:
    """Service for receipt validation business logic"""
    
    def __init__(self, event_service: EventService):
        self.event_service = event_service
    
    async def validate_receipt(
        self, 
        session: AsyncSession, 
        validation_request: ReceiptValidationRequest
    ) -> Tuple[ReceiptValidationResponse, int]:
        """
        Validate a receipt according to business rules
        Returns (response, http_status_code)
        """
        try:
            # Check if receipt already exists and is used
            existing_receipt = await self._get_receipt_by_number(session, validation_request.receipt_no)
            
            if existing_receipt:
                if existing_receipt.used_flag:
                    # Receipt already used - return 409 Duplicate
                    await self.event_service.publish_receipt_duplicate(
                        validation_request.receipt_no,
                        validation_request.dict()
                    )
                    
                    return ReceiptValidationResponse(
                        success=False,
                        receipt_no=validation_request.receipt_no,
                        message="Receipt has already been used",
                        validation_timestamp=datetime.now(timezone.utc)
                    ), 409
                else:
                    # Receipt exists but not used - update it and mark as used
                    existing_receipt.issue_date = validation_request.issue_date
                    existing_receipt.location = validation_request.location
                    existing_receipt.amount = validation_request.amount
                    existing_receipt.mark_as_used()
                    
                    await session.commit()
                    await session.refresh(existing_receipt)
                    
                    # Publish validation event
                    await self.event_service.publish_receipt_validated(existing_receipt)
                    
                    return ReceiptValidationResponse(
                        success=True,
                        receipt_no=existing_receipt.receipt_no,
                        message=f"Receipt {existing_receipt.receipt_no} validated successfully",
                        receipt=ReceiptResponse.from_orm(existing_receipt),
                        validation_timestamp=existing_receipt.validated_at
                    ), 200
            else:
                # New receipt - create and mark as used
                new_receipt = Receipt(
                    receipt_no=validation_request.receipt_no,
                    issue_date=validation_request.issue_date,
                    location=validation_request.location,
                    amount=validation_request.amount
                )
                new_receipt.mark_as_used()
                
                session.add(new_receipt)
                await session.commit()
                await session.refresh(new_receipt)
                
                # Publish validation event
                await self.event_service.publish_receipt_validated(new_receipt)
                
                return ReceiptValidationResponse(
                    success=True,
                    receipt_no=new_receipt.receipt_no,
                    message=f"Receipt {new_receipt.receipt_no} validated successfully",
                    receipt=ReceiptResponse.from_orm(new_receipt),
                    validation_timestamp=new_receipt.validated_at
                ), 200
                
        except IntegrityError as e:
            await session.rollback()
            logger.error(f"Database integrity error during receipt validation: {e}")
            
            return ReceiptValidationResponse(
                success=False,
                receipt_no=validation_request.receipt_no,
                message="Receipt validation failed due to database constraint",
                validation_timestamp=datetime.now(timezone.utc)
            ), 409
            
        except Exception as e:
            await session.rollback()
            logger.error(f"Unexpected error during receipt validation: {e}")
            
            # Publish invalid receipt event
            await self.event_service.publish_receipt_invalid(
                validation_request.receipt_no,
                [str(e)],
                validation_request.dict()
            )
            
            return ReceiptValidationResponse(
                success=False,
                receipt_no=validation_request.receipt_no,
                message=f"Receipt validation failed: {str(e)}",
                validation_timestamp=datetime.now(timezone.utc)
            ), 400
    
    async def _get_receipt_by_number(self, session: AsyncSession, receipt_no: str) -> Optional[Receipt]:
        """Get receipt by receipt number"""
        try:
            result = await session.execute(
                select(Receipt).where(Receipt.receipt_no == receipt_no)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error fetching receipt {receipt_no}: {e}")
            return None
    
    async def get_receipt_by_number(self, session: AsyncSession, receipt_no: str) -> Optional[Receipt]:
        """Public method to get receipt by number"""
        return await self._get_receipt_by_number(session, receipt_no)
    
    async def get_receipt_statistics(self, session: AsyncSession) -> dict:
        """Get receipt validation statistics"""
        try:
            from sqlalchemy import func
            
            # Count total receipts
            total_result = await session.execute(select(func.count(Receipt.receipt_no)))
            total_receipts = total_result.scalar()
            
            # Count used receipts
            used_result = await session.execute(select(func.count(Receipt.receipt_no)).where(Receipt.used_flag == True))
            used_receipts = used_result.scalar()
            
            return {
                "total_receipts": total_receipts,
                "used_receipts": used_receipts,
                "unused_receipts": total_receipts - used_receipts,
                "usage_rate": (used_receipts / total_receipts * 100) if total_receipts > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"Error getting receipt statistics: {e}")
            return {
                "total_receipts": 0,
                "used_receipts": 0,
                "unused_receipts": 0,
                "usage_rate": 0,
                "error": str(e)
            }