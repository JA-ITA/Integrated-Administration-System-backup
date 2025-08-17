"""
Database configuration and initialization for ITADIAS Identity Microservice
"""
import logging
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import text
from config import config

logger = logging.getLogger(__name__)

# Database engine and session maker
engine = None
async_session_maker = None

# Base class for SQLAlchemy models
Base = declarative_base()

async def init_db():
    """Initialize database connection and create tables"""
    global engine, async_session_maker
    
    try:
        # Create async engine
        engine = create_async_engine(
            config.db.url,
            echo=config.debug,
            pool_pre_ping=True,
            pool_recycle=3600
        )
        
        # Create session maker
        async_session_maker = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        
        # Test connection
        async with engine.begin() as conn:
            # Create schema if not exists
            await conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {config.db.schema}"))
            logger.info(f"Schema '{config.db.schema}' ensured")
        
        # Import models to register them with Base
        from models import Candidate, OTPVerification, EventLog
        
        # Create all tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        logger.info("Database initialized successfully")
        
    except Exception as e:
        logger.warning(f"Failed to initialize database: {e}")
        logger.info("Service will continue without database connectivity")
        # Don't raise the exception, allow service to start

def get_db_engine():
    """Get database engine"""
    return engine

@asynccontextmanager
async def get_db_session():
    """Get database session context manager"""
    if not async_session_maker:
        raise RuntimeError("Database not initialized")
    
    async with async_session_maker() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

async def get_db():
    """Dependency to get database session"""
    if not async_session_maker:
        # Return None when database is not available instead of raising exception
        logger.warning("Database not available, returning None")
        yield None
        return
    
    async with get_db_session() as session:
        yield session