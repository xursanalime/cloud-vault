from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import CommandStart
from sqlalchemy import select

from app.utils.texts import TEXTS
from app.keyboards.auth import get_auth_keyboard
from app.keyboards.language import language_keyboard
from app.keyboards.main_menu import get_main_menu
from app.db.session import AsyncSessionLocal
from app.db.models import User

router = Router()


# =========================
# /start bosilganda
# =========================

@router.message(CommandStart())
async def start_handler(message: Message):

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(User).where(User.telegram_id == str(message.from_user.id))
        )
        user = result.scalar_one_or_none()

    # ❌ User yo‘q yoki til tanlanmagan
    if not user or not user.language:
        await message.answer(
            "🌍 Tilni tanlang / Choose language:",
            reply_markup=language_keyboard
        )
        return

    lang = user.language

    # ✅ Agar login bo‘lgan bo‘lsa → Main Menu
    if user.is_logged_in:
        await message.answer(
            f"🔐 {TEXTS[lang]['welcome']}\n\nCloud Vault tayyor 🚀",
            reply_markup=get_main_menu(lang)
        )
        return

    # ❌ Login qilmagan bo‘lsa → Auth menu
    await message.answer(
        f"{TEXTS[lang]['welcome']}\n\n{TEXTS[lang]['choose_action']}",
        reply_markup=get_auth_keyboard(lang)
    )


# =========================
# Til tanlanganda
# =========================

@router.message(F.text.in_(["🇺🇿 O'zbekcha", "🇷🇺 Русский", "🇬🇧 English"]))
async def language_selected(message: Message):

    if "O'zbekcha" in message.text:
        lang = "uz"
    elif "Русский" in message.text:
        lang = "ru"
    else:
        lang = "en"

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(User).where(User.telegram_id == str(message.from_user.id))
        )
        user = result.scalar_one_or_none()

        # 🔥 Agar user mavjud bo‘lsa tilni update qilamiz
        if user:
            user.language = lang
            await db.commit()

    await message.answer(
        "✅ Til saqlandi!\n\nRo'yxatdan o'tish yoki tizimga kirishni tanlang:",
        reply_markup=get_auth_keyboard(lang)
    )