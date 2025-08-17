"""
ITADIAS Registration Microservice
FastAPI application for driver registration with age, medical, and document validation
"""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import logging

from database import init_db, get_db_engine
from routes.registrations import router as registrations_router
from services.event_service import EventService
from services.validation_service import ValidationService
from config import config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events"""
    # Startup
    logger.info("Starting ITADIAS Registration Microservice...")
    
    # Initialize database
    await init_db()
    logger.info("Database initialized")
    
    # Initialize event service
    event_service = EventService()
    await event_service.initialize()
    app.state.event_service = event_service
    logger.info("Event service initialized")
    
    # Initialize validation service
    validation_service = ValidationService()
    app.state.validation_service = validation_service
    logger.info("Validation service initialized")
    
    # Check dependencies health
    try:
        dependency_status = await validation_service.health_check_dependencies()
        if dependency_status["all_dependencies_available"]:
            logger.info("All external dependencies are available")
        else:
            logger.warning("Some external dependencies are unavailable")
            for service, status in dependency_status["services"].items():
                if not status["available"]:
                    logger.warning(f"Service {service} is unavailable: {status.get('error', 'Unknown error')}")
    except Exception as e:
        logger.error(f"Failed to check dependencies: {e}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down ITADIAS Registration Microservice...")
    
    # Close event service
    if hasattr(app.state, 'event_service'):
        await app.state.event_service.close()
    
    # Close database connections
    engine = get_db_engine()
    if engine:
        await engine.dispose()
    logger.info("Cleanup completed")

# Create FastAPI application
app = FastAPI(
    title="ITADIAS Registration Microservice",
    description="Driver registration service with age, medical, and document validation for ITADIAS platform",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Configure JSON encoder for datetime serialization
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse as FastAPIJSONResponse

class CustomJSONResponse(FastAPIJSONResponse):
    def render(self, content) -> bytes:
        return super().render(jsonable_encoder(content))

app.default_response_class = CustomJSONResponse

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal server error", 
            "detail": str(exc),
            "code": "INTERNAL_ERROR"
        }
    )

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check database connection
        engine = get_db_engine()
        db_status = "connected" if engine else "unavailable"
        
        # Check event service
        event_status = "connected" if hasattr(app.state, 'event_service') else "unavailable"
        
        # Get event service connection info
        event_info = {}
        if hasattr(app.state, 'event_service'):
            event_info = await app.state.event_service.get_connection_status()
        
        # Check validation service and dependencies
        dependency_status = {}
        if hasattr(app.state, 'validation_service'):
            dependency_status = await app.state.validation_service.health_check_dependencies()
        
        return {
            "status": "healthy",
            "service": "ITADIAS Registration Microservice",
            "version": "1.0.0",
            "database": db_status,
            "events": event_status,
            "event_details": event_info,
            "dependencies": dependency_status,
            "configuration": {
                "min_age_provisional": config.registration.min_age_provisional,
                "min_age_class_b": config.registration.min_age_class_b,
                "min_age_class_c_ppv": config.registration.min_age_class_c_ppv,
                "weight_threshold_class_c": config.registration.weight_threshold_class_c,
                "max_document_size_mb": config.registration.max_document_size // (1024 * 1024),
                "environment": config.environment
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "degraded",
            "service": "ITADIAS Registration Microservice",
            "version": "1.0.0",
            "database": "error",
            "events": "error",
            "dependencies": "error",
            "error": str(e)
        }

# Include routers with API versioning
app.include_router(registrations_router, prefix="/api/v1", tags=["registrations"])

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "ITADIAS Registration Microservice",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
        "features": [
            "Driver registration with age validation",
            "Medical certificate requirements (MC1 for Provisional, MC2 for ALL Class C/PPV)",
            "Document upload and validation",
            "External service integration (Calendar, Receipt)",
            "Event publishing (RegistrationCompleted)",
            "Manager override support"
        ]
    }

# Configuration endpoint (for debugging/admin)
@app.get("/config")
async def get_configuration():
    """Get service configuration (excluding sensitive data)"""
    return {
        "registration_rules": {
            "min_age_provisional": config.registration.min_age_provisional,
            "min_age_class_b": config.registration.min_age_class_b,
            "min_age_class_c_ppv": config.registration.min_age_class_c_ppv,
            "weight_threshold_class_c": config.registration.weight_threshold_class_c,
            "max_document_size_mb": config.registration.max_document_size // (1024 * 1024)
        },
        "document_formats": {
            "photo": config.registration.allowed_photo_formats,
            "id_proof": config.registration.allowed_id_proof_formats,
            "medical": config.registration.allowed_medical_formats,
            "other": config.registration.allowed_other_formats
        },
        "database": {
            "schema": config.db.schema,
            "host": config.db.host,
            "port": config.db.port,
            "name": config.db.name
            # Exclude password and user for security
        },
        "external_services": {
            "calendar_service": "http://localhost:8002",
            "receipt_service": "http://localhost:8003"
        },
        "environment": config.environment,
        "debug": config.debug
    }

# Events endpoint (for monitoring)
@app.get("/events/status")
async def get_events_status():
    """Get event publishing status and fallback events"""
    try:
        if hasattr(app.state, 'event_service'):
            connection_status = await app.state.event_service.get_connection_status()
            fallback_events = await app.state.event_service.get_fallback_events()
            
            return {
                "event_service": connection_status,
                "fallback_events_count": len(fallback_events),
                "fallback_events": fallback_events[-10:]  # Last 10 events for preview
            }
        else:
            return {
                "event_service": {"connected": False, "error": "Event service not initialized"},
                "fallback_events_count": 0,
                "fallback_events": []
            }
    except Exception as e:
        logger.error(f"Failed to get events status: {e}")
        return {
            "error": str(e),
            "event_service": {"connected": False},
            "fallback_events_count": 0
        }

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8004"))
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=port,
        reload=os.getenv("ENV") == "development",
        log_level="info"
    )