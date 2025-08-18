"""
ITADIAS Certificate Microservice
FastAPI application for certificate generation and management
"""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
import uvicorn
import logging

from database import init_db, get_db_engine
from routes.certificates import router as certificates_router
from services.event_service import EventService
from services.certificate_service import CertificateService
from services.storage_service import StorageService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events"""
    # Startup
    logger.info("Starting ITADIAS Certificate Microservice...")
    
    # Initialize database
    await init_db()
    logger.info("Database initialized")
    
    # Initialize event service
    event_service = EventService()
    await event_service.initialize()
    app.state.event_service = event_service
    logger.info("Event service initialized")
    
    # Initialize storage service
    storage_service = StorageService()
    await storage_service.initialize()
    app.state.storage_service = storage_service
    logger.info("Storage service initialized")
    
    # Initialize certificate service
    certificate_service = CertificateService()
    app.state.certificate_service = certificate_service
    logger.info("Certificate service initialized")
    
    yield
    
    # Shutdown
    logger.info("Shutting down ITADIAS Certificate Microservice...")
    
    # Close services
    if hasattr(app.state, 'event_service'):
        await app.state.event_service.close()
    
    if hasattr(app.state, 'storage_service'):
        await app.state.storage_service.close()
    
    # Close database connections
    engine = get_db_engine()
    if engine:
        await engine.dispose()
    logger.info("Cleanup completed")

# Create FastAPI application
app = FastAPI(
    title="ITADIAS Certificate Microservice",
    description="Certificate generation and management for ITADIAS platform",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

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
        content={"error": "Internal server error", "detail": str(exc)}
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
        event_details = {}
        if hasattr(app.state, 'event_service'):
            event_details = app.state.event_service.get_status()
        
        # Check storage service
        storage_status = "connected" if hasattr(app.state, 'storage_service') else "unavailable"
        storage_details = {}
        if hasattr(app.state, 'storage_service'):
            storage_details = await app.state.storage_service.get_status()
        
        return {
            "status": "healthy",
            "service": "ITADIAS Certificate Microservice",
            "version": "1.0.0",
            "database": db_status,
            "events": event_status,
            "storage": storage_status,
            "event_details": event_details,
            "storage_details": storage_details
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "degraded",
            "service": "ITADIAS Certificate Microservice",
            "version": "1.0.0",
            "database": "error",
            "events": "error",
            "storage": "error",
            "error": str(e)
        }

# Configuration endpoint
@app.get("/config")
async def get_config():
    """Get certificate configuration"""
    from config import config
    return {
        "storage_backend": config.storage.backend,
        "supported_formats": ["PDF"],
        "max_certificate_age_days": config.certificate.max_age_days,
        "qr_code_enabled": config.certificate.qr_code_enabled,
        "template_engine": "handlebars",
        "available_templates": [
            "driver-licence-certificate",
            "endorsement-certificate"
        ]
    }

# Events status endpoint
@app.get("/events/status")
async def get_events_status():
    """Get events service status"""
    try:
        if hasattr(app.state, 'event_service'):
            return app.state.event_service.get_status()
        else:
            return {"error": "Event service not available"}
    except Exception as e:
        logger.error(f"Error getting events status: {e}")
        return {"error": "Failed to get events status", "detail": str(e)}

# Storage status endpoint
@app.get("/storage/status")
async def get_storage_status():
    """Get storage service status"""
    try:
        if hasattr(app.state, 'storage_service'):
            return await app.state.storage_service.get_status()
        else:
            return {"error": "Storage service not available"}
    except Exception as e:
        logger.error(f"Error getting storage status: {e}")
        return {"error": "Failed to get storage status", "detail": str(e)}

# Include routers
app.include_router(certificates_router, prefix="/api/v1", tags=["certificates"])

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "ITADIAS Certificate Microservice",
        "version": "1.0.0",
        "docs": "/docs"
    }

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8006))
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=port,
        reload=os.getenv("ENV") == "development",
        log_level="info"
    )