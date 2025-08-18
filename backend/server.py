from fastapi import FastAPI, APIRouter, HTTPException, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Literal, Dict, Any
import uuid
from datetime import datetime
from calendar_client import calendar_client, BookingRequest
from receipt_client import receipt_client, ReceiptValidationRequest
from registration_routes import router as registration_router
from test_engine_client import test_engine_client
from certificate_client import certificate_client
from special_admin_client import special_admin_client
from audit_client import audit_client, OverrideRequest as AuditOverrideRequest

# Configure logging early
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

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

# Checklist Models
class ChecklistItem(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    category: str
    description: str
    checked: bool = False
    breach_type: Optional[Literal["minor", "major"]] = None
    notes: Optional[str] = ""
    timestamp: Optional[datetime] = Field(default_factory=datetime.utcnow)

class Checklist(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    driver_record_id: str
    examiner_id: str
    test_type: Literal["Class B", "Class C", "PPV", "Special"]
    test_category: Literal["Yard", "Road"]
    status: Literal["in_progress", "completed", "submitted"] = "in_progress"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    synced: bool = False
    items: List[ChecklistItem] = []
    
    # Summary fields for quick assessment
    total_items: int = 0
    checked_items: int = 0
    minor_breaches: int = 0
    major_breaches: int = 0
    pass_fail_status: Optional[Literal["pass", "fail"]] = None

class ChecklistCreate(BaseModel):
    driver_record_id: str
    examiner_id: str
    test_type: Literal["Class B", "Class C", "PPV", "Special"]
    test_category: Literal["Yard", "Road"]
    items: Optional[List[ChecklistItem]] = []

class ChecklistUpdate(BaseModel):
    status: Optional[Literal["in_progress", "completed", "submitted"]] = None
    items: Optional[List[ChecklistItem]] = None
    synced: Optional[bool] = None

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

# Special Admin service integration endpoints
@api_router.get("/special-admin/health")
async def check_special_admin_service():
    """Check if special admin service is healthy"""
    health = await special_admin_client.health_check()
    return {
        "special_admin_service": health.get("status", "unavailable") if health else "unavailable",
        "status": health
    }

@api_router.get("/special-admin/config")
async def get_special_admin_config():
    """Get special admin configuration"""
    try:
        config = await special_admin_client.get_config()
        return config if config else {"error": "Special admin service unavailable"}
    except Exception as e:
        logger.error(f"Error getting special admin config: {e}")
        return {"error": str(e)}

@api_router.get("/special-admin/statistics")
async def get_special_admin_statistics():
    """Get special admin statistics"""
    try:
        stats = await special_admin_client.get_statistics()
        return stats if stats else {"error": "Special admin service unavailable"}
    except Exception as e:
        logger.error(f"Error getting special admin statistics: {e}")
        return {"error": str(e)}

# Special Test Types endpoints
@api_router.get("/special-types")
async def get_special_types():
    """Get all special test types"""
    try:
        types = await special_admin_client.get_special_types()
        return {"success": True, "data": types} if types else {"success": False, "error": "Service unavailable"}
    except Exception as e:
        logger.error(f"Error getting special types: {e}")
        return {"success": False, "error": str(e)}

@api_router.post("/special-types")
async def create_special_type(type_data: dict):
    """Create a new special test type"""
    try:
        result = await special_admin_client.create_special_type(type_data)
        return result
    except Exception as e:
        logger.error(f"Error creating special type: {e}")
        return {"success": False, "error": str(e)}

@api_router.get("/special-types/{type_id}")
async def get_special_type(type_id: str):
    """Get a specific special test type"""
    try:
        type_uuid = uuid.UUID(type_id)
        result = await special_admin_client.get_special_type(type_uuid)
        return result
    except Exception as e:
        logger.error(f"Error getting special type: {e}")
        return {"success": False, "error": str(e)}

# Certificate Templates endpoints
@api_router.get("/templates")
async def get_certificate_templates(template_type: str = None):
    """Get certificate templates"""
    try:
        templates = await special_admin_client.get_templates(template_type)
        return {"success": True, "data": templates} if templates else {"success": False, "error": "Service unavailable"}
    except Exception as e:
        logger.error(f"Error getting templates: {e}")
        return {"success": False, "error": str(e)}

@api_router.post("/templates")
async def create_certificate_template(template_data: dict):
    """Create a new certificate template"""
    try:
        result = await special_admin_client.create_template(template_data)
        return result
    except Exception as e:
        logger.error(f"Error creating template: {e}")
        return {"success": False, "error": str(e)}

@api_router.get("/templates/{template_id}/preview")
async def get_template_preview(template_id: str):
    """Get template preview"""
    try:
        template_uuid = uuid.UUID(template_id)
        result = await special_admin_client.get_template_preview(template_uuid)
        return result
    except Exception as e:
        logger.error(f"Error getting template preview: {e}")
        return {"success": False, "error": str(e)}

@api_router.post("/templates/preview")
async def preview_template_content(preview_data: dict):
    """Generate preview for template content"""
    try:
        result = await special_admin_client.preview_template_content(preview_data)
        return result
    except Exception as e:
        logger.error(f"Error generating template preview: {e}")
        return {"success": False, "error": str(e)}

@api_router.get("/templates/config/default")
async def get_default_template_config():
    """Get default template configuration"""
    try:
        result = await special_admin_client.get_default_template_config()
        return result
    except Exception as e:
        logger.error(f"Error getting default template config: {e}")
        return {"success": False, "error": str(e)}

# Question Modules endpoints
@api_router.get("/question-modules")
async def get_question_modules():
    """Get all question modules"""
    try:
        modules = await special_admin_client.get_modules()
        return {"success": True, "data": modules} if modules else {"success": False, "error": "Service unavailable"}
    except Exception as e:
        logger.error(f"Error getting question modules: {e}")
        return {"success": False, "error": str(e)}

@api_router.post("/question-modules")
async def create_question_module(module_data: dict):
    """Create a new question module"""
    try:
        result = await special_admin_client.create_module(module_data)
        return result
    except Exception as e:
        logger.error(f"Error creating question module: {e}")
        return {"success": False, "error": str(e)}

@api_router.post("/questions/upload")
async def upload_questions(upload_data: dict):
    """Upload questions from CSV"""
    try:
        result = await special_admin_client.upload_questions_csv(
            upload_data["module_code"],
            upload_data["created_by"], 
            upload_data["csv_data"]
        )
        return result
    except Exception as e:
        logger.error(f"Error uploading questions: {e}")
        return {"success": False, "error": str(e)}

@api_router.get("/questions/template")
async def get_questions_csv_template():
    """Get CSV template for question upload"""
    try:
        result = await special_admin_client.get_csv_template()
        return result
    except Exception as e:
        logger.error(f"Error getting CSV template: {e}")
        return {"success": False, "error": str(e)}

# Checklist Management Endpoints
def generate_default_checklist_items(test_type: str, test_category: str) -> List[ChecklistItem]:
    """Generate default checklist items based on test type and category"""
    items = []
    
    # Common pre-inspection items for all tests
    pre_inspection_items = [
        "Vehicle exterior condition check",
        "Mirrors properly adjusted",
        "Seat and steering wheel adjustment",
        "Safety equipment present and functional",
        "Documents and identification verified"
    ]
    
    # Yard test specific items
    yard_items = [
        "Reverse parking maneuver",
        "Three-point turn execution",
        "Hill start procedure",
        "Emergency stop demonstration",
        "Parallel parking (if applicable)"
    ]
    
    # Road test specific items  
    road_items = [
        "Traffic observation and awareness",
        "Signal usage and timing",
        "Lane discipline maintenance",
        "Speed control and adaptation",
        "Hazard perception and response",
        "Junction approach and execution",
        "Overtaking procedure (if applicable)",
        "Roundabout navigation"
    ]
    
    # Class-specific items
    if test_type in ["Class C"]:
        commercial_items = [
            "Commercial vehicle pre-trip inspection",
            "Load securement verification",
            "Air brake system check",
            "Coupling/uncoupling procedure (if applicable)"
        ]
        pre_inspection_items.extend(commercial_items)
    
    if test_type == "PPV":
        ppv_items = [
            "Passenger safety equipment check",
            "Emergency exit operation",
            "Wheelchair accessibility features",
            "First aid kit presence and location"
        ]
        pre_inspection_items.extend(ppv_items)
    
    # Generate ChecklistItem objects
    category_items = {
        "Pre-inspection": pre_inspection_items,
        "Yard Maneuvers": yard_items if test_category == "Yard" else [],
        "Road Driving": road_items if test_category == "Road" else []
    }
    
    for category, descriptions in category_items.items():
        for desc in descriptions:
            if desc:  # Only add non-empty descriptions
                items.append(ChecklistItem(
                    category=category,
                    description=desc
                ))
    
    return items

def calculate_checklist_summary(checklist: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate summary statistics for a checklist"""
    items = checklist.get("items", [])
    
    total_items = len(items)
    checked_items = sum(1 for item in items if item.get("checked", False))
    minor_breaches = sum(1 for item in items if item.get("breach_type") == "minor")
    major_breaches = sum(1 for item in items if item.get("breach_type") == "major")
    
    # Determine pass/fail status
    pass_fail_status = None
    if checklist.get("status") == "completed":
        # Fail if any major breaches, or too many minor breaches
        if major_breaches > 0:
            pass_fail_status = "fail"
        elif minor_breaches > 3:  # Allow up to 3 minor breaches
            pass_fail_status = "fail"  
        else:
            pass_fail_status = "pass"
    
    checklist.update({
        "total_items": total_items,
        "checked_items": checked_items,
        "minor_breaches": minor_breaches,
        "major_breaches": major_breaches,
        "pass_fail_status": pass_fail_status
    })
    
    return checklist

@api_router.post("/checklists", response_model=Checklist)
async def create_checklist(checklist_data: ChecklistCreate):
    """Create a new checklist for driver examination"""
    try:
        checklist_dict = checklist_data.dict()
        
        # Generate default items if none provided
        if not checklist_dict.get("items"):
            checklist_dict["items"] = [
                item.dict() for item in generate_default_checklist_items(
                    checklist_dict["test_type"], 
                    checklist_dict["test_category"]
                )
            ]
        
        # Create the checklist object
        checklist = Checklist(**checklist_dict)
        checklist_with_summary = calculate_checklist_summary(checklist.dict())
        
        # Insert into MongoDB
        result = await db.checklists.insert_one(checklist_with_summary)
        checklist_with_summary["_id"] = str(result.inserted_id)
        
        logger.info(f"Created checklist {checklist.id} for driver {checklist.driver_record_id}")
        return Checklist(**checklist_with_summary)
        
    except Exception as e:
        logger.error(f"Error creating checklist: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/checklists/unsynced")
async def get_unsynced_checklists():
    """Get all checklists that need to be synced"""
    try:
        checklists = await db.checklists.find({"synced": False}).to_list(1000)
        
        # Remove MongoDB _ids and calculate summaries
        processed_checklists = []
        for checklist in checklists:
            checklist.pop("_id", None)
            checklist_with_summary = calculate_checklist_summary(checklist)
            processed_checklists.append(checklist_with_summary)
        
        return {
            "success": True,
            "data": processed_checklists,
            "count": len(processed_checklists)
        }
        
    except Exception as e:
        logger.error(f"Error getting unsynced checklists: {e}")
        return {"success": False, "error": str(e)}

@api_router.get("/checklists/{driver_record_id}")
async def get_checklist_by_driver(driver_record_id: str):
    """Get checklist for a specific driver record"""
    try:
        checklist = await db.checklists.find_one({"driver_record_id": driver_record_id})
        
        if not checklist:
            return {"success": False, "error": "Checklist not found"}
        
        # Remove MongoDB _id and calculate summary
        checklist.pop("_id", None)
        checklist_with_summary = calculate_checklist_summary(checklist)
        
        return {
            "success": True,
            "data": checklist_with_summary
        }
        
    except Exception as e:
        logger.error(f"Error getting checklist for driver {driver_record_id}: {e}")
        return {"success": False, "error": str(e)}

@api_router.put("/checklists/{checklist_id}")
async def update_checklist(checklist_id: str, update_data: ChecklistUpdate):
    """Update an existing checklist"""
    try:
        update_dict = {k: v for k, v in update_data.dict().items() if v is not None}
        update_dict["updated_at"] = datetime.utcnow()
        
        # If items are being updated, convert to dict format
        if "items" in update_dict and update_dict["items"]:
            update_dict["items"] = [
                item.dict() if hasattr(item, 'dict') else item 
                for item in update_dict["items"]
            ]
        
        result = await db.checklists.update_one(
            {"id": checklist_id},
            {"$set": update_dict}
        )
        
        if result.matched_count == 0:
            return {"success": False, "error": "Checklist not found"}
        
        # Get updated checklist
        updated_checklist = await db.checklists.find_one({"id": checklist_id})
        if updated_checklist:
            updated_checklist.pop("_id", None)
            checklist_with_summary = calculate_checklist_summary(updated_checklist)
            
            logger.info(f"Updated checklist {checklist_id}")
            return {
                "success": True,
                "data": checklist_with_summary
            }
        
        return {"success": False, "error": "Failed to retrieve updated checklist"}
        
    except Exception as e:
        logger.error(f"Error updating checklist {checklist_id}: {e}")
        return {"success": False, "error": str(e)}

@api_router.post("/checklists/{checklist_id}/sync")
async def mark_checklist_synced(checklist_id: str):
    """Mark a checklist as synced"""
    try:
        result = await db.checklists.update_one(
            {"id": checklist_id},
            {"$set": {"synced": True, "updated_at": datetime.utcnow()}}
        )
        
        if result.matched_count == 0:
            return {"success": False, "error": "Checklist not found"}
        
        logger.info(f"Marked checklist {checklist_id} as synced")
        return {"success": True, "message": "Checklist marked as synced"}
        
    except Exception as e:
        logger.error(f"Error marking checklist {checklist_id} as synced: {e}")
        return {"success": False, "error": str(e)}

@api_router.get("/checklists")
async def get_all_checklists(
    limit: int = 50,
    skip: int = 0,
    examiner_id: Optional[str] = None,
    test_type: Optional[str] = None,
    status: Optional[str] = None
):
    """Get checklists with optional filtering"""
    try:
        # Build filter query
        filter_query = {}
        if examiner_id:
            filter_query["examiner_id"] = examiner_id
        if test_type:
            filter_query["test_type"] = test_type
        if status:
            filter_query["status"] = status
        
        # Get checklists with pagination
        checklists = await db.checklists.find(filter_query).skip(skip).limit(limit).to_list(limit)
        
        # Remove MongoDB _ids and calculate summaries
        processed_checklists = []
        for checklist in checklists:
            checklist.pop("_id", None)
            checklist_with_summary = calculate_checklist_summary(checklist)
            processed_checklists.append(checklist_with_summary)
        
        # Get total count
        total_count = await db.checklists.count_documents(filter_query)
        
        return {
            "success": True,
            "data": processed_checklists,
            "pagination": {
                "total": total_count,
                "limit": limit,
                "skip": skip,
                "has_more": skip + len(processed_checklists) < total_count
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting checklists: {e}")
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

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
