# ITADIAS Driver Records API

A comprehensive FastAPI router for managing driver records, test attempts, court records, and administrative overrides in the ITADIAS (Island Traffic Authority Driver Information and Assessment System).

## 🚀 Features

### ✅ **Complete Driver Record Management**
- Full CRUD operations on driver records
- Integration with identity service for candidate references
- Support for all Jamaica licence types (Provisional, Class B, Class C, PPV, Special)

### ✅ **Test Attempt Tracking**
- **Theory Tests**: Module-based scoring with pass/fail determination
- **Practical Tests**: Yard and Road tests with detailed criteria assessment
- **Attempt Limits**: Configurable attempt tracking with visit numbers

### ✅ **Legal & Administrative Features**  
- **Court Records**: Complete judgment and offense tracking
- **Suspension Management**: Date-based licence suspension periods
- **Retest Requirements**: Configurable retest mandates per court order
- **RD Overrides**: Regional Director emergency override functionality

### ✅ **Security & Compliance**
- **JWT Authentication**: Integration with existing identity microservice
- **Role-Based Access**: DAO, Manager, and RD permission levels
- **Audit Trail**: Complete action logging with actor tracking
- **Mandatory Reasoning**: Required justification for all override actions

### ✅ **Technical Excellence**
- **AsyncPG Integration**: High-performance PostgreSQL connectivity
- **RabbitMQ Events**: Real-time event publishing with fallback mechanisms
- **OpenAPI 3.0**: Complete API documentation with examples
- **Comprehensive Testing**: pytest-asyncio unit tests with faker data generation

---

## 📋 API Endpoints

| Method | Endpoint | Description | Authorization |
|--------|----------|-------------|---------------|
| `GET` | `/driver-records/{licence_number}` | Get complete driver record with all related data | Any authenticated user |
| `POST` | `/driver-records` | Create new driver record | DAO or RD roles only |
| `PUT` | `/driver-records/{licence_number}` | Update personal information fields | DAO or RD roles only |
| `POST` | `/driver-records/{licence_number}/theory-attempts` | Record theory test attempt | Any authenticated user |
| `POST` | `/driver-records/{licence_number}/yard-road-attempts` | Record yard/road test attempt | Any authenticated user |
| `POST` | `/driver-records/{licence_number}/court-records` | Add court judgment record | Any authenticated user |
| `POST` | `/driver-records/{licence_number}/override` | Perform RD override action | RD role only |

---

## 🔧 Installation & Setup

### Prerequisites
```bash
# Required Python packages
pip install fastapi asyncpg aio-pika pydantic python-jose

# For testing
pip install pytest pytest-asyncio faker
```

### Database Schema
First, create the database schema using the provided SQL file:
```bash
psql -h localhost -U ita_admin -d itadias -f driver_record_schema.sql
```

### Router Integration
```python
from fastapi import FastAPI
from driver_record_router import router

app = FastAPI(title="ITADIAS API")

# Mount the driver records router
app.include_router(router)

# The router will be available at /api/v1/driver-records/*
```

### Environment Configuration
The router expects these database settings:
```python
# Database Configuration (modify in router file if needed)
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432, 
    'database': 'itadias',
    'user': 'ita_admin',
    'password': 'ita_secure_2024'
}

# RabbitMQ Configuration  
RABBITMQ_URL = "amqp://guest:guest@localhost:5672/"
```

---

## 📖 Usage Examples

### 1. Create Driver Record
```bash
POST /api/v1/driver-records
Authorization: Bearer <JWT_TOKEN>
Content-Type: application/json

{
    "candidate_id": "123e4567-e89b-12d3-a456-426614174000",
    "licence_number": "D123456789", 
    "christian_names": "John Michael",
    "surname": "Smith",
    "address": "123 Main Street, Kingston, Jamaica",
    "dob": "1990-05-15",
    "licence_type": "Class B",
    "status": "Issued",
    "application_date": "2024-01-15"
}
```

**Response:**
```json
{
    "success": true,
    "message": "Driver record created successfully",
    "data": {
        "record_id": "550e8400-e29b-41d4-a716-446655440000",
        "licence_number": "D123456789"
    }
}
```

### 2. Get Complete Driver Record
```bash
GET /api/v1/driver-records/D123456789
Authorization: Bearer <JWT_TOKEN>
```

**Response:**
```json
{
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "licence_number": "D123456789",
    "christian_names": "John Michael", 
    "surname": "Smith",
    "address": "123 Main Street, Kingston, Jamaica",
    "dob": "1990-05-15",
    "licence_type": "Class B",
    "status": "Issued",
    "theory_attempts": [
        {
            "id": "660f8400-e29b-41d4-a716-446655440001",
            "attempt_no": 1,
            "module": "Traffic Signs and Rules",
            "score": 18,
            "passed": true,
            "attempt_date": "2024-01-20"
        }
    ],
    "yard_road_attempts": [],
    "endorsements": [],
    "court_records": []
}
```

### 3. Record Theory Test Attempt
```bash
POST /api/v1/driver-records/D123456789/theory-attempts
Authorization: Bearer <JWT_TOKEN>
Content-Type: application/json

{
    "attempt_no": 1,
    "module": "Traffic Signs and Rules", 
    "score": 18,
    "passed": true,
    "attempt_date": "2024-01-20"
}
```

### 4. Record Yard/Road Test Attempt
```bash
POST /api/v1/driver-records/D123456789/yard-road-attempts
Authorization: Bearer <JWT_TOKEN>
Content-Type: application/json

{
    "test_type": "Yard",
    "visit_no": 1,
    "attempt_date": "2024-01-25",
    "criteria": [
        {
            "criterion": "Reverse Parking",
            "major": 0,
            "minor": 1, 
            "score": 8
        },
        {
            "criterion": "Hill Start",
            "major": 0,
            "minor": 0,
            "score": 10
        }
    ],
    "overall_result": false
}
```

### 5. Add Court Record
```bash
POST /api/v1/driver-records/D123456789/court-records
Authorization: Bearer <JWT_TOKEN>
Content-Type: application/json

{
    "judgment_date": "2024-01-30",
    "offence": "Dangerous driving causing injury",
    "suspension_from": "2024-02-01",
    "suspension_to": "2024-08-01",
    "retest_required": {
        "written": true,
        "yard": true, 
        "road": true,
        "other": false
    }
}
```

### 6. RD Override Action
```bash
POST /api/v1/driver-records/D123456789/override
Authorization: Bearer <RD_JWT_TOKEN>
Content-Type: application/json

{
    "action": "Override suspension due to appeal",
    "reason": "Court appeal successful. Driver demonstrated sufficient evidence of medical recovery and completed remedial driving course as ordered by magistrate.",
    "new_status": "Issued",
    "metadata": {
        "court_case_no": "TC2024/001234",
        "appeal_date": "2024-02-15"
    }
}
```

---

## 🔐 Authentication & Authorization

### JWT Token Requirements
All endpoints require a valid JWT Bearer token:
```bash
Authorization: Bearer <JWT_TOKEN>
```

### Role-Based Access Control

| Role | Permissions |
|------|-------------|
| **Any Authenticated User** | • View driver records<br>• Add test attempts<br>• Add court records |
| **DAO (Data Administrative Officer)** | • All user permissions<br>• Create driver records<br>• Update personal information |
| **Manager** | • All user permissions<br>• Administrative oversight |
| **RD (Regional Director)** | • All permissions<br>• Override actions<br>• Emergency status changes |

### Error Responses
```json
// 401 Unauthorized
{
    "detail": "Invalid or expired authentication token"
}

// 403 Forbidden  
{
    "detail": "Access denied. RD role required."
}

// 404 Not Found
{
    "detail": "Driver record not found for licence number: D123456789"
}

// 409 Conflict
{
    "detail": "Driver record already exists for licence number: D123456789"
}
```

---

## 🧪 Testing

### Run Unit Tests
```bash
# Install test dependencies
pip install pytest pytest-asyncio faker

# Run all tests
pytest tests/test_driver_record.py -v

# Run specific test class
pytest tests/test_driver_record.py::TestCreateDriverRecord -v

# Run with coverage
pytest tests/test_driver_record.py --cov=driver_record_router --cov-report=html
```

### Test Categories
- **Authentication Tests**: JWT validation, role-based access control
- **Database Operation Tests**: CRUD operations, connection handling
- **API Endpoint Tests**: Request/response validation, error handling
- **Pydantic Model Tests**: Data validation, field constraints
- **Integration Tests**: End-to-end workflows
- **Error Handling Tests**: Exception scenarios, fallback mechanisms

### Mock Data Generation
The test suite uses `faker` for realistic test data:
```python
# Generate sample driver record
fake_driver = sample_driver_create()
fake_theory_attempt = sample_theory_attempt()
fake_court_record = sample_court_record()
```

---

## 📊 Database Schema Integration

### Tables Used
- **`driver_record.driver_records`**: Main driver information
- **`driver_record.theory_attempts`**: Theory test history  
- **`driver_record.yard_road_attempts`**: Practical test history
- **`driver_record.endorsements`**: Licence endorsements
- **`driver_record.court_records`**: Legal proceedings
- **`driver_record.audit_log`**: Administrative actions audit trail
- **`identity.candidates`**: Referenced for candidate information

### Foreign Key Relationships
```sql
-- Driver records reference candidates
driver_records.candidate_id → identity.candidates.id

-- All related tables reference driver records  
theory_attempts.driver_record_id → driver_records.id
yard_road_attempts.driver_record_id → driver_records.id
court_records.driver_record_id → driver_records.id
endorsements.driver_record_id → driver_records.id

-- Audit log references candidates for actor tracking
audit_log.actor_id → identity.candidates.id
```

---

## 🎯 Event Publishing

### Events Published

| Event Type | Routing Key | Trigger |
|------------|-------------|---------|
| `DriverRecordUpdated` | `driver_record.created.{licence_type}` | New driver record creation |
| `DriverRecordUpdated` | `driver_record.updated.personal_info` | Personal information update |
| `DriverRecordUpdated` | `driver_record.theory_attempt.{module}` | Theory test completion |
| `DriverRecordUpdated` | `driver_record.{test_type}_attempt` | Practical test completion |
| `DriverRecordUpdated` | `driver_record.court_record.added` | Court record addition |
| `OverrideIssued` | `driver_record.override.{actor_role}` | RD override action |

### Event Payload Example
```json
{
    "record_id": "550e8400-e29b-41d4-a716-446655440000",
    "licence_number": "D123456789",
    "action": "CREATED",
    "actor_id": "123e4567-e89b-12d3-a456-426614174000",
    "actor_role": "dao",
    "timestamp": "2024-01-15T10:30:00.000Z"
}
```

---

## ⚠️ Important Notes

### Licence Number Format
- Must be unique across the system
- Recommended format: `D` followed by 9 digits (e.g., `D123456789`)
- Case-sensitive matching

### Business Rules
- **Theory Tests**: Score 0-20, pass threshold typically ≥15
- **Practical Tests**: Major faults = automatic fail, minor faults ≤3 for pass
- **Court Suspensions**: End date must be after start date
- **Overrides**: RD role required, mandatory reason (minimum 20 characters)

### Data Validation
- **Dates**: Must be valid ISO format (YYYY-MM-DD)
- **UUIDs**: Must be valid UUID4 format
- **Addresses**: Minimum 10 characters for completeness
- **Names**: No special character restrictions (supports international names)

### Error Handling
- Database connection failures: Graceful degradation
- RabbitMQ unavailable: Fallback to local logging
- Validation errors: Detailed field-level error messages
- Authentication failures: Secure error responses without information leakage

---

## 🔧 Configuration Options

### Connection Pool Settings
```python
# Modify in router file
DB_POOL_CONFIG = {
    'min_size': 1,
    'max_size': 10, 
    'command_timeout': 30
}
```

### JWT Configuration
```python
# Update authentication settings
JWT_CONFIG = {
    'secret_key': 'your-secret-key-here',
    'algorithm': 'HS256',
    'identity_service_url': 'http://localhost:8001'
}
```

### RabbitMQ Settings
```python
# Event publishing configuration
RABBITMQ_CONFIG = {
    'exchange': 'itadias.events',
    'exchange_type': 'topic',
    'durable': True
}
```

---

## 📞 Support & Maintenance

### API Documentation
- **Interactive Docs**: Available at `/docs` when router is mounted
- **OpenAPI Schema**: Available at `/openapi.json`
- **ReDoc**: Available at `/redoc`

### Monitoring & Logging
- All operations logged with appropriate log levels
- Database connection health monitoring
- Event publishing status tracking
- Authentication failure alerting

### Performance Considerations
- Connection pooling for database efficiency
- Async operations throughout
- Indexed database queries for fast lookups
- Event publishing with fallback mechanisms

---

## 🆕 Version History

### v1.0.0 - Initial Release
- ✅ Complete driver record CRUD operations
- ✅ Theory and practical test attempt tracking
- ✅ Court record management
- ✅ RD override functionality
- ✅ JWT authentication with role-based access
- ✅ PostgreSQL integration with asyncpg
- ✅ RabbitMQ event publishing
- ✅ Comprehensive unit test suite
- ✅ OpenAPI 3.0 documentation

---

*For technical support or feature requests, please contact the ITADIAS development team.*