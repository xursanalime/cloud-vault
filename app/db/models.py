from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.sql import func
from datetime import datetime
from app.db.base import Base

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey

telegram_id = Column(Integer, unique=True, nullable=True)
username = Column(String, unique=True, index=True)

class User(Base):
    __tablename__ = "users"
    is_logged_in = Column(Boolean, default=False)
    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(String, unique=True, nullable=True)
    username = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    security_key = Column(String, nullable=False)
    language = Column(String, default="uz")
    is_limited = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    # 🔐 LOGIN PROTECTION
    failed_attempts = Column(Integer, default=0)
    blocked_until = Column(DateTime, nullable=True)


class File(Base):
    __tablename__ = "files"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    telegram_file_id = Column(String)
    message_id = Column(Integer)
    file_name = Column(String)
    file_type = Column(String)   # 👈 SHU BORLIGINI TEKSHIR
    file_size = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
