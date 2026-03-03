from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def get_main_menu(lang="uz"):
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📤 Fayl yuklash")],
            [KeyboardButton(text="📂 Mening fayllarim")],
            [KeyboardButton(text="🚪 Logout")]
        ],
        resize_keyboard=True
    )