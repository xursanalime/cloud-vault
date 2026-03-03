from aiogram import Router, F
from aiogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery
)
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter

from sqlalchemy import select, func
from collections import defaultdict
import asyncio

from app.db.session import AsyncSessionLocal
from app.db.models import User, File
from app.config import CHANNEL_ID

router = Router()
media_groups = defaultdict(list)


# =================================================
# STATES
# =================================================

class UploadState(StatesGroup):
    waiting_for_filename = State()
    waiting_for_confirmation = State()
    waiting_for_file = State()


# =================================================
# CONFIRM KEYBOARD
# =================================================

confirm_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Ha", callback_data="confirm_yes"),
            InlineKeyboardButton(text="❌ Yo‘q", callback_data="confirm_no"),
        ]
    ]
)


# @router.message()
# async def debug_all(message: Message):
#     print("DEBUG:", message.text)
# =================================================
# GLOBAL: MENING FAYLLARIM (HAR DOIM ISHLAYDI)
# =================================================
@router.message(F.text.contains("Mening fayllarim"))
async def my_files(message: Message, state: FSMContext):

    print("MY_FILES HANDLER ISHLADI")

    await state.clear()

    async with AsyncSessionLocal() as db:

        result = await db.execute(
            select(User).where(User.telegram_id == str(message.from_user.id))
        )
        user = result.scalars().first()

        if not user:
            await message.answer("❌ Avval tizimga kiring.")
            return

        result = await db.execute(
            select(File.file_name, func.count(File.id))
            .where(File.user_id == user.id)
            .group_by(File.file_name)
        )
        # 🔥 STATISTIKA
        result_stats = await db.execute(
            select(
                func.count(File.id),
                func.coalesce(func.sum(File.file_size), 0)
            ).where(File.user_id == user.id)
        )

        total_files, total_size = result_stats.first()

        mb = round(total_size / (1024 * 1024), 2)


        files = result.all()

        if not files:
            await message.answer("📭 Sizda hali fayllar yo‘q.")
            return

        keyboard = [
            [
                InlineKeyboardButton(
                    text=f"📂 {name} ({count} ta)",
                    callback_data=f"open_{name}"
                )
            ]
            for name, count in files
        ]

        text = (
            f"📊 {total_files} ta fayl\n"
            f"💾 {mb} MB ishlatilgan\n\n"
            "📁 Sizning fayllaringiz:"
        )

        await message.answer(
            text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
# =================================================
# START UPLOAD
# =================================================

@router.message(F.text == "📤 Fayl yuklash")
async def start_upload(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("📝 Fayl nomini kiriting:")
    await state.set_state(UploadState.waiting_for_filename)


# =================================================
# GET FILE NAME
# =================================================

@router.message(UploadState.waiting_for_filename)
async def get_filename(message: Message, state: FSMContext):

    file_name = message.text.strip()

    if len(file_name) < 2:
        await message.answer("❌ Nom juda qisqa.")
        return

    async with AsyncSessionLocal() as db:

        result_user = await db.execute(
            select(User).where(User.telegram_id == str(message.from_user.id))
        )
        user = result_user.scalar_one_or_none()

        if not user or not user.is_logged_in:
            await message.answer("❌ Avval tizimga kiring.")
            await state.clear()
            return

        result = await db.execute(
            select(File.id).where(
                File.user_id == user.id,
                File.file_name == file_name
            )
        )

        exists = result.first()

    await state.update_data(file_name=file_name)

    if exists:
        await message.answer(
            f'⚠️ "{file_name}" mavjud.\n'
            f'Shu faylga qo‘shmoqchimisiz?',
            reply_markup=confirm_keyboard
        )
        await state.set_state(UploadState.waiting_for_confirmation)
    else:
        await message.answer("📎 Endi faylni yuboring:")
        await state.set_state(UploadState.waiting_for_file)


# =================================================
# CONFIRM YES
# =================================================

@router.callback_query(F.data == "confirm_yes")
async def confirm_yes(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("📎 Endi faylni yuboring:")
    await state.set_state(UploadState.waiting_for_file)
    await callback.answer()


# =================================================
# CONFIRM NO
# =================================================

@router.callback_query(F.data == "confirm_no")
async def confirm_no(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("📝 Yangi fayl nomini kiriting:")
    await state.set_state(UploadState.waiting_for_filename)
    await callback.answer()


# =================================================
# SAVE FILE (MEDIA GROUP SUPPORT)
# =================================================

@router.message(
    UploadState.waiting_for_file,
    F.document | F.photo | F.video | F.audio
)
async def save_file(message: Message, state: FSMContext):

    group_id = message.media_group_id

    if group_id:
        media_groups[group_id].append(message)
        await asyncio.sleep(0.8)

        if group_id not in media_groups:
            return

        messages = media_groups.pop(group_id)
        await process_files(messages, state)
    else:
        await process_files([message], state)


# =================================================
# PROCESS FILES
# =================================================

async def process_files(messages, state: FSMContext):

    data = await state.get_data()
    file_name = data.get("file_name")

    async with AsyncSessionLocal() as db:

        result_user = await db.execute(
            select(User).where(
                User.telegram_id == str(messages[0].from_user.id)
            )
        )
        user = result_user.scalar_one_or_none()

        if not user:
            await messages[0].answer("❌ Foydalanuvchi topilmadi.")
            await state.clear()
            return

        count = 0

        for msg in messages:

            sent = await msg.copy_to(CHANNEL_ID)

            if msg.document:
                file_id = msg.document.file_id
                file_size = msg.document.file_size

            elif msg.photo:
                file_id = msg.photo[-1].file_id
                file_size = msg.photo[-1].file_size

            elif msg.video:
                file_id = msg.video.file_id
                file_size = msg.video.file_size

            elif msg.audio:
                file_id = msg.audio.file_id
                file_size = msg.audio.file_size

            else:
                continue

            db.add(
                File(
                    user_id=user.id,
                    telegram_file_id=file_id,
                    message_id=sent.message_id,
                    file_name=file_name,
                    file_type=msg.content_type,
                    file_size=file_size
                )
            )

            count += 1

        await db.commit()

    await messages[0].answer(
        f"📦 {count} ta fayl muvaffaqiyatli saqlandi 🔐"
    )

    await state.clear()


# =================================================
# WRONG INPUT
# =================================================

@router.message(
    UploadState.waiting_for_file,
    ~(
        F.document |
        F.photo |
        F.video |
        F.audio
    )
)
async def wrong_input(message: Message):
    await message.answer("❌ Iltimos fayl yuboring.")


# =================================================
# OPEN FILE GROUP
# =================================================

@router.callback_query(F.data.startswith("open_"))
async def open_file(callback: CallbackQuery):

    file_name = callback.data.replace("open_", "")

    async with AsyncSessionLocal() as db:

        result_user = await db.execute(
            select(User).where(User.telegram_id == str(callback.from_user.id))
        )
        user = result_user.scalar_one_or_none()

        result_files = await db.execute(
            select(File).where(
                File.user_id == user.id,
                File.file_name == file_name
            )
        )

        files = result_files.scalars().all()

        if not files:
            await callback.answer("Fayl topilmadi.", show_alert=True)
            return

        await callback.message.answer(
            f'📂 "{file_name}" ichida {len(files)} ta fayl mavjud.'
        )

        for file in files:
            await callback.bot.copy_message(
                chat_id=callback.from_user.id,
                from_chat_id=CHANNEL_ID,
                message_id=file.message_id
            )
    await callback.answer()