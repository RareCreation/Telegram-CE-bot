import re
import asyncio
from aiogram import F, Dispatcher
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from states.states import OnlineCheckState
from keyboards.main_keyboards import get_back_button
from utils.constants import PHOTO, TRACKING_LIMIT
from utils.database import (
    check_tracking_exists, remove_tracking, get_tracking_count,
    add_tracking, get_tracking_status, update_tracking_status
)
from utils.steam_parser import extract_steam_id
from utils.tracking import tracking_tasks, check_status


async def on_online_status(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()
    caption = (
        "> 🔍 Чекер статуса\n"
        "> ╰ уведомляет об изменениях статуса мамонта\n\n"
        "📎 *Отправь ссылку на профиль мамонта:*\n\n"
        "❗️*Внимание:* Если вписать ссылку на профиль, который вы уже отслеживаете \\- "
        "бот выключит отслеживание данного участника\\."
    )

    await callback.message.answer_photo(
        photo=PHOTO,
        caption=caption,
        parse_mode="MarkdownV2",
        reply_markup=get_back_button()
    )
    await state.set_state(OnlineCheckState.waiting_for_profile_link)


async def handle_online_status_link(message: Message, state: FSMContext):
    url = message.text.strip()
    steam_id = extract_steam_id(url)

    if not steam_id:
        await message.answer("❌ Ошибка: Неверный формат ссылки. Пример: https://steamcommunity.com/profiles/7656119...")
        return

    tg_id = message.from_user.id

    if check_tracking_exists(tg_id, steam_id):
        remove_tracking(tg_id, steam_id)

        task_key = (tg_id, steam_id)
        if task_key in tracking_tasks:
            tracking_tasks[task_key].cancel()
            del tracking_tasks[task_key]

        await message.answer(f"❌ Отслеживание профиля {steam_id} остановлено.")
        await state.clear()
        return

    count = get_tracking_count(tg_id)

    if count >= TRACKING_LIMIT:
        await message.answer(f"❌ Вы достигли лимита отслеживаемых профилей ({TRACKING_LIMIT}).")
        await state.clear()
        return

    await state.update_data(steam_id=steam_id, url=url)
    await message.answer("💬 Напишите комментарий для этого профиля:")
    await state.set_state(OnlineCheckState.waiting_for_comment)


async def handle_profile_comment(message: Message, state: FSMContext):
    comment = message.text.strip()
    data = await state.get_data()
    steam_id = data['steam_id']
    url = data['url']
    tg_id = message.from_user.id

    add_tracking(tg_id, steam_id, comment, "Currently Offline")

    task = asyncio.create_task(check_status(tg_id, steam_id, comment))
    tracking_tasks[(tg_id, steam_id)] = task

    await message.answer(f"✅ Отслеживание профиля начато\n\n"
                         f"📎 {url}\n"
                         f"💬 Комментарий: \"{comment}\"")
    await state.clear()


def register_handlers(dp: Dispatcher):
    dp.callback_query.register(on_online_status, F.data == "online_status")
    dp.message.register(handle_online_status_link, OnlineCheckState.waiting_for_profile_link)
    dp.message.register(handle_profile_comment, OnlineCheckState.waiting_for_comment)