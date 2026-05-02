from aiogram import F, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from utils.database import add_user, get_user_count
from utils.constants import PHOTO
from keyboards.main_keyboards import get_main_keyboard


async def start_handler(message: Message, state: FSMContext):
    add_user(message.from_user.id)
    user_count = get_user_count()

    await message.answer_photo(
        photo=PHOTO,
        caption=(
            "🖐 Добро пожаловать в лучший отрисовщик для ворка по CN/EU\n\n"
            "🤝<b> Спасибо что выбрали именно нас!</b>\n\n"
            f"🥷🏻<b> Число</b> юзеров в данном боте - {user_count} 👤"
        ),
        parse_mode="HTML",
        reply_markup=get_main_keyboard()
    )
    await state.clear()


async def back_to_main(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()
    user_count = get_user_count()

    await callback.message.answer_photo(
        photo=PHOTO,
        caption=(
            "🖐 Добро пожаловать в лучший отрисовщик для ворка по CN/EU\n\n"
            "🤝<b> Спасибо что выбрали именно нас!</b>\n\n"
            f"🥷🏻<b> Число</b> юзеров в данном боте - {user_count} 👤"
        ),
        parse_mode="HTML",
        reply_markup=get_main_keyboard()
    )
    await state.clear()


def register_handlers(dp: Dispatcher):
    dp.message.register(start_handler, Command("start"))
    dp.callback_query.register(back_to_main, F.data == "back_to_main")