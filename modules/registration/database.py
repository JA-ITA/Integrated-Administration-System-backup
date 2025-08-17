"""
Database setup and connection management for Registration microservice
"""
import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text
from config import config

logger = logging.getLogger(__name__)

# SQLAlchemy Base
class Base(DeclarativeBase):
    pass

# Database engine and session
engine = None
async_session_factory = None

def get_db_engine():
    """Get the database engine"""
    return engine

async def init_db():
    """Initialize database connection and create schema/tables"""
    global engine, async_session_factory
    
    try:
        # Create async engine
        engine = create_async_engine(
            config.db.url,
            echo=config.debug,
            pool_pre_ping=True,
            pool_recycle=300,
        )
        
        # Create session factory
        async_session_factory = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        
        # Create schema if it doesn't exist
        async with engine.begin() as conn:
            await conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {config.db.schema}"))
            logger.info(f"Schema '{config.db.schema}' ensured")
        
        # Create all tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            logger.info("Database tables created successfully")
            
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise

async def get_db_session() -> AsyncSession:
    """Get database session"""
    if async_session_factory is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

async def close_db():
    """Close database connections"""
    global engine
    if engine:
        await engine.dispose()
        logger.info("Database connections closed")