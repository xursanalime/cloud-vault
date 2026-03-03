import bcrypt
import secrets
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.models import User


async def create_user(
    db: AsyncSession,
    username: str,
    password: str,
    language: str = "uz"
):
    # Username tekshir
    result = await db.execute(select(User).where(User.username == username))
    existing_user = result.scalar_one_or_none()

    if existing_user:
        return None

    # Parol hash qilish
    hashed_password = bcrypt.hashpw(
        password.encode(),
        bcrypt.gensalt()
    ).decode()

    # Random security key
    security_key = secrets.token_hex(8)

    new_user = User(
        username=username,
        password_hash=hashed_password,
        security_key=security_key,
        language=language
    )

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    return new_user