from __future__ import annotations

import os
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import get_settings

settings = get_settings()

# Define a URL de conexão do PostgreSQL
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    settings.database_url if "postgres" in settings.database_url else "postgresql+asyncpg://postgres:postgres@localhost:5432/finscope"
)

engine: AsyncEngine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependência FastAPI que fornece uma sessão assíncrona por requisição.

    Yields:
        Sessão SQLAlchemy com rollback automático em erro e fechamento
        garantido ao final da requisição.
    """
    async with async_session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
