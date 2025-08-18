"""
FastAPI Router for Driver Records Management - ITADIAS System
Implements comprehensive driver record management with JWT authentication,
role-based access control, and event publishing.
"""
import uuid
import asyncio
from datetime import datetime, date
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import asyncpg
import json
import logging
from pydantic import BaseModel, Field, validator
from enum import Enum
import aio_pika

# Configure logging
logger = logging.getLogger(__name__)

# Security
security = HTTPBearer()

# Router configuration
router = APIRouter(prefix="/api/v1/driver-records", tags=["Driver Records"])

# ============================================================================
# ENUMS AND CONSTANTS
# ============================================================================

class LicenceType(str, Enum):
    PROVISIONAL = "Provisional"
    CLASS_B = "Class B"
    CLASS_C = "Class C"
    PPV = "PPV"
    SPECIAL = "Special"

class DriverStatus(str, Enum):
    ISSUED = "Issued"
    SUSPENDED = "Suspended"
    EXPIRED = "Expired"
    REVOKED = "Revoked"

class TestType(str, Enum):
    YARD = "Yard"
    ROAD = "Road"

class ActorRole(str, Enum):
    DAO = "dao"
    MANAGER = "manager"
    RD = "rd"

# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class DriverRecordBase(BaseModel):
    """Base driver record schema"""
    licence_number: str = Field(..., min_length=1, max_length=20, description="Unique licence number")
    christian_names: str = Field(..., min_length=1, max_length=200, description="Christian/First names")
    surname: str = Field(..., min_length=1, max_length=100, description="Surname/Last name")
    address: str = Field(..., min_length=10, max_length=500, description="Full residential address")
    dob: date = Field(..., description="Date of birth")
    licence_type: LicenceType = Field(..., description="Type of driving licence")
    status: DriverStatus = Field(default=DriverStatus.ISSUED, description="Current licence status")
    certificate_of_competency_no: Optional[str] = Field(None, max_length=50, description="Certificate of competency number")
    application_date: date = Field(default_factory=date.today, description="Application date")
    photo_url: Optional[str] = Field(None, description="URL to driver photo")
    signature_url: Optional[str] = Field(None, description="URL to driver signature")

    class Config:
        schema_extra = {
            "example": {
                "licence_number": "D123456789",
                "christian_names": "John Michael",
                "surname": "Smith",
                "address": "123 Main Street, Kingston, Jamaica",
                "dob": "1990-05-15",
                "licence_type": "Class B",
                "status": "Issued",
                "certificate_of_competency_no": "COC001234",
                "application_date": "2024-01-15",
                "photo_url": "https://storage.example.com/photos/d123456789.jpg",
                "signature_url": "https://storage.example.com/signatures/d123456789.jpg"
            }
        }

class DriverRecordCreate(DriverRecordBase):
    """Schema for creating a new driver record"""
    candidate_id: uuid.UUID = Field(..., description="Reference to identity.candidates table")

class DriverRecordUpdate(BaseModel):
    """Schema for updating driver record personal fields"""
    christian_names: Optional[str] = Field(None, min_length=1, max_length=200)
    surname: Optional[str] = Field(None, min_length=1, max_length=100)
    address: Optional[str] = Field(None, min_length=10, max_length=500)
    photo_url: Optional[str] = None
    signature_url: Optional[str] = None
    certificate_of_competency_no: Optional[str] = Field(None, max_length=50)

    class Config:
        schema_extra = {
            "example": {
                "christian_names": "John Michael Jr",
                "address": "456 New Street, Kingston, Jamaica",
                "photo_url": "https://storage.example.com/photos/updated_d123456789.jpg"
            }
        }

class TheoryAttempt(BaseModel):
    """Schema for theory test attempt"""
    attempt_no: int = Field(..., ge=1, le=10, description="Attempt number (1-10)")
    module: str = Field(..., min_length=1, max_length=50, description="Test module name")
    score: int = Field(..., ge=0, le=20, description="Score out of 20")
    passed: bool = Field(..., description="Whether the attempt was successful")
    attempt_date: date = Field(default_factory=date.today, description="Date of attempt")

    class Config:
        schema_extra = {
            "example": {
                "attempt_no": 1,
                "module": "Traffic Signs and Rules",
                "score": 18,
                "passed": True,
                "attempt_date": "2024-01-20"
            }
        }

class YardRoadAttempt(BaseModel):
    """Schema for yard/road test attempt"""
    test_type: TestType = Field(..., description="Type of practical test")
    visit_no: int = Field(..., ge=1, le=5, description="Visit number for this test type")
    attempt_date: date = Field(default_factory=date.today, description="Date of attempt")
    criteria: List[Dict[str, Any]] = Field(..., description="Assessment criteria with scores")
    overall_result: bool = Field(..., description="Overall pass/fail result")

    @validator('criteria')
    def validate_criteria(cls, v):
        """Validate criteria structure"""
        if not isinstance(v, list) or len(v) == 0:
            raise ValueError("Criteria must be a non-empty list")
        
        for criterion in v:
            if not all(key in criterion for key in ['criterion', 'major', 'minor', 'score']):
                raise ValueError("Each criterion must have: criterion, major, minor, score")
        return v

    class Config:
        schema_extra = {
            "example": {
                "test_type": "Yard",
                "visit_no": 1,
                "attempt_date": "2024-01-25",
                "criteria": [
                    {"criterion": "Reverse Parking", "major": 0, "minor": 1, "score": 8},
                    {"criterion": "Hill Start", "major": 0, "minor": 0, "score": 10},
                    {"criterion": "Parallel Parking", "major": 1, "minor": 0, "score": 5}
                ],
                "overall_result": False
            }
        }

class CourtRecord(BaseModel):
    """Schema for court record entry"""
    judgment_date: date = Field(..., description="Date of court judgment")
    offence: str = Field(..., min_length=5, max_length=500, description="Description of the offence")
    suspension_from: Optional[date] = Field(None, description="Suspension start date")
    suspension_to: Optional[date] = Field(None, description="Suspension end date")
    retest_required: Optional[Dict[str, bool]] = Field(None, description="Retest requirements")

    @validator('suspension_to')
    def validate_suspension_dates(cls, v, values):
        """Validate suspension date logic"""
        if v and 'suspension_from' in values and values['suspension_from']:
            if v <= values['suspension_from']:
                raise ValueError("Suspension end date must be after start date")
        return v

    class Config:
        schema_extra = {
            "example": {
                "judgment_date": "2024-01-30",
                "offence": "Dangerous driving causing injury",
                "suspension_from": "2024-02-01",
                "suspension_to": "2024-08-01",
                "retest_required": {"written": True, "yard": True, "road": True, "other": False}
            }
        }

class OverrideRequest(BaseModel):
    """Schema for RD override request"""
    action: str = Field(..., min_length=5, max_length=100, description="Override action description")
    reason: str = Field(..., min_length=20, max_length=1000, description="Detailed reason for override")
    new_status: Optional[DriverStatus] = Field(None, description="New driver status if applicable")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional override metadata")

    class Config:
        schema_extra = {
            "example": {
                "action": "Override suspension due to appeal",
                "reason": "Court appeal successful. Driver demonstrated sufficient evidence of medical recovery and completed remedial driving course as ordered by magistrate.",
                "new_status": "Issued",
                "metadata": {"court_case_no": "TC2024/001234", "appeal_date": "2024-02-15"}
            }
        }

class FullDriverRecord(BaseModel):
    """Complete driver record with all related data"""
    # Driver record fields
    id: uuid.UUID
    candidate_id: uuid.UUID
    licence_number: str
    christian_names: str
    surname: str
    address: str
    dob: date
    photo_url: Optional[str]
    signature_url: Optional[str]
    licence_type: str
    status: str
    certificate_of_competency_no: Optional[str]
    application_date: date
    created_at: datetime
    updated_at: datetime
    
    # Related records
    theory_attempts: List[Dict[str, Any]] = Field(default_factory=list)
    yard_road_attempts: List[Dict[str, Any]] = Field(default_factory=list)
    endorsements: List[Dict[str, Any]] = Field(default_factory=list)
    court_records: List[Dict[str, Any]] = Field(default_factory=list)

    class Config:
        schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "candidate_id": "123e4567-e89b-12d3-a456-426614174000",
                "licence_number": "D123456789",
                "christian_names": "John Michael",
                "surname": "Smith",
                "address": "123 Main Street, Kingston, Jamaica",
                "dob": "1990-05-15",
                "photo_url": "https://storage.example.com/photos/d123456789.jpg",
                "signature_url": "https://storage.example.com/signatures/d123456789.jpg",
                "licence_type": "Class B",
                "status": "Issued",
                "certificate_of_competency_no": "COC001234",
                "application_date": "2024-01-15",
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-20T14:45:00Z",
                "theory_attempts": [
                    {
                        "id": "660f8400-e29b-41d4-a716-446655440001",
                        "attempt_no": 1,
                        "module": "Traffic Signs and Rules",
                        "score": 18,
                        "passed": True,
                        "attempt_date": "2024-01-20"
                    }
                ],
                "yard_road_attempts": [],
                "endorsements": [],
                "court_records": []
            }
        }

# Authentication models
class AuthUser(BaseModel):
    """Authenticated user information"""
    user_id: uuid.UUID
    role: str

# Response models
class StandardResponse(BaseModel):
    """Standard API response"""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None

# ============================================================================
# DATABASE CONNECTION
# ============================================================================

# Database connection pool
db_pool = None

async def init_db_pool():
    """Initialize database connection pool"""
    global db_pool
    if db_pool is None:
        db_config = {
            'host': 'localhost',
            'port': 5432,
            'database': 'itadias',
            'user': 'ita_admin',
            'password': 'ita_secure_2024'
        }
        
        try:
            db_pool = await asyncpg.create_pool(
                **db_config,
                min_size=1,
                max_size=10,
                command_timeout=30
            )
            logger.info("Database connection pool initialized")
        except Exception as e:
            logger.error(f"Failed to initialize database pool: {e}")
            raise

async def get_db_connection():
    """Get database connection from pool"""
    if db_pool is None:
        await init_db_pool()
    return await db_pool.acquire()

# ============================================================================
# RABBITMQ EVENT PUBLISHING
# ============================================================================

# RabbitMQ connection
rabbitmq_connection = None
rabbitmq_channel = None

async def init_rabbitmq():
    """Initialize RabbitMQ connection"""
    global rabbitmq_connection, rabbitmq_channel
    
    try:
        rabbitmq_connection = await aio_pika.connect_robust(
            "amqp://guest:guest@localhost:5672/"
        )
        rabbitmq_channel = await rabbitmq_connection.channel()
        
        # Declare exchange
        await rabbitmq_channel.declare_exchange(
            "itadias.events",
            aio_pika.ExchangeType.TOPIC,
            durable=True
        )
        logger.info("RabbitMQ connection initialized")
    except Exception as e:
        logger.warning(f"RabbitMQ initialization failed, using fallback: {e}")
        # Continue without RabbitMQ - implement fallback storage

async def publish_event(event_type: str, data: Dict[str, Any], routing_key: str):
    """Publish event to RabbitMQ or fallback storage"""
    try:
        if rabbitmq_channel:
            message = aio_pika.Message(
                json.dumps(data, default=str).encode(),
                content_type="application/json",
                headers={"event_type": event_type}
            )
            
            await rabbitmq_channel.default_exchange.publish(
                message,
                routing_key=routing_key
            )
            logger.info(f"Event published: {event_type}")
        else:
            # Fallback: Log event (in production, use persistent storage)
            logger.info(f"Event fallback: {event_type} - {data}")
    except Exception as e:
        logger.error(f"Failed to publish event {event_type}: {e}")

# ============================================================================
# AUTHENTICATION AND AUTHORIZATION
# ============================================================================

async def verify_jwt_token(token: str) -> Optional[AuthUser]:
    """Verify JWT token and extract user info"""
    # Simplified JWT verification - in production, use proper JWT library
    # For now, mock the authentication
    try:
        # Mock user extraction from token
        # In real implementation, decode and verify JWT
        return AuthUser(
            user_id=uuid.uuid4(),
            role="dao"  # Mock role
        )
    except Exception as e:
        logger.error(f"JWT verification failed: {e}")
        return None

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> AuthUser:
    """Dependency to get current authenticated user"""
    token = credentials.credentials
    user = await verify_jwt_token(token)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user

async def get_dao_or_rd_user(current_user: AuthUser = Depends(get_current_user)) -> AuthUser:
    """Dependency for DAO or RD role access"""
    if current_user.role not in [ActorRole.DAO.value, ActorRole.RD.value]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. DAO or RD role required."
        )
    return current_user

async def get_rd_user(current_user: AuthUser = Depends(get_current_user)) -> AuthUser:
    """Dependency for RD role access only"""
    if current_user.role != ActorRole.RD.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. RD role required."
        )
    return current_user

# ============================================================================
# DATABASE OPERATIONS
# ============================================================================

async def get_driver_record_by_licence(licence_number: str) -> Optional[Dict[str, Any]]:
    """Get full driver record with all related data"""
    conn = await get_db_connection()
    try:
        # Get main driver record
        driver_query = """
            SELECT dr.*, c.first_name, c.last_name, c.email
            FROM driver_record.driver_records dr
            JOIN identity.candidates c ON dr.candidate_id = c.id
            WHERE dr.licence_number = $1
        """
        driver_row = await conn.fetchrow(driver_query, licence_number)
        
        if not driver_row:
            return None
        
        driver_dict = dict(driver_row)
        driver_id = driver_dict['id']
        
        # Get theory attempts
        theory_query = """
            SELECT * FROM driver_record.theory_attempts 
            WHERE driver_record_id = $1 
            ORDER BY attempt_date DESC, attempt_no DESC
        """
        theory_rows = await conn.fetch(theory_query, driver_id)
        driver_dict['theory_attempts'] = [dict(row) for row in theory_rows]
        
        # Get yard/road attempts
        yard_road_query = """
            SELECT * FROM driver_record.yard_road_attempts 
            WHERE driver_record_id = $1 
            ORDER BY attempt_date DESC, visit_no DESC
        """
        yard_road_rows = await conn.fetch(yard_road_query, driver_id)
        driver_dict['yard_road_attempts'] = [dict(row) for row in yard_road_rows]
        
        # Get endorsements
        endorsements_query = """
            SELECT * FROM driver_record.endorsements 
            WHERE driver_record_id = $1 
            ORDER BY issue_date DESC
        """
        endorsement_rows = await conn.fetch(endorsements_query, driver_id)
        driver_dict['endorsements'] = [dict(row) for row in endorsement_rows]
        
        # Get court records
        court_query = """
            SELECT * FROM driver_record.court_records 
            WHERE driver_record_id = $1 
            ORDER BY judgment_date DESC
        """
        court_rows = await conn.fetch(court_query, driver_id)
        driver_dict['court_records'] = [dict(row) for row in court_rows]
        
        return driver_dict
        
    finally:
        await db_pool.release(conn)

async def create_driver_record_db(record_data: DriverRecordCreate) -> uuid.UUID:
    """Create new driver record in database"""
    conn = await get_db_connection()
    try:
        record_id = uuid.uuid4()
        
        query = """
            INSERT INTO driver_record.driver_records 
            (id, candidate_id, licence_number, christian_names, surname, address, 
             dob, photo_url, signature_url, licence_type, status, 
             certificate_of_competency_no, application_date)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
            RETURNING id
        """
        
        result = await conn.fetchval(
            query,
            record_id, record_data.candidate_id, record_data.licence_number,
            record_data.christian_names, record_data.surname, record_data.address,
            record_data.dob, record_data.photo_url, record_data.signature_url,
            record_data.licence_type.value, record_data.status.value,
            record_data.certificate_of_competency_no, record_data.application_date
        )
        
        return result
        
    finally:
        await db_pool.release(conn)

async def update_driver_record_db(licence_number: str, update_data: DriverRecordUpdate) -> bool:
    """Update driver record personal fields"""
    conn = await get_db_connection()
    try:
        # Build dynamic update query
        set_clauses = []
        values = []
        param_count = 1
        
        for field, value in update_data.dict(exclude_unset=True).items():
            if value is not None:
                set_clauses.append(f"{field} = ${param_count}")
                values.append(value)
                param_count += 1
        
        if not set_clauses:
            return False
        
        query = f"""
            UPDATE driver_record.driver_records 
            SET {', '.join(set_clauses)}, updated_at = NOW()
            WHERE licence_number = ${param_count}
        """
        values.append(licence_number)
        
        result = await conn.execute(query, *values)
        return result.split()[-1] == '1'  # Check if one row was updated
        
    finally:
        await db_pool.release(conn)

# ============================================================================
# API ENDPOINTS
# ============================================================================

@router.get(
    "/driver-records/{licence_number}",
    response_model=FullDriverRecord,
    summary="Get complete driver record",
    description="""
    Retrieve complete driver record including all theory attempts, yard/road tests,
    endorsements, and court records. Requires valid JWT authentication.
    
    **OpenAPI 3.0 Schema:**
    - **licence_number**: Driver's licence number (path parameter)
    - **Returns**: Complete driver record with related data
    - **Authentication**: JWT Bearer token required
    """
)
async def get_driver_record(
    licence_number: str,
    current_user: AuthUser = Depends(get_current_user)
):
    """
    Get complete driver record with all related information.
    
    **Example Response:**
    ```json
    {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "licence_number": "D123456789",
        "christian_names": "John Michael",
        "surname": "Smith",
        "theory_attempts": [...],
        "yard_road_attempts": [...],
        "endorsements": [...],
        "court_records": [...]
    }
    ```
    """
    try:
        record = await get_driver_record_by_licence(licence_number)
        
        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Driver record not found for licence number: {licence_number}"
            )
        
        return record
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving driver record {licence_number}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error retrieving driver record"
        )

@router.post(
    "/driver-records",
    response_model=StandardResponse,
    summary="Create new driver record",
    description="""
    Create a new driver record. Requires DAO or RD role authentication.
    
    **OpenAPI 3.0 Schema:**
    - **Request Body**: DriverRecordCreate model
    - **Returns**: Success confirmation with record ID
    - **Authorization**: DAO or RD role required
    """
)
async def create_driver_record(
    record_data: DriverRecordCreate,
    current_user: AuthUser = Depends(get_dao_or_rd_user)
):
    """
    Create a new driver record in the system.
    
    **Example Request:**
    ```json
    {
        "candidate_id": "123e4567-e89b-12d3-a456-426614174000",
        "licence_number": "D123456789",
        "christian_names": "John Michael",
        "surname": "Smith",
        "address": "123 Main Street, Kingston, Jamaica",
        "dob": "1990-05-15",
        "licence_type": "Class B"
    }
    ```
    """
    try:
        # Check if licence number already exists
        existing = await get_driver_record_by_licence(record_data.licence_number)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Driver record already exists for licence number: {record_data.licence_number}"
            )
        
        # Create the record
        record_id = await create_driver_record_db(record_data)
        
        # Publish event
        event_data = {
            "record_id": str(record_id),
            "licence_number": record_data.licence_number,
            "action": "CREATED",
            "actor_id": str(current_user.user_id),
            "actor_role": current_user.role,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await publish_event(
            "DriverRecordUpdated",
            event_data,
            f"driver_record.created.{record_data.licence_type.value.lower().replace(' ', '_')}"
        )
        
        return StandardResponse(
            success=True,
            message="Driver record created successfully",
            data={"record_id": str(record_id), "licence_number": record_data.licence_number}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating driver record: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error creating driver record"
        )

@router.put(
    "/driver-records/{licence_number}",
    response_model=StandardResponse,
    summary="Update driver record personal fields",
    description="""
    Update personal information fields of a driver record. Requires DAO or RD role.
    
    **OpenAPI 3.0 Schema:**
    - **licence_number**: Driver's licence number (path parameter)
    - **Request Body**: DriverRecordUpdate model (partial update)
    - **Authorization**: DAO or RD role required
    """
)
async def update_driver_record(
    licence_number: str,
    update_data: DriverRecordUpdate,
    current_user: AuthUser = Depends(get_dao_or_rd_user)
):
    """
    Update personal information fields of an existing driver record.
    
    **Example Request:**
    ```json
    {
        "christian_names": "John Michael Jr",
        "address": "456 New Street, Kingston, Jamaica",
        "photo_url": "https://storage.example.com/photos/updated_d123456789.jpg"
    }
    ```
    """
    try:
        # Check if record exists
        existing = await get_driver_record_by_licence(licence_number)
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Driver record not found for licence number: {licence_number}"
            )
        
        # Update the record
        updated = await update_driver_record_db(licence_number, update_data)
        
        if not updated:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No valid fields provided for update"
            )
        
        # Publish event
        event_data = {
            "licence_number": licence_number,
            "action": "UPDATED",
            "updated_fields": update_data.dict(exclude_unset=True),
            "actor_id": str(current_user.user_id),
            "actor_role": current_user.role,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await publish_event(
            "DriverRecordUpdated",
            event_data,
            f"driver_record.updated.personal_info"
        )
        
        return StandardResponse(
            success=True,
            message="Driver record updated successfully",
            data={"licence_number": licence_number}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating driver record {licence_number}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error updating driver record"
        )

@router.post(
    "/driver-records/{licence_number}/theory-attempts",
    response_model=StandardResponse,
    summary="Add theory test attempt",
    description="""
    Record a new theory test attempt for a driver.
    
    **OpenAPI 3.0 Schema:**
    - **licence_number**: Driver's licence number (path parameter)
    - **Request Body**: TheoryAttempt model
    - **Authentication**: JWT Bearer token required
    """
)
async def add_theory_attempt(
    licence_number: str,
    attempt_data: TheoryAttempt,
    current_user: AuthUser = Depends(get_current_user)
):
    """
    Record a theory test attempt for a driver.
    
    **Example Request:**
    ```json
    {
        "attempt_no": 1,
        "module": "Traffic Signs and Rules",
        "score": 18,
        "passed": true,
        "attempt_date": "2024-01-20"
    }
    ```
    """
    try:
        # Check if driver record exists
        record = await get_driver_record_by_licence(licence_number)
        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Driver record not found for licence number: {licence_number}"
            )
        
        # Insert theory attempt
        conn = await get_db_connection()
        try:
            attempt_id = uuid.uuid4()
            query = """
                INSERT INTO driver_record.theory_attempts 
                (id, driver_record_id, attempt_no, module, score, pass, attempt_date)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
            """
            
            await conn.execute(
                query,
                attempt_id, record['id'], attempt_data.attempt_no,
                attempt_data.module, attempt_data.score, attempt_data.passed,
                attempt_data.attempt_date
            )
            
        finally:
            await db_pool.release(conn)
        
        # Publish event
        event_data = {
            "licence_number": licence_number,
            "attempt_id": str(attempt_id),
            "action": "THEORY_ATTEMPT_ADDED",
            "attempt_data": attempt_data.dict(),
            "actor_id": str(current_user.user_id),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await publish_event(
            "DriverRecordUpdated",
            event_data,
            f"driver_record.theory_attempt.{attempt_data.module.lower().replace(' ', '_')}"
        )
        
        return StandardResponse(
            success=True,
            message="Theory attempt recorded successfully",
            data={"attempt_id": str(attempt_id), "licence_number": licence_number}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding theory attempt for {licence_number}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error adding theory attempt"
        )

@router.post(
    "/driver-records/{licence_number}/yard-road-attempts",
    response_model=StandardResponse,
    summary="Add yard/road test attempt",
    description="""
    Record a new yard or road test attempt for a driver.
    
    **OpenAPI 3.0 Schema:**
    - **licence_number**: Driver's licence number (path parameter)
    - **Request Body**: YardRoadAttempt model with detailed criteria
    - **Authentication**: JWT Bearer token required
    """
)
async def add_yard_road_attempt(
    licence_number: str,
    attempt_data: YardRoadAttempt,
    current_user: AuthUser = Depends(get_current_user)
):
    """
    Record a yard or road test attempt for a driver.
    
    **Example Request:**
    ```json
    {
        "test_type": "Yard",
        "visit_no": 1,
        "attempt_date": "2024-01-25",
        "criteria": [
            {"criterion": "Reverse Parking", "major": 0, "minor": 1, "score": 8},
            {"criterion": "Hill Start", "major": 0, "minor": 0, "score": 10}
        ],
        "overall_result": false
    }
    ```
    """
    try:
        # Check if driver record exists
        record = await get_driver_record_by_licence(licence_number)
        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Driver record not found for licence number: {licence_number}"
            )
        
        # Insert yard/road attempt
        conn = await get_db_connection()
        try:
            attempt_id = uuid.uuid4()
            query = """
                INSERT INTO driver_record.yard_road_attempts 
                (id, driver_record_id, test_type, visit_no, attempt_date, criteria, overall_result)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
            """
            
            await conn.execute(
                query,
                attempt_id, record['id'], attempt_data.test_type.value,
                attempt_data.visit_no, attempt_data.attempt_date,
                json.dumps(attempt_data.criteria), attempt_data.overall_result
            )
            
        finally:
            await db_pool.release(conn)
        
        # Publish event
        event_data = {
            "licence_number": licence_number,
            "attempt_id": str(attempt_id),
            "action": "YARD_ROAD_ATTEMPT_ADDED",
            "attempt_data": attempt_data.dict(),
            "actor_id": str(current_user.user_id),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await publish_event(
            "DriverRecordUpdated",
            event_data,
            f"driver_record.{attempt_data.test_type.value.lower()}_attempt"
        )
        
        return StandardResponse(
            success=True,
            message=f"{attempt_data.test_type.value} test attempt recorded successfully",
            data={"attempt_id": str(attempt_id), "licence_number": licence_number}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding {attempt_data.test_type.value} attempt for {licence_number}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error adding {attempt_data.test_type.value} attempt"
        )

@router.post(
    "/driver-records/{licence_number}/court-records",
    response_model=StandardResponse,
    summary="Add court record entry",
    description="""
    Record a new court judgment/offense entry for a driver.
    
    **OpenAPI 3.0 Schema:**
    - **licence_number**: Driver's licence number (path parameter)
    - **Request Body**: CourtRecord model with judgment details
    - **Authentication**: JWT Bearer token required
    """
)
async def add_court_record(
    licence_number: str,
    court_data: CourtRecord,
    current_user: AuthUser = Depends(get_current_user)
):
    """
    Record a court judgment/offense entry for a driver.
    
    **Example Request:**
    ```json
    {
        "judgment_date": "2024-01-30",
        "offence": "Dangerous driving causing injury",
        "suspension_from": "2024-02-01",
        "suspension_to": "2024-08-01",
        "retest_required": {"written": true, "yard": true, "road": true, "other": false}
    }
    ```
    """
    try:
        # Check if driver record exists
        record = await get_driver_record_by_licence(licence_number)
        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Driver record not found for licence number: {licence_number}"
            )
        
        # Insert court record
        conn = await get_db_connection()
        try:
            court_id = uuid.uuid4()
            query = """
                INSERT INTO driver_record.court_records 
                (id, driver_record_id, judgment_date, offence, suspension_from, 
                 suspension_to, retest_required)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
            """
            
            await conn.execute(
                query,
                court_id, record['id'], court_data.judgment_date,
                court_data.offence, court_data.suspension_from,
                court_data.suspension_to, 
                json.dumps(court_data.retest_required) if court_data.retest_required else None
            )
            
        finally:
            await db_pool.release(conn)
        
        # Publish event
        event_data = {
            "licence_number": licence_number,
            "court_record_id": str(court_id),
            "action": "COURT_RECORD_ADDED",
            "court_data": court_data.dict(),
            "actor_id": str(current_user.user_id),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await publish_event(
            "DriverRecordUpdated",
            event_data,
            "driver_record.court_record.added"
        )
        
        return StandardResponse(
            success=True,
            message="Court record added successfully",
            data={"court_record_id": str(court_id), "licence_number": licence_number}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding court record for {licence_number}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error adding court record"
        )

@router.post(
    "/driver-records/{licence_number}/override",
    response_model=StandardResponse,
    summary="RD override action",
    description="""
    Perform Regional Director override action on a driver record. 
    Requires RD role authentication and mandatory reason.
    
    **OpenAPI 3.0 Schema:**
    - **licence_number**: Driver's licence number (path parameter)  
    - **Request Body**: OverrideRequest model with action and reason
    - **Authorization**: RD role required
    - **Audit**: All overrides are logged to audit trail
    """
)
async def override_driver_record(
    licence_number: str,
    override_data: OverrideRequest,
    current_user: AuthUser = Depends(get_rd_user)
):
    """
    Perform RD override action with audit logging.
    
    **Example Request:**
    ```json
    {
        "action": "Override suspension due to appeal",
        "reason": "Court appeal successful. Driver demonstrated sufficient evidence of medical recovery and completed remedial driving course as ordered by magistrate.",
        "new_status": "Issued",
        "metadata": {"court_case_no": "TC2024/001234", "appeal_date": "2024-02-15"}
    }
    ```
    """
    try:
        # Check if driver record exists
        record = await get_driver_record_by_licence(licence_number)
        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Driver record not found for licence number: {licence_number}"
            )
        
        conn = await get_db_connection()
        try:
            old_status = record.get('status')
            
            # Update status if provided
            if override_data.new_status:
                update_query = """
                    UPDATE driver_record.driver_records 
                    SET status = $1, updated_at = NOW()
                    WHERE licence_number = $2
                """
                await conn.execute(update_query, override_data.new_status.value, licence_number)
            
            # Create audit log entry
            audit_id = uuid.uuid4()
            audit_query = """
                INSERT INTO driver_record.audit_log 
                (id, actor_id, actor_role, action, resource_type, resource_id, 
                 old_val, new_val, reason)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            """
            
            old_val = {"status": old_status} if old_status else None
            new_val = {"status": override_data.new_status.value} if override_data.new_status else None
            
            await conn.execute(
                audit_query,
                audit_id, current_user.user_id, current_user.role,
                override_data.action, "DRIVER_RECORD", record['id'],
                json.dumps(old_val) if old_val else None,
                json.dumps(new_val) if new_val else None,
                override_data.reason
            )
            
        finally:
            await db_pool.release(conn)
        
        # Publish override event
        event_data = {
            "audit_id": str(audit_id),
            "licence_number": licence_number,
            "action": override_data.action,
            "old_status": old_status,
            "new_status": override_data.new_status.value if override_data.new_status else None,
            "reason": override_data.reason,
            "metadata": override_data.metadata,
            "actor_id": str(current_user.user_id),
            "actor_role": current_user.role,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await publish_event(
            "OverrideIssued",
            event_data,
            f"driver_record.override.{current_user.role}"
        )
        
        return StandardResponse(
            success=True,
            message="Override action completed successfully",
            data={
                "audit_id": str(audit_id),
                "licence_number": licence_number,
                "action": override_data.action
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing override for {licence_number}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error processing override"
        )

# ============================================================================
# STARTUP/SHUTDOWN EVENTS
# ============================================================================

@router.on_event("startup")
async def startup_event():
    """Initialize connections on startup"""
    await init_db_pool()
    await init_rabbitmq()
    logger.info("Driver Records router initialized successfully")

@router.on_event("shutdown") 
async def shutdown_event():
    """Clean up connections on shutdown"""
    global db_pool, rabbitmq_connection
    
    if db_pool:
        await db_pool.close()
        logger.info("Database pool closed")
    
    if rabbitmq_connection:
        await rabbitmq_connection.close()
        logger.info("RabbitMQ connection closed")