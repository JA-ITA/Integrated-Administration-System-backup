"""
ITADIAS Identity Microservice
FastAPI application for candidate identity management
"""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import logging

from database import init_db, get_db_engine
from routes.candidates import router as candidates_router
from services.event_service import EventService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events"""
    # Startup
    logger.info("Starting ITADIAS Identity Microservice...")
    
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
    logger.info("Shutting down ITADIAS Identity Microservice...")
    if hasattr(app.state, 'event_service'):
        await app.state.event_service.close()
    
    # Close database connections
    engine = get_db_engine()
    if engine:
        await engine.dispose()
    logger.info("Cleanup completed")

# Create FastAPI application
app = FastAPI(
    title="ITADIAS Identity Microservice",
    description="Identity and Profile management for candidates",
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
        if not engine:
            raise HTTPException(status_code=503, detail="Database not available")
        
        # Check event service
        if not hasattr(app.state, 'event_service'):
            raise HTTPException(status_code=503, detail="Event service not available")
        
        return {
            "status": "healthy",
            "service": "ITADIAS Identity Microservice",
            "version": "1.0.0",
            "database": "connected",
            "events": "connected"
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")

# Include routers
app.include_router(candidates_router, prefix="/api/v1", tags=["candidates"])

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "ITADIAS Identity Microservice",
        "version": "1.0.0",
        "docs": "/docs"
    }

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8001))
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=port,
        reload=os.getenv("ENV") == "development",
        log_level="info"
    )