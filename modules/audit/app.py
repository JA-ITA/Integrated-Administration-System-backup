"""
ITADIAS Audit Microservice
FastAPI application for audit logging and RD override management
"""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import logging

from database import init_db, get_db_engine, close_db
from routes.overrides import router as overrides_router, set_services
from routes.audit_logs import router as audit_logs_router, set_audit_service
from services.event_service import EventService
from services.audit_service import AuditService
from config import config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events"""
    # Startup
    logger.info("Starting ITADIAS Audit Microservice...")
    
    # Initialize database
    db_initialized = await init_db()
    if not db_initialized:
        logger.error("Failed to initialize database")
        # Continue anyway for degraded mode
    else:
        logger.info("Database initialized successfully")
    
    # Initialize event service
    event_service = EventService()
    await event_service.initialize()
    app.state.event_service = event_service
    logger.info("Event service initialized")
    
    # Initialize audit service
    audit_service = AuditService(event_service)
    app.state.audit_service = audit_service
    logger.info("Audit service initialized")
    
    # Set service dependencies for routes
    set_services(audit_service, event_service)
    set_audit_service(audit_service)
    
    logger.info("Audit microservice startup completed")
    
    yield
    
    # Shutdown
    logger.info("Shutting down ITADIAS Audit Microservice...")
    
    # Close event service
    if hasattr(app.state, 'event_service'):
        await app.state.event_service.close()
    
    # Close database connections
    await close_db()
    
    logger.info("Audit microservice shutdown completed")

# Create FastAPI application
app = FastAPI(
    title="ITADIAS Audit Microservice",
    description="Audit logging and RD override management service for ITADIAS platform",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Configure JSON encoder for datetime and UUID serialization
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
        event_status = "unavailable"
        event_info = {}
        if hasattr(app.state, 'event_service'):
            event_info = await app.state.event_service.get_connection_status()
            event_status = "connected" if event_info.get("connected") else "fallback"
        
        return {
            "status": "healthy",
            "service": "ITADIAS Audit Microservice",
            "version": "1.0.0",
            "port": config.port,
            "database": {
                "status": db_status,
                "schema": config.db.schema,
                "host": config.db.host,
                "port": config.db.port
            },
            "events": {
                "status": event_status,
                "details": event_info
            },
            "authentication": {
                "identity_service_url": config.identity.service_url,
                "jwt_algorithm": config.identity.jwt_algorithm
            },
            "environment": config.environment
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "degraded",
                "service": "ITADIAS Audit Microservice",
                "version": "1.0.0",
                "database": "error",
                "events": "error",
                "error": str(e)
            }
        )

# Include routers with API versioning
app.include_router(overrides_router, prefix="/api/v1", tags=["overrides"])
app.include_router(audit_logs_router, prefix="/api/v1", tags=["audit-logs"])

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "ITADIAS Audit Microservice",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
        "features": [
            "RD JWT-based authentication",
            "PostgreSQL audit logging",
            "Override management with mandatory reasons",
            "Event publishing (OverrideIssued)",
            "Comprehensive audit trail",
            "Resource audit history tracking"
        ]
    }

# Configuration endpoint (for debugging/admin)
@app.get("/config")
async def get_configuration():
    """Get service configuration (excluding sensitive data)"""
    return {
        "service": {
            "name": "ITADIAS Audit Microservice",
            "version": "1.0.0",
            "port": config.port,
            "environment": config.environment,
            "debug": config.debug
        },
        "database": {
            "schema": config.db.schema,
            "host": config.db.host,
            "port": config.db.port,
            "name": config.db.name
            # Exclude password and user for security
        },
        "identity": {
            "service_url": config.identity.service_url,
            "jwt_algorithm": config.identity.jwt_algorithm
            # Exclude JWT secret for security
        },
        "rabbitmq": {
            "host": config.rabbitmq.host,
            "port": config.rabbitmq.port,
            "exchange": config.rabbitmq.exchange
            # Exclude credentials for security
        },
        "supported_actions": [
            "OVERRIDE", "REJECT", "APPROVE", "UPDATE_SLOT", 
            "CANCEL_BOOKING", "CREATE", "UPDATE", "DELETE"
        ],
        "supported_resource_types": [
            "RECEIPT", "REGISTRATION", "TEST", "CERTIFICATE", 
            "BOOKING", "SLOT"
        ],
        "supported_actor_roles": ["dao", "manager", "rd"]
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
    port = int(os.getenv("PORT", "8008"))
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=port,
        reload=os.getenv("ENV") == "development",
        log_level="info"
    )