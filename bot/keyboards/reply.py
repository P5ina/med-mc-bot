from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder

mainMenu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text='🛂 Мой Паспорт'), KeyboardButton(text='🪙 Купить Мёдкоин')]
    ],
    resize_keyboard=True,
)
