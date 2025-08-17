"""
Database configuration and connection management for PostgreSQL.
Uses SQLAlchemy async engine with connection pooling.
"""

import logging
from typing import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool
from sqlalchemy import MetaData, event
from sqlalchemy.engine import Engine

from core.config import get_settings, get_database_url

logger = logging.getLogger("ita.database")


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""
    
    metadata = MetaData(
        naming_convention={
            "ix": "ix_%(column_0_label)s",
            "uq": "uq_%(table_name)s_%(column_0_name)s",
            "ck": "ck_%(table_name)s_%(constraint_name)s",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s",
        }
    )


# Global database engine and session factory
engine = None
async_session_factory = None


def create_engine():
    """Create and configure the database engine."""
    global engine
    
    settings = get_settings()
    database_url = get_database_url()
    
    # Engine configuration
    engine_kwargs = {
        "echo": settings.is_development,
        "pool_size": settings.DATABASE_POOL_SIZE,
        "max_overflow": settings.DATABASE_MAX_OVERFLOW,
        "pool_timeout": settings.DATABASE_POOL_TIMEOUT,
        "pool_recycle": settings.DATABASE_POOL_RECYCLE,
    }
    
    # Use NullPool for testing to avoid connection issues
    if settings.is_testing:
        engine_kwargs["poolclass"] = NullPool
    
    engine = create_async_engine(database_url, **engine_kwargs)
    
    logger.info(f"Database engine created for: {database_url.split('@')[1] if '@' in database_url else 'database'}")
    
    return engine


async def init_database():
    """Initialize database connection and create session factory."""
    global async_session_factory
    
    if engine is None:
        create_engine()
    
    # Create async session factory
    async_session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    logger.info("Database session factory initialized")


async def close_database():
    """Close database connections and cleanup."""
    global engine
    
    if engine:
        await engine.dispose()
        logger.info("Database connections closed")


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Get database session with automatic transaction management."""
    if async_session_factory is None:
        raise RuntimeError("Database not initialized. Call init_database() first.")
    
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for FastAPI to get database session."""
    async with get_session() as session:
        yield session


# Database event listeners for enhanced functionality
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Set SQLite pragmas for better performance (if using SQLite in testing)."""
    if "sqlite" in str(dbapi_connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


# Health check functions
async def check_database_health() -> dict:
    """Check database connectivity and return health status."""
    try:
        async with get_session() as session:
            result = await session.execute("SELECT 1")
            result.scalar()
            return {
                "status": "healthy",
                "message": "Database connection successful"
            }
    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "message": f"Database connection failed: {str(e)}"
        }


# Utility functions for database operations
async def create_tables():
    """Create all database tables. Used for development and testing."""
    if engine is None:
        create_engine()
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    logger.info("Database tables created")


async def drop_tables():
    """Drop all database tables. Used for testing cleanup."""
    if engine is None:
        create_engine()
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    logger.info("Database tables dropped")


# Database URL utilities
def get_db_info() -> dict:
    """Get database connection information for monitoring."""
    if engine is None:
        return {"status": "not_initialized"}
    
    return {
        "pool_size": engine.pool.size(),
        "checked_in": engine.pool.checkedin(),
        "checked_out": engine.pool.checkedout(),
        "overflow": engine.pool.overflow(),
        "status": "initialized"
    }