# db/database.py
"""
Database connection and session management for PostgreSQL.
"""
import logging
from typing import AsyncGenerator, Optional
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
    AsyncEngine
)
from sqlalchemy.orm import declarative_base
from sqlalchemy import event
from sqlalchemy.pool import NullPool

from core.settings import (
    DATABASE_URL,
    DB_POOL_SIZE,
    DB_MAX_OVERFLOW,
    DB_POOL_TIMEOUT,
    DB_ECHO,
)

logger = logging.getLogger(__name__)

# Create async engine with connection pooling
engine: Optional[AsyncEngine] = None
async_session_maker: Optional[async_sessionmaker] = None


async def init_db() -> None:
    """Initialize database connection pool."""
    global engine, async_session_maker
    
    try:
        # For async engines, SQLAlchemy automatically uses AsyncAdaptedQueuePool
        # We just need to specify pool_size and max_overflow
        engine = create_async_engine(
            DATABASE_URL,
            pool_size=DB_POOL_SIZE,
            max_overflow=DB_MAX_OVERFLOW,
            pool_timeout=DB_POOL_TIMEOUT,
            pool_pre_ping=True,  # Verify connections before using
            echo=DB_ECHO,
        )
        
        async_session_maker = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
        
        logger.info(
            f"Database connection pool initialized "
            f"(pool_size={DB_POOL_SIZE}, max_overflow={DB_MAX_OVERFLOW})"
        )
        
        # Test connection
        try:
            async with engine.begin() as conn:
                from sqlalchemy import text
                await conn.execute(text("SELECT 1"))
            logger.info("Database connection test successful")
        except Exception as test_error:
            logger.warning(f"Database connection test failed: {test_error}")
            # Don't fail initialization if test fails (might be connection issue)
        
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}", exc_info=True)
        raise


async def close_db() -> None:
    """Close database connection pool."""
    global engine, async_session_maker
    
    if engine:
        await engine.dispose()
        engine = None
        async_session_maker = None
        logger.info("Database connection pool closed")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for getting database session.
    Use this in FastAPI route dependencies.
    """
    if not async_session_maker:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


def get_async_session() -> AsyncSession:
    """
    Get a new async database session.
    Use this for manual session management.
    """
    if not async_session_maker:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    
    return async_session_maker()


def SessionLocal():
    """
    Get a database session context manager.
    Use this as: async with SessionLocal() as session:
    
    This is a compatibility function for code that expects SessionLocal().
    """
    if not async_session_maker:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    
    return async_session_maker()

