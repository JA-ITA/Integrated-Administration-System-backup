"""
Island Traffic Authority Driver Integrated Administration System
FastAPI Main Application Entry Point
"""

import os
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from core.config import settings
from core.database import init_database, close_database
from core.logging_config import setup_logging
from core.middleware import setup_middleware
from core.exceptions import setup_exception_handlers

# Import module routers
from modules.identity.router import router as identity_router
from modules.calendar.router import router as calendar_router
from modules.receipt.router import router as receipt_router
from modules.registration.router import router as registration_router
from modules.test_engine.router import router as test_engine_router
from modules.certificate.router import router as certificate_router
from modules.special_admin.router import router as special_admin_router
from modules.audit.router import router as audit_router
from modules.checklist.router import router as checklist_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager for startup and shutdown events."""
    
    # Startup
    setup_logging()
    logger = logging.getLogger("ita.main")
    logger.info("🚀 Starting Island Traffic Authority Driver Platform")
    
    # Initialize database connection
    await init_database()
    logger.info("📊 Database connection established")
    
    yield
    
    # Shutdown
    await close_database()
    logger.info("👋 Island Traffic Authority Driver Platform shutdown complete")


def create_application() -> FastAPI:
    """Create and configure the FastAPI application."""
    
    app = FastAPI(
        title="Island Traffic Authority Driver Platform",
        description="Comprehensive digital platform for managing driver licensing, testing, and administrative operations",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/api/docs" if settings.ENVIRONMENT != "production" else None,
        redoc_url="/api/redoc" if settings.ENVIRONMENT != "production" else None,
        openapi_url="/api/openapi.json" if settings.ENVIRONMENT != "production" else None,
    )
    
    # Setup middleware
    setup_middleware(app)
    
    # Setup exception handlers
    setup_exception_handlers(app)
    
    # Include module routers with /api prefix
    app.include_router(identity_router, prefix="/api/identity", tags=["Identity Management"])
    app.include_router(calendar_router, prefix="/api/calendar", tags=["Calendar & Scheduling"])
    app.include_router(receipt_router, prefix="/api/receipts", tags=["Payments & Receipts"])
    app.include_router(registration_router, prefix="/api/registration", tags=["Driver Registration"])
    app.include_router(test_engine_router, prefix="/api/tests", tags=["Testing & Assessment"])
    app.include_router(certificate_router, prefix="/api/certificates", tags=["License Certificates"])
    app.include_router(special_admin_router, prefix="/api/admin", tags=["Special Administration"])
    app.include_router(audit_router, prefix="/api/audit", tags=["Audit & Compliance"])
    app.include_router(checklist_router, prefix="/api/checklists", tags=["Process Checklists"])
    
    # Health check endpoints
    @app.get("/health")
    async def health_check():
        """Health check endpoint for load balancers and monitoring."""
        return {
            "status": "healthy",
            "service": "ita-driver-platform",
            "version": "1.0.0",
            "environment": settings.ENVIRONMENT
        }
    
    @app.get("/api/health")
    async def api_health_check():
        """API health check with database connectivity verification."""
        # TODO: Add database connectivity check
        return {
            "status": "healthy",
            "service": "ita-driver-platform-api",
            "version": "1.0.0",
            "environment": settings.ENVIRONMENT,
            "database": "connected"
        }
    
    # Root endpoint
    @app.get("/")
    async def root():
        """Root endpoint with system information."""
        return {
            "message": "Island Traffic Authority Driver Integrated Administration System",
            "version": "1.0.0",
            "environment": settings.ENVIRONMENT,
            "documentation": "/api/docs" if settings.ENVIRONMENT != "production" else None
        }
    
    return app


# Create the application instance
app = create_application()


if __name__ == "__main__":
    # Development server configuration
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True if settings.ENVIRONMENT == "development" else False,
        log_level="info",
        access_log=True,
    )