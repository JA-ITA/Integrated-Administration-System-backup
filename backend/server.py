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
from registration_routes import router as registration_router
from test_engine_client import test_engine_client
from certificate_client import certificate_client


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

# Test Engine service integration endpoints
@api_router.get("/test-engine/health")
async def check_test_engine_service():
    """Check if test engine service is healthy"""
    health = await test_engine_client.health_check()
    return {
        "test_engine_service": health.get("status", "unavailable"),
        "status": health
    }

@api_router.get("/test-engine/config")
async def get_test_engine_config():
    """Get test configuration from test engine service"""
    try:
        config = await test_engine_client.get_config()
        return config
    except Exception as e:
        logger.error(f"Error getting test engine config: {e}")
        return {"error": str(e)}

@api_router.post("/test-engine/tests/start")
async def start_test(test_data: dict):
    """Start a new test via test engine service"""
    try:
        driver_record_id = uuid.UUID(test_data["driver_record_id"])
        module = test_data["module"]
        
        result = await test_engine_client.start_test(driver_record_id, module)
        return {
            "success": True,
            "test_id": result["test_id"],
            "questions": result["questions"],
            "time_limit_minutes": result["time_limit_minutes"],
            "start_time": result["start_time"],
            "expires_at": result["expires_at"]
        }
    except Exception as e:
        logger.error(f"Error starting test: {e}")
        return {"success": False, "error": str(e)}

@api_router.post("/test-engine/tests/{test_id}/submit")
async def submit_test(test_id: str, submission_data: dict):
    """Submit test answers via test engine service"""
    try:
        test_uuid = uuid.UUID(test_id)
        answers = submission_data["answers"]
        
        result = await test_engine_client.submit_test(test_uuid, answers)
        return {
            "success": True,
            "test_id": result["test_id"],
            "score": result["score"],
            "passed": result["passed"],
            "correct_answers": result["correct_answers"],
            "total_questions": result["total_questions"],
            "submitted_at": result["submitted_at"]
        }
    except Exception as e:
        logger.error(f"Error submitting test: {e}")
        return {"success": False, "error": str(e)}

@api_router.get("/test-engine/tests/{test_id}/status")
async def get_test_status(test_id: str):
    """Get test status and time remaining"""
    try:
        test_uuid = uuid.UUID(test_id)
        status = await test_engine_client.get_test_status(test_uuid)
        return status
    except Exception as e:
        logger.error(f"Error getting test status: {e}")
        return {"error": str(e)}

@api_router.get("/test-engine/statistics")
async def get_test_engine_statistics():
    """Get test statistics from test engine service"""
    try:
        stats = await test_engine_client.get_statistics()
        return stats
    except Exception as e:
        logger.error(f"Error getting test engine statistics: {e}")
        return {"error": str(e)}

# Certificate service integration endpoints
@api_router.get("/certificates/health")
async def check_certificate_service():
    """Check if certificate service is healthy"""
    health = await certificate_client.health_check()
    return {
        "certificate_service": health.get("status", "unavailable"),
        "status": health
    }

@api_router.post("/certificates/generate")
async def generate_certificate(certificate_data: dict):
    """Generate a new certificate via certificate service"""
    try:
        driver_record_id = uuid.UUID(certificate_data["driver_record_id"])
        
        result = await certificate_client.generate_certificate(driver_record_id)
        if result["success"]:
            return {
                "success": True,
                "certificate_id": result["data"]["certificate_id"],
                "download_url": result["data"]["download_url"],
                "verification_token": result["data"]["verification_token"],
                "qr_code": result["data"].get("qr_code"),
                "issue_date": result["data"]["issue_date"],
                "expiry_date": result["data"].get("expiry_date"),
                "metadata": result["data"]["metadata"]
            }
        else:
            return {
                "success": False,
                "error": result["error"],
                "status_code": result.get("status_code", 500)
            }
    except Exception as e:
        logger.error(f"Error generating certificate: {e}")
        return {"success": False, "error": str(e)}

@api_router.get("/certificates/{driver_record_id}/download")
async def download_certificate_by_driver_record(driver_record_id: str):
    """Get certificate download URL by driver record ID"""
    try:
        driver_uuid = uuid.UUID(driver_record_id)
        
        result = await certificate_client.download_certificate_by_driver_record(driver_uuid)
        if result["success"]:
            return {
                "success": True,
                "download_url": result["download_url"]
            }
        else:
            return {
                "success": False,
                "error": result["error"],
                "status_code": result.get("status_code", 500)
            }
    except Exception as e:
        logger.error(f"Error getting certificate download URL: {e}")
        return {"success": False, "error": str(e)}

@api_router.get("/certificates/download/{certificate_id}")
async def download_certificate_by_id(certificate_id: str):
    """Get certificate download URL by certificate ID"""
    try:
        cert_uuid = uuid.UUID(certificate_id)
        
        result = await certificate_client.download_certificate_by_id(cert_uuid)
        if result["success"]:
            return {
                "success": True,
                "download_url": result["download_url"]
            }
        else:
            return {
                "success": False,
                "error": result["error"],
                "status_code": result.get("status_code", 500)
            }
    except Exception as e:
        logger.error(f"Error getting certificate download URL: {e}")
        return {"success": False, "error": str(e)}

@api_router.get("/certificates/verify/{verification_token}")
async def verify_certificate(verification_token: str):
    """Verify certificate authenticity"""
    try:
        result = await certificate_client.verify_certificate(verification_token)
        if result["success"]:
            return {
                "success": True,
                "verification": result["data"]
            }
        else:
            return {
                "success": False,
                "error": result["error"],
                "status_code": result.get("status_code", 500)
            }
    except Exception as e:
        logger.error(f"Error verifying certificate: {e}")
        return {"success": False, "error": str(e)}

@api_router.get("/certificates/status/{certificate_id}")
async def get_certificate_status(certificate_id: str):
    """Get certificate status and metadata"""
    try:
        cert_uuid = uuid.UUID(certificate_id)
        
        result = await certificate_client.get_certificate_status(cert_uuid)
        if result["success"]:
            return {
                "success": True,
                "certificate": result["data"]
            }
        else:
            return {
                "success": False,
                "error": result["error"],
                "status_code": result.get("status_code", 500)
            }
    except Exception as e:
        logger.error(f"Error getting certificate status: {e}")
        return {"success": False, "error": str(e)}

@api_router.get("/certificates/driver/{driver_record_id}")
async def get_driver_certificates(driver_record_id: str):
    """Get all certificates for a driver record"""
    try:
        driver_uuid = uuid.UUID(driver_record_id)
        
        result = await certificate_client.get_driver_certificates(driver_uuid)
        if result["success"]:
            return {
                "success": True,
                "data": result["data"]
            }
        else:
            return {
                "success": False,
                "error": result["error"],
                "status_code": result.get("status_code", 500)
            }
    except Exception as e:
        logger.error(f"Error getting driver certificates: {e}")
        return {"success": False, "error": str(e)}

# Include the router in the main app
app.include_router(api_router)

# Include registration routes
app.include_router(registration_router, prefix="/api")

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
