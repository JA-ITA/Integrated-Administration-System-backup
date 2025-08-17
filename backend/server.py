from fastapi import FastAPI, APIRouter
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional
import uuid
from datetime import datetime
from calendar_client import calendar_client, BookingRequest
from receipt_client import receipt_client, ReceiptValidationRequest


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")


# Define Models
class StatusCheck(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class StatusCheckCreate(BaseModel):
    client_name: str

# Add your routes to the router instead of directly to app
@api_router.get("/")
async def root():
    return {"message": "Hello World"}

@api_router.post("/status", response_model=StatusCheck)
async def create_status_check(input: StatusCheckCreate):
    status_dict = input.dict()
    status_obj = StatusCheck(**status_dict)
    _ = await db.status_checks.insert_one(status_obj.dict())
    return status_obj

@api_router.get("/status", response_model=List[StatusCheck])
async def get_status_checks():
    status_checks = await db.status_checks.find().to_list(1000)
    return [StatusCheck(**status_check) for status_check in status_checks]

# Calendar service integration endpoints
@api_router.get("/calendar/health")
async def check_calendar_service():
    """Check if calendar service is healthy"""
    health = await calendar_client.health_check()
    if health:
        return {
            "calendar_service": "healthy",
            "status": health.dict()
        }
    else:
        return {
            "calendar_service": "unavailable",
            "status": None
        }

@api_router.get("/calendar/slots")
async def get_calendar_slots(
    hub_id: str,
    date: str,
    duration_minutes: Optional[int] = None
):
    """Get available slots from calendar service"""
    try:
        hub_uuid = uuid.UUID(hub_id)
        slots = await calendar_client.get_available_slots(
            hub_id=hub_uuid,
            date=date,
            duration_minutes=duration_minutes
        )
        return {
            "hub_id": hub_id,
            "date": date,
            "slots": [slot.dict() for slot in slots],
            "total_slots": len(slots)
        }
    except Exception as e:
        logger.error(f"Error getting calendar slots: {e}")
        return {"error": str(e)}

@api_router.post("/calendar/bookings")
async def create_calendar_booking(booking_data: dict):
    """Create a booking via calendar service"""
    try:
        booking_request = BookingRequest(
            slot_id=uuid.UUID(booking_data["slot_id"]),
            candidate_id=uuid.UUID(booking_data["candidate_id"]),
            contact_email=booking_data["contact_email"],
            contact_phone=booking_data.get("contact_phone"),
            special_requirements=booking_data.get("special_requirements")
        )
        
        result = await calendar_client.create_booking(booking_request)
        return {
            "success": True,
            "booking_id": str(result.booking.id),
            "booking_reference": result.booking.booking_reference,
            "lock_expires_at": result.lock_expires_at.isoformat(),
            "message": result.message,
            "status": result.booking.status
        }
    except Exception as e:
        logger.error(f"Error creating calendar booking: {e}")
        return {"success": False, "error": str(e)}

@api_router.get("/calendar/bookings/{booking_id}")
async def get_calendar_booking(booking_id: str):
    """Get booking details from calendar service"""
    try:
        booking_uuid = uuid.UUID(booking_id)
        booking = await calendar_client.get_booking(booking_uuid)
        if booking:
            return {
                "found": True,
                "booking": booking.dict()
            }
        else:
            return {
                "found": False,
                "booking": None
            }
    except Exception as e:
        logger.error(f"Error getting calendar booking: {e}")
        return {"error": str(e)}

# Receipt service integration endpoints
@api_router.get("/receipts/health")
async def check_receipt_service():
    """Check if receipt service is healthy"""
    health = await receipt_client.health_check()
    if health:
        return {
            "receipt_service": "healthy",
            "status": health
        }
    else:
        return {
            "receipt_service": "unavailable",
            "status": None
        }

@api_router.post("/receipts/validate")
async def validate_receipt(receipt_data: dict):
    """Validate a receipt via receipt service"""
    try:
        # Parse the receipt data
        validation_request = ReceiptValidationRequest(
            receipt_no=receipt_data["receipt_no"],
            issue_date=receipt_data["issue_date"],
            location=receipt_data["location"],
            amount=receipt_data["amount"]
        )
        
        result = await receipt_client.validate_receipt(validation_request)
        if result:
            return {
                "success": result.success,
                "receipt_no": result.receipt_no,
                "message": result.message,
                "receipt": result.receipt,
                "validation_timestamp": result.validation_timestamp.isoformat(),
                "http_status": 200 if result.success else 409
            }
        else:
            return {
                "success": False,
                "error": "Receipt service unavailable"
            }
    except Exception as e:
        logger.error(f"Error validating receipt: {e}")
        return {
            "success": False,
            "error": str(e)
        }

@api_router.get("/receipts/{receipt_no}")
async def get_receipt(receipt_no: str):
    """Get receipt details from receipt service"""
    try:
        receipt = await receipt_client.get_receipt(receipt_no)
        if receipt:
            return {
                "found": True,
                "receipt": receipt
            }
        else:
            return {
                "found": False,
                "receipt": None
            }
    except Exception as e:
        logger.error(f"Error getting receipt: {e}")
        return {"error": str(e)}

@api_router.get("/receipts/statistics")
async def get_receipt_statistics():
    """Get receipt validation statistics from receipt service"""
    try:
        stats = await receipt_client.get_statistics()
        if stats:
            return stats
        else:
            return {
                "success": False,
                "error": "Receipt service unavailable"
            }
    except Exception as e:
        logger.error(f"Error getting receipt statistics: {e}")
        return {"error": str(e)}

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
