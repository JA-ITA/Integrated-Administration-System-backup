"""
ITADIAS Test Engine Microservice
FastAPI application for test management and auto-grading
"""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import logging

from database import init_db, get_db_engine
from routes.tests import router as tests_router
from routes.questions import router as questions_router
from services.event_service import EventService
from services.test_service import TestService
from services.seed_service import SeedService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events"""
    # Startup
    logger.info("Starting ITADIAS Test Engine Microservice...")
    
    # Initialize database
    await init_db()
    logger.info("Database initialized")
    
    # Initialize event service
    event_service = EventService()
    await event_service.initialize()
    app.state.event_service = event_service
    logger.info("Event service initialized")
    
    # Initialize test service
    test_service = TestService()
    app.state.test_service = test_service
    logger.info("Test service initialized")
    
    # Seed sample questions if needed
    try:
        seed_service = SeedService()
        await seed_service.seed_sample_questions()
        logger.info("Sample questions seeded (if needed)")
    except Exception as e:
        logger.warning(f"Failed to seed sample questions: {e}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down ITADIAS Test Engine Microservice...")
    
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
    title="ITADIAS Test Engine Microservice",
    description="Test management and auto-grading for ITADIAS platform",
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
        
        return {
            "status": "healthy",
            "service": "ITADIAS Test Engine Microservice",
            "version": "1.0.0",
            "database": db_status,
            "events": event_status,
            "event_details": event_details
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "degraded",
            "service": "ITADIAS Test Engine Microservice",
            "version": "1.0.0",
            "database": "error",
            "events": "error",
            "error": str(e)
        }

# Configuration endpoint
@app.get("/config")
async def get_config():
    """Get test configuration"""
    from config import config
    return {
        "questions_per_test": config.test.questions_per_test,
        "time_limit_minutes": config.test.time_limit_minutes,
        "passing_score_percent": config.test.passing_score_percent,
        "max_attempts_per_booking": config.test.max_attempts_per_booking,
        "available_modules": [module.value for module in config.test.__class__.__dict__.get('TestModule', [])] or [
            "Provisional", "Class-B", "Class-C", "PPV", "HAZMAT"
        ]
    }

# Statistics endpoint
@app.get("/stats")
async def get_statistics():
    """Get test statistics"""
    try:
        if hasattr(app.state, 'test_service'):
            from database import get_db_session
            async with get_db_session() as db:
                stats = await app.state.test_service.get_test_statistics(db)
                return stats
        else:
            return {"error": "Test service not available"}
    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        return {"error": "Failed to get statistics", "detail": str(e)}

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

# Include routers
app.include_router(tests_router, prefix="/api/v1", tags=["tests"])

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "ITADIAS Test Engine Microservice",
        "version": "1.0.0",
        "docs": "/docs"
    }

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8005))
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=port,
        reload=os.getenv("ENV") == "development",
        log_level="info"
    )