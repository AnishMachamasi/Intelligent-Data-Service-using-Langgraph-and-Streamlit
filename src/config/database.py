import os

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.declarative import declarative_base

from utils.constants.constant import db_host, db_name, db_password, db_port, db_username

ECHO_VALUE = os.getenv("PROFILE") != "prod"

# Database connection URL (PostgreSQL)
DATABASE_URL = (
    f"postgresql+asyncpg://{db_username}:{db_password}@{db_host}:{db_port}/{db_name}"
)

engine = create_async_engine(DATABASE_URL, future=True, echo=True)

AsyncSessionFactory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=True,  # Add explicit autoflush setting
    autocommit=False,  # Add explicit autocommit setting
)
Base = declarative_base()
