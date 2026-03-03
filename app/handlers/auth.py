from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

from sqlalchemy import select
from datetime import datetime, timedelta

import hashlib
import secrets
import asyncio
import re
from sqlalchemy.exc import IntegrityError

from app.db.session import AsyncSessionLocal
from app.db.models import User
from app.keyboards.main_menu import get_main_menu

router = Router()


# =========================
# FSM STATES
# =========================

class RegisterState(StatesGroup):
    waiting_for_username = State()
    waiting_for_password = State()


class LoginState(StatesGroup):
    waiting_for_username = State()
    waiting_for_password = State()


# =========================
# REGISTER START
# =========================

@router.message(F.text == "📝 Ro'yxatdan o'tish")
async def register_start(message: Message, state: FSMContext):

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(User).where(User.telegram_id == str(message.from_user.id))
        )
        existing_user = result.scalar_one_or_none()

    # Faqat haqiqiy ro‘yxatdan o‘tgan bo‘lsa blokla
    if existing_user and not existing_user.is_limited:
        await message.answer(
            "⚠️ Siz allaqachon ro'yxatdan o'tgansiz!\n\n"
            "Iltimos, tizimga kiring 🔑"
        )
        return

    await message.answer("👤 Username kiriting:")
    await state.set_state(RegisterState.waiting_for_username)

# =========================
# USERNAME
# =========================

@router.message(RegisterState.waiting_for_username)
async def get_username(message: Message, state: FSMContext):

    username = message.text.strip()

    if not re.match(r"^[a-zA-Z0-9_]{3,20}$", username):
        await message.answer(
            "❌ Username faqat harf, raqam va _ dan iborat bo‘lishi kerak.\n"
            "Uzunligi 3–20 belgi oralig‘ida.\n\n"
            "Qaytadan kiriting:"
        )
        return

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(User).where(User.username == username)
        )
        existing_user = result.scalar_one_or_none()

    if existing_user:
        await message.answer(
            "❌ Bu username allaqachon band!\n\n"
            "Boshqa username kiriting:"
        )
        return

    await state.update_data(username=username)
    await message.answer("🔒 Parol kiriting (kamida 6 ta belgi):")
    await state.set_state(RegisterState.waiting_for_password)


# =========================
# PASSWORD
# =========================

@router.message(RegisterState.waiting_for_password)
async def get_password(message: Message, state: FSMContext):

    user_password_message = message
    password = message.text.strip()

    if len(password) < 6:
        await message.answer(
            "❌ Parol kamida 6 ta belgidan iborat bo‘lishi kerak!\n\n"
            "Qaytadan kiriting:"
        )
        return

    data = await state.get_data()
    username = data.get("username")

    if not username:
        await message.answer("❌ Xatolik yuz berdi. Qaytadan urinib ko‘ring.")
        await state.clear()
        return

    password_hash = hashlib.sha256(password.encode()).hexdigest()
    security_key = secrets.token_hex(8)

    async with AsyncSessionLocal() as db:

        new_user = User(
            telegram_id=str(message.from_user.id),
            username=username,
            password_hash=password_hash,
            security_key=security_key,
            language="uz",
            is_logged_in=True,
            is_limited=False,
            failed_attempts=0,
            blocked_until=None
        )


        try:
            db.add(new_user)
            await db.commit()
        except IntegrityError:
            await db.rollback()
            await message.answer("❌ Username allaqachon band!")
            return


    await state.clear()

    success_message = await message.answer(
        f"✅ Muvaffaqiyatli ro'yxatdan o'tdingiz!\n\n"
        f"🔑 Maxfiy kalitingiz:\n{security_key}\n\n"
        f"⚠️ Bu xabar 24 soatdan so‘ng o‘chiriladi."
    )

    await message.answer(
        "🚀 Cloud Vault tayyor 🔐",
        reply_markup=get_main_menu("uz")
    )

    async def delete_later():
        await asyncio.sleep(86400)
        try:
            await success_message.delete()
        except:
            pass
        try:
            await user_password_message.delete()
        except:
            pass

    asyncio.create_task(delete_later())


# =========================
# LOGIN START
# =========================

@router.message(F.text == "🔑 Tizimga kirish")
async def login_start(message: Message, state: FSMContext):
    await message.answer("👤 Username kiriting:")
    await state.set_state(LoginState.waiting_for_username)


# =========================
# LOGIN USERNAME
# =========================

@router.message(LoginState.waiting_for_username)
async def login_username(message: Message, state: FSMContext):

    username = message.text.strip()

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(User).where(User.username == username)
        )
        user = result.scalar_one_or_none()

    if not user:
        await message.answer("❌ Bunday username topilmadi!\nQaytadan kiriting:")
        return

    await state.update_data(username=username)
    await message.answer("🔒 Parol kiriting:")
    await state.set_state(LoginState.waiting_for_password)


# =========================
# LOGIN PASSWORD
# =========================

@router.message(LoginState.waiting_for_password)
async def login_password(message: Message, state: FSMContext):

    password = message.text.strip()
    password_hash = hashlib.sha256(password.encode()).hexdigest()

    data = await state.get_data()
    username = data.get("username")

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(User).where(User.username == username)
        )
        user = result.scalar_one_or_none()

        if not user:
            await message.answer("❌ Foydalanuvchi topilmadi.")
            return

        # BLOCK TEKSHIRUV
        if user.blocked_until and user.blocked_until > datetime.utcnow():
            remaining = (user.blocked_until - datetime.utcnow()).seconds
            await message.answer(
                f"⛔ Siz bloklangansiz!\n"
                f"{remaining // 60} minutdan keyin urinib ko‘ring."
            )
            return

        # ❌ Noto‘g‘ri parol
        if user.password_hash != password_hash:

            user.failed_attempts = (user.failed_attempts or 0) + 1

            if user.failed_attempts >= 3:
                user.blocked_until = datetime.utcnow() + timedelta(minutes=5)
                user.failed_attempts = 0
                await db.commit()

                await message.answer(
                    "⛔ 3 marta noto‘g‘ri parol!\n5 minutga bloklandingiz."
                )
                return

            await db.commit()

            await message.answer(
                f"❌ Parol noto‘g‘ri!\n"
                f"Qolgan urinish: {3 - user.failed_attempts}"
            )
            return

        # ✅ To‘g‘ri parol
        user.failed_attempts = 0
        user.blocked_until = None
        user.is_logged_in = True
        await db.commit()

    await state.clear()

    await message.answer(
        "✅ Muvaffaqiyatli tizimga kirdingiz!\nCloud Vault tayyor 🚀",
        reply_markup=get_main_menu(user.language)
    )