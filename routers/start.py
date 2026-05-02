from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from utils.database import add_user, get_user_count
from utils.constants import PHOTO
from keyboards.main_keyboards import get_main_keyboard

router = Router(name="start")


def load(dp: Router) -> None:
    dp.include_router(router)


@router.message(Command("start"))
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


@router.callback_query(F.data == "back_to_main")
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