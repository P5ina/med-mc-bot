import logging

from aiogram import Bot, Dispatcher, Router, types, F
from aiogram.filters import Command, Text
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, ReplyKeyboardRemove, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from pony.orm import *

from bot.database import db, User
from bot.keyboards import mainMenu
from bot.misc import TgKeys, Config

router = Router()
bot = Bot(TgKeys.TOKEN, parse_mode="HTML")


class NicknameForm(StatesGroup):
    nickname = State()


class PassportForm(StatesGroup):
    full_name = State()
    family = State()
    age = State()
    address = State()


@router.message(Command(commands=["start"]))
async def command_start_handler(message: Message, state: FSMContext) -> None:
    with db_session:
        u = User.get(telegram_user_id=message.from_user.id)
    if u is not None:
        if u.verified:
            await message.answer(f"У вас уже привязан аккаунт, можете продолжать пользоваться ботом",
                                 reply_markup=mainMenu)
        else:
            await message.answer(f"У вас уже привязан аккаунт, ожидайте подтверждения аккаунта",
                                 reply_markup=ReplyKeyboardRemove())
        return

    await state.set_state(NicknameForm.nickname)
    await message.answer(f"Привет, введите ваш никнейм в Minecraft:", reply_markup=ReplyKeyboardRemove())


@router.message(Command("cancel"))
@router.message(F.text.casefold() == "отмена")
async def cancel_handler(message: Message, state: FSMContext) -> None:
    """
    Allow user to cancel any action
    """
    current_state = await state.get_state()
    if current_state is None:
        return

    logging.info("Cancelling state %r", current_state)
    await state.clear()
    await message.answer(
        "Отменено.",
        reply_markup=mainMenu,
    )


@router.message(NicknameForm.nickname)
async def nickname_entered_handler(message: Message, state: FSMContext) -> None:
    data = await state.update_data(nickname=message.text)
    await state.clear()
    with db_session:
        User(telegram_user_id=message.from_user.id, minecraft_nickname=data['nickname'])
    menu = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text='✅ Подтвердить', callback_data=f"confirm_account_{message.from_user.id}"),
                InlineKeyboardButton(text='❌ Отклонить', callback_data=f"cancel_account_{message.from_user.id}"),
            ]
        ]
    )
    for admin_id in Config.ADMINS:
        await bot.send_message(admin_id,
                               "Подтвердите создание аккаунта, " +
                               f"<a href=\"tg://user?id={message.from_user.id}\">{message.from_user.first_name}</a> " +
                               f"хочет создать аккаунт с ником {data['nickname']}",
                               reply_markup=menu)
    await message.answer(f"Отлично, {message.from_user.first_name} (AKA {data['nickname']}), " +
                         "ожидайте подтверждения от модератора ⏳")


@router.message(Command(commands=["request_passport"]))
async def command_request_passport_handler(message: Message, state: FSMContext) -> None:
    await state.set_state(PassportForm.full_name)
    await message.answer(f"Введите ваше полное имя (не реальное):", reply_markup=ReplyKeyboardRemove())


@router.message(Command(commands=["add_police"]))
async def command_request_passport_handler(message: Message, state: FSMContext) -> None:
    await state.set_state(PassportForm.full_name)
    await message.answer(f"Введите ваше полное имя (не реальное):", reply_markup=ReplyKeyboardRemove())


@router.message(F.text == "🛂 Мой Паспорт")
async def show_passport_handler(message: Message) -> None:
    await message.answer("У вас еще нет паспорта. Хотите запросить создание? \n/request_passport")


@router.message()
async def echo_handler(message: types.Message) -> None:
    await message.answer("🤨 Не понимаю вас. Выберите команду на клавиатуре.")


@router.callback_query(Text(startswith="confirm_account_"))
async def callback_query_handler(callback_query: CallbackQuery) -> None:
    telegram_user_id = int(callback_query.data.split('_')[2])

    with db_session:
        u = User.get(telegram_user_id=telegram_user_id)
        if u is None:
            message = "Аккаунт уже отклонен или не существует!"
        else:
            if u.verified:
                message = "Аккаунт уже подтвержден."
            else:
                u.verified = True
                await bot.send_message(u.telegram_user_id,
                                       "Аккаунт подтвержден, теперь вам доступны все функции бота",
                                       reply_markup=mainMenu)
                message = "Аккаунт подтвержден."

    await callback_query.message.answer(message)
    await callback_query.answer()


@router.callback_query(Text(startswith="cancel_account_"))
async def callback_query_handler(callback_query: CallbackQuery) -> None:
    telegram_user_id = int(callback_query.data.split('_')[2])

    with db_session:
        u = User.get(telegram_user_id=telegram_user_id)
        if u is None:
            message = "Аккаунт уже отклонен или не существует!"
        else:
            if u.verified:
                message = "Аккаунт уже подтвержден."
            else:
                u.delete()
                await bot.send_message(u.telegram_user_id,
                                       "Аккаунт отклонен, напишите еще раз /start, " +
                                       "чтобы подать новую заявку")
                message = "Аккаунт отклонен."

    await callback_query.message.answer(message)
    await callback_query.answer()


async def start_bot() -> None:
    set_sql_debug(True)
    db.bind(provider='sqlite', filename='database.sqlite', create_db=True)
    db.generate_mapping(create_tables=True)

    dp = Dispatcher()
    dp.include_router(router)

    await dp.start_polling(bot)
