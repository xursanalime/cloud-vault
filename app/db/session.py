from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    AsyncSession
)
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession


from sqlalchemy.orm import sessionmaker
from app.config import DATABASE_URL


# 🔹 Engine yaratamiz
engine = create_async_engine(
    DATABASE_URL,
    echo=False,          # True qilsang SQL log chiqadi
    future=True,
)


# 🔹 Async session factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# 🔹 Dependency-style session (ixtiyoriy)
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


engine = create_async_engine(DATABASE_URL, echo=False)

async_session = async_sessionmaker(
    engine,
    expire_on_commit=False,
    class_=AsyncSession
)