"""
ITADIAS Special Admin Microservice
FastAPI application for special test types, templates, and question management
Port: 8007, PostgreSQL schema: config
"""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import logging

from database import init_db, get_db_engine
from routes.special_types import router as special_types_router
from routes.templates import router as templates_router
from routes.modules import router as modules_router
from services.event_service import EventService
from services.template_service import TemplateService
from services.question_service import QuestionService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events"""
    # Startup
    logger.info("Starting ITADIAS Special Admin Microservice...")
    
    # Initialize database
    await init_db()
    logger.info("Database initialized with 'config' schema")
    
    # Initialize services
    event_service = EventService()
    await event_service.initialize()
    app.state.event_service = event_service
    logger.info("Event service initialized")
    
    template_service = TemplateService()
    app.state.template_service = template_service
    logger.info("Template service initialized")
    
    question_service = QuestionService()
    app.state.question_service = question_service
    logger.info("Question service initialized")
    
    yield
    
    # Shutdown
    logger.info("Shutting down ITADIAS Special Admin Microservice...")
    
    # Close services
    if hasattr(app.state, 'event_service'):
        await app.state.event_service.close()
    
    # Close database connections
    engine = get_db_engine()
    if engine:
        await engine.dispose()
    logger.info("Cleanup completed")

# Create FastAPI application
app = FastAPI(
    title="ITADIAS Special Admin Microservice",
    description="Special admin management for test types, certificate templates, and question modules",
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
        
        # Check services
        event_status = "connected" if hasattr(app.state, 'event_service') else "unavailable"
        template_status = "connected" if hasattr(app.state, 'template_service') else "unavailable"
        question_status = "connected" if hasattr(app.state, 'question_service') else "unavailable"
        
        # Get detailed service status
        services_detail = {}
        if hasattr(app.state, 'event_service'):
            services_detail["events"] = app.state.event_service.get_status()
        
        return {
            "status": "healthy",
            "service": "ITADIAS Special Admin Microservice",
            "version": "1.0.0",
            "port": 8007,
            "database": {
                "status": db_status,
                "schema": "config"
            },
            "services": {
                "events": event_status,
                "templates": template_status,
                "questions": question_status
            },
            "services_detail": services_detail
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "degraded",
            "service": "ITADIAS Special Admin Microservice",
            "version": "1.0.0",
            "port": 8007,
            "database": {"status": "error"},
            "services": {"status": "error"},
            "error": str(e)
        }

# Configuration endpoint
@app.get("/config")
async def get_config():
    """Get service configuration"""
    from config import config
    return {
        "service": {
            "name": config.service.name,
            "version": config.service.version,
            "port": config.service.port,
            "environment": config.service.env
        },
        "database": {
            "schema": config.db.schema,
            "host": config.db.host,
            "port": config.db.port,
            "name": config.db.name
        },
        "features": {
            "special_test_types": True,
            "certificate_templates": True,
            "question_modules": True,
            "csv_upload": True,
            "drag_drop_designer": True,
            "live_preview": True
        }
    }

# Statistics endpoint
@app.get("/stats")
async def get_statistics():
    """Get service statistics"""
    try:
        from database import get_db_session
        from sqlalchemy import func, select
        from models import SpecialTestType, QuestionModule, CertificateTemplate
        
        async with get_db_session() as db:
            # Count special test types
            stmt = select(func.count(SpecialTestType.id))
            result = await db.execute(stmt)
            special_types_count = result.scalar() or 0
            
            # Count active special test types
            stmt = select(func.count(SpecialTestType.id)).where(SpecialTestType.status == "active")
            result = await db.execute(stmt)
            active_special_types = result.scalar() or 0
            
            # Count question modules
            stmt = select(func.count(QuestionModule.id))
            result = await db.execute(stmt)
            modules_count = result.scalar() or 0
            
            # Count total questions across modules
            stmt = select(func.sum(QuestionModule.question_count))
            result = await db.execute(stmt)
            total_questions = result.scalar() or 0
            
            # Count certificate templates
            stmt = select(func.count(CertificateTemplate.id))
            result = await db.execute(stmt)
            templates_count = result.scalar() or 0
            
            # Count active templates
            stmt = select(func.count(CertificateTemplate.id)).where(CertificateTemplate.status == "active")
            result = await db.execute(stmt)
            active_templates = result.scalar() or 0
            
            return {
                "special_test_types": {
                    "total": special_types_count,
                    "active": active_special_types
                },
                "question_modules": {
                    "total": modules_count,
                    "total_questions": total_questions
                },
                "certificate_templates": {
                    "total": templates_count,
                    "active": active_templates
                },
                "last_updated": "2024-12-15T10:00:00Z"
            }
    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        return {"error": "Failed to get statistics", "detail": str(e)}

# Events status endpoint
@app.get("/events/status")
async def get_events_status():
    """Get events service status and fallback events"""
    try:
        if hasattr(app.state, 'event_service'):
            status = app.state.event_service.get_status()
            fallback_events = app.state.event_service.get_fallback_events(50)
            return {
                "service_status": status,
                "recent_fallback_events": fallback_events
            }
        else:
            return {"error": "Event service not available"}
    except Exception as e:
        logger.error(f"Error getting events status: {e}")
        return {"error": "Failed to get events status", "detail": str(e)}

# Include routers with API prefix
app.include_router(special_types_router, prefix="/api/v1", tags=["special-types"])
app.include_router(templates_router, prefix="/api/v1", tags=["templates"])
app.include_router(modules_router, prefix="/api/v1", tags=["modules"])

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "ITADIAS Special Admin Microservice",
        "version": "1.0.0",
        "port": 8007,
        "schema": "config",
        "docs": "/docs",
        "features": [
            "Special Test Types Management",
            "Certificate Template Designer", 
            "Question Module Management",
            "CSV Question Upload",
            "Live Template Preview",
            "Event Publishing"
        ]
    }

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8007))
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=port,
        reload=os.getenv("ENV") == "development",
        log_level="info"
    )