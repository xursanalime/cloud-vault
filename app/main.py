import asyncio
from app.bot import bot, dp
from app.handlers.start import router as start_router
from app.db.session import engine
from app.db.base import Base
from app.handlers.auth import router as auth_router
from sqlalchemy import text
from app.handlers.upload import router as upload_router



async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        # 🔥 AGAR COLUMN YO‘Q BO‘LSA QO‘SHADI
        await conn.execute(text("""
            ALTER TABLE users
            ADD COLUMN IF NOT EXISTS failed_attempts INTEGER DEFAULT 0;
        """))

        await conn.execute(text("""
            ALTER TABLE users
            ADD COLUMN IF NOT EXISTS blocked_until TIMESTAMP;
        """))
async def main():
    await create_tables()

    dp.include_router(start_router)
    dp.include_router(auth_router)
    dp.include_router(upload_router)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())