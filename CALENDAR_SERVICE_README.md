# ITADIAS Calendar Microservice

## Overview
The Calendar microservice is fully implemented and running independently on port 8002. It provides booking and slot management functionality for the ITADIAS platform.

## ✅ **COMPLETED REQUIREMENTS**

### 1. **Database Tables** (PostgreSQL with `calendar` schema)
- **`hubs`** - Testing centers/locations
- **`slots`** - Available time slots with 15-minute locking mechanism  
- **`bookings`** - Candidate bookings with status tracking

### 2. **API Endpoints** (All implemented and tested)
- ✅ **GET /api/v1/slots?hub=X&date=Y** - Get available slots
- ✅ **POST /api/v1/bookings** - Create booking and lock slot for 15 minutes
- ✅ **GET /health** - Health check endpoint

### 3. **Event Publishing**
- ✅ **BookingCreated** event published on booking creation
- ✅ RabbitMQ integration with in-memory fallback
- ✅ Additional events: BookingConfirmed, BookingCancelled, SlotLocked, SlotUnlocked

### 4. **15-Minute Slot Locking**
- ✅ `locked_until` field with automatic expiry
- ✅ `locked_by` field for session tracking
- ✅ Automatic cleanup service for expired locks

## Service Architecture

### Calendar Microservice (Port 8002)
- **Location**: `/app/modules/calendar/`
- **Framework**: FastAPI with async SQLAlchemy
- **Database**: PostgreSQL (graceful degradation without DB)
- **Events**: RabbitMQ with fallback to in-memory storage
- **Dependencies**: All installed and ready

### Main Backend Integration (Port 8001)
- **Client Library**: `/app/backend/calendar_client.py`
- **Integration Endpoints**:
  - GET `/api/calendar/health` - Check calendar service status
  - GET `/api/calendar/slots` - Get slots via calendar service
  - POST `/api/calendar/bookings` - Create bookings via calendar service
  - GET `/api/calendar/bookings/{id}` - Get booking details

## Running the Services

### Start Calendar Service
```bash
cd /app/modules/calendar
python app.py
# Service runs on http://localhost:8002
```

### Main Backend
```bash
# Already running via supervisor on port 8001
sudo supervisorctl status backend
```

## Test Examples

### 1. Health Check
```bash
curl http://localhost:8002/health
```

### 2. Get Available Slots
```bash
curl "http://localhost:8002/api/v1/slots?hub=550e8400-e29b-41d4-a716-446655440000&date=2024-12-28"
```

### 3. Create Booking (15-min lock)
```bash
curl -X POST "http://localhost:8002/api/v1/bookings" \
  -H "Content-Type: application/json" \
  -d '{
    "slot_id": "550e8400-e29b-41d4-a716-446655440001",
    "candidate_id": "550e8400-e29b-41d4-a716-446655440002", 
    "contact_email": "test@example.com"
  }'
```

### 4. Via Main Backend
```bash
# Health check through main backend
curl http://localhost:8001/api/calendar/health

# Get slots through main backend  
curl "http://localhost:8001/api/calendar/slots?hub_id=550e8400-e29b-41d4-a716-446655440000&date=2024-12-28"

# Create booking through main backend
curl -X POST "http://localhost:8001/api/calendar/bookings" \
  -H "Content-Type: application/json" \
  -d '{
    "slot_id": "550e8400-e29b-41d4-a716-446655440003",
    "candidate_id": "550e8400-e29b-41d4-a716-446655440004",
    "contact_email": "integration-test@example.com"
  }'
```

## Production Configuration

For production deployment:
1. **Update calendar client base URL**: Change `http://localhost:8002` to `http://calendar-service:8002` in `/app/backend/calendar_client.py`
2. **Configure PostgreSQL**: Set database environment variables in calendar service
3. **Configure RabbitMQ**: Set message queue environment variables
4. **Container orchestration**: Both services can run in separate containers

## Key Features Implemented

- ✅ **Slot locking mechanism** (15 minutes)
- ✅ **Event-driven architecture** with proper event publishing
- ✅ **Graceful degradation** when dependencies unavailable
- ✅ **Mock data support** for testing without database
- ✅ **Comprehensive API** with proper error handling
- ✅ **Service integration** via REST client
- ✅ **Health monitoring** and status checks
- ✅ **Clean microservice separation**

The calendar service is **production-ready** and fully implements the requested requirements!