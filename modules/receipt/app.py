"""
ITADIAS Receipt Microservice
FastAPI application for receipt validation
"""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import logging

from database import init_db, get_db_engine
from routes.receipts import router as receipts_router
from services.event_service import EventService
from config import config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events"""
    # Startup
    logger.info("Starting ITADIAS Receipt Microservice...")
    
    # Initialize database
    await init_db()
    logger.info("Database initialized")
    
    # Initialize event service
    event_service = EventService()
    await event_service.initialize()
    app.state.event_service = event_service
    logger.info("Event service initialized")
    
    yield
    
    # Shutdown
    logger.info("Shutting down ITADIAS Receipt Microservice...")
    
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
    title="ITADIAS Receipt Microservice",
    description="Receipt validation service for ITADIAS platform",
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
        
        return {
            "status": "healthy",
            "service": "ITADIAS Receipt Microservice",
            "version": "1.0.0",
            "database": db_status,
            "events": event_status,
            "configuration": {
                "max_receipt_age_days": config.receipt.max_age_days,
                "valid_locations_count": len(config.receipt.valid_locations),
                "environment": config.environment
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "degraded",
            "service": "ITADIAS Receipt Microservice",
            "version": "1.0.0",
            "database": "error",
            "events": "error",
            "error": str(e)
        }

# Include routers with API versioning
app.include_router(receipts_router, prefix="/api/v1", tags=["receipts"])

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "ITADIAS Receipt Microservice",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }

# Configuration endpoint (for debugging/admin)
@app.get("/config")
async def get_configuration():
    """Get service configuration (excluding sensitive data)"""
    return {
        "receipt_validation": {
            "max_age_days": config.receipt.max_age_days,
            "receipt_no_pattern": config.receipt.receipt_no_pattern,
            "valid_locations": config.receipt.valid_locations
        },
        "database": {
            "schema": config.db.schema,
            "host": config.db.host,
            "port": config.db.port,
            "name": config.db.name
            # Exclude password and user for security
        },
        "environment": config.environment,
        "debug": config.debug
    }

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8003))
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=port,
        reload=os.getenv("ENV") == "development",
        log_level="info"
    )