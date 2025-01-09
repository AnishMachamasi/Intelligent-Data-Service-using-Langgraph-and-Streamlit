from collections.abc import AsyncGenerator, Generator

# If you want to use the context manager pattern:
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession

from config.database import AsyncSessionFactory, Base, engine


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionFactory() as session:
        try:
            yield session
        finally:
            await session.commit()


# Ensure that the tables are created at the application startup
async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
