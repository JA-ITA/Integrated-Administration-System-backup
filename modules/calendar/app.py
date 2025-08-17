"""
ITADIAS Calendar Microservice
FastAPI application for booking and slot management
"""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import logging

from database import init_db, get_db_engine
from routes.slots import router as slots_router
from routes.bookings import router as bookings_router
from routes.hubs import router as hubs_router
from services.event_service import EventService
from services.cleanup_service import CleanupService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events"""
    # Startup
    logger.info("Starting ITADIAS Calendar Microservice...")
    
    # Initialize database
    await init_db()
    logger.info("Database initialized")
    
    # Initialize event service
    event_service = EventService()
    await event_service.initialize()
    app.state.event_service = event_service
    logger.info("Event service initialized")
    
    # Initialize cleanup service for expired slot locks
    cleanup_service = CleanupService()
    await cleanup_service.start()
    app.state.cleanup_service = cleanup_service
    logger.info("Cleanup service started")
    
    yield
    
    # Shutdown
    logger.info("Shutting down ITADIAS Calendar Microservice...")
    
    # Stop cleanup service
    if hasattr(app.state, 'cleanup_service'):
        await app.state.cleanup_service.stop()
    
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
    title="ITADIAS Calendar Microservice",
    description="Booking and slot management for ITADIAS platform",
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
        
        # Check cleanup service
        cleanup_status = "running" if hasattr(app.state, 'cleanup_service') else "unavailable"
        
        return {
            "status": "healthy",
            "service": "ITADIAS Calendar Microservice",
            "version": "1.0.0",
            "database": db_status,
            "events": event_status,
            "cleanup_service": cleanup_status
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "degraded",
            "service": "ITADIAS Calendar Microservice",
            "version": "1.0.0",
            "database": "error",
            "events": "error",
            "cleanup_service": "error",
            "error": str(e)
        }

# Include routers
app.include_router(hubs_router, prefix="/api/v1", tags=["hubs"])
app.include_router(slots_router, prefix="/api/v1", tags=["slots"])
app.include_router(bookings_router, prefix="/api/v1", tags=["bookings"])

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "ITADIAS Calendar Microservice",
        "version": "1.0.0",
        "docs": "/docs"
    }

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8002))
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=port,
        reload=os.getenv("ENV") == "development",
        log_level="info"
    )