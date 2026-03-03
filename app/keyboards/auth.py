from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from app.utils.texts import TEXTS


auth_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="🆕 Register"),
            KeyboardButton(text="🔑 Login")
        ]
    ],
    resize_keyboard=True
)



def get_auth_keyboard(lang: str):
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=TEXTS[lang]["register"]),
                KeyboardButton(text=TEXTS[lang]["login"])
            ]
        ],
        resize_keyboard=True
    )