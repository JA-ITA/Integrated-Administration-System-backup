"""
Database configuration and management for Special Admin Microservice
"""
import asyncio
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text
import logging
from config import config

logger = logging.getLogger(__name__)

# SQLAlchemy Base
class Base(DeclarativeBase):
    pass

# Global engine and session maker
engine = None
async_session_maker = None

async def init_db():
    """Initialize database connection and create schema/tables"""
    global engine, async_session_maker
    
    try:
        # Create async engine
        engine = create_async_engine(
            config.db.url,
            echo=config.service.env == "development",
            pool_size=10,
            max_overflow=20,
            pool_timeout=30,
            pool_recycle=1800,
        )
        
        # Create session maker
        async_session_maker = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        
        # Create schema if it doesn't exist
        async with engine.begin() as conn:
            await conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {config.db.schema}"))
            logger.info(f"Schema '{config.db.schema}' created or verified")
        
        # Import models to register them
        from models import SpecialTestType, QuestionModule, CertificateTemplate
        
        # Create tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            logger.info("Database tables created or verified")
            
        logger.info("Database initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise

def get_db_engine():
    """Get database engine"""
    return engine

@asynccontextmanager
async def get_db_session():
    """Get database session with proper cleanup"""
    if not async_session_maker:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            await session.close()

async def close_db():
    """Close database connections"""
    global engine
    if engine:
        await engine.dispose()
        logger.info("Database connections closed")