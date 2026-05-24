import re
import asyncio
import sqlite3

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from states.states import OnlineCheckState
from keyboards.main_keyboards import get_back_button
from utils.check_status_util import tracking_tasks, check_status
from utils.constants import PHOTO
from utils.logger_util import logger
from utils.steam_api import resolve_vanity_url


router = Router(name="online_check")

def load(dp: Router) -> None:
    dp.include_router(router)


def normalize_steam_url(url: str):
    url = url.strip().split("?")[0]
    url = url.replace("steamchina.com", "steamcommunity.com")
    return url


@router.callback_query(F.data == "online_status")
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


@router.message(OnlineCheckState.waiting_for_profile_link)
async def handle_online_status_link(message: Message, state: FSMContext):
    url = normalize_steam_url(message.text)
    steam_id = None

    match_profile = re.fullmatch(r"https?://steamcommunity\.com/profiles/(\d{17})/?", url)
    if match_profile:
        steam_id = match_profile.group(1)

    match_vanity = re.fullmatch(r"https?://steamcommunity\.com/id/([a-zA-Z0-9_-]+)/?", url)
    if match_vanity:
        steam_id = await resolve_vanity_url(match_vanity.group(1))

    if not steam_id:
        match_any = re.search(r"(\d{17})", url)
        if match_any:
            steam_id = match_any.group(1)

    if not steam_id:
        await message.answer("❌ Неверная ссылка")
        return

    logger.info(f"Received link: {url}")
    logger.info(f"Resolved steam_id: {steam_id}")

    tg_id = message.from_user.id

    conn = sqlite3.connect("tracking.db")
    cursor = conn.cursor()

    cursor.execute(
        "SELECT 1 FROM tracking WHERE tg_id = ? AND steam_id = ?",
        (tg_id, steam_id)
    )

    if cursor.fetchone():
        cursor.execute(
            "DELETE FROM tracking WHERE tg_id = ? AND steam_id = ?",
            (tg_id, steam_id)
        )
        conn.commit()

        task_key = (tg_id, steam_id)
        if task_key in tracking_tasks:
            tracking_tasks[task_key].cancel()
            del tracking_tasks[task_key]

        await message.answer("❌ Отслеживание остановлено")
        await state.clear()
        return

    await state.update_data(steam_id=steam_id, url=url)
    await message.answer("💬 Напишите комментарий для этого профиля:")
    await state.set_state(OnlineCheckState.waiting_for_comment)


@router.message(OnlineCheckState.waiting_for_comment)
async def handle_profile_comment(message: Message, state: FSMContext):
    comment = message.text.strip()
    data = await state.get_data()

    steam_id = data["steam_id"]
    url = data["url"]
    tg_id = message.from_user.id

    conn = sqlite3.connect("tracking.db")
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO tracking (tg_id, steam_id, comment, last_status) VALUES (?, ?, ?, ?)",
        (tg_id, steam_id, comment, "offline")
    )

    conn.commit()
    conn.close()
    logger.info(f"Saving tracking: tg_id={tg_id}, steam_id={steam_id}, comment={comment}")
    task = asyncio.create_task(check_status(tg_id, steam_id, comment))
    tracking_tasks[(tg_id, steam_id)] = task

    await message.answer(f"✅ Начато отслеживание\n\n{url}\n💬 {comment}")
    await state.clear()
