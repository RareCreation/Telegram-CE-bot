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
from utils.steam_parser import is_china_profile

router = Router(name="online_check")


def load(dp: Router) -> None:
    dp.include_router(router)


def normalize_steam_url(url: str):
    url = url.strip().split("?")[0]

    
    if "my.steamchina.com" in url:
        
        pass
    elif "steamchina.com" in url:
        
        url = url.replace("steamchina.com", "my.steamchina.com")
    elif "steamcommunity.com" in url:
        
        pass

    return url


def extract_steam_id_from_url(url: str) -> str:

    match_profile = re.search(r"steamcommunity\.com/profiles/(\d{17})", url)
    if match_profile:
        return match_profile.group(1)

    
    match_china_profile = re.search(r"my\.steamchina\.com/profiles/(\d{17})", url)
    if match_china_profile:
        return match_china_profile.group(1)

    
    match_any = re.search(r"(\d{17})", url)
    if match_any:
        return match_any.group(1)

    return None


async def resolve_steam_id(url: str) -> tuple:

    url = normalize_steam_url(url)
    steam_id = None

    
    match_vanity = re.fullmatch(r"https?://steamcommunity\.com/id/([a-zA-Z0-9_-]+)/?", url)
    if match_vanity:
        steam_id = await resolve_vanity_url(match_vanity.group(1))
        if steam_id:
            
            url = f"https://steamcommunity.com/profiles/{steam_id}/"
        return steam_id, url

    
    match_china_vanity = re.fullmatch(r"https?://my\.steamchina\.com/id/([a-zA-Z0-9_-]+)/?", url)
    if match_china_vanity:
        
        
        
        steam_id = await resolve_vanity_url(match_china_vanity.group(1))
        if steam_id:
            url = f"https://my.steamchina.com/profiles/{steam_id}/"
        return steam_id, url

    
    steam_id = extract_steam_id_from_url(url)

    return steam_id, url


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
    raw_url = message.text.strip()
    url = normalize_steam_url(raw_url)

    
    is_valid_steam_url = (
            "steamcommunity.com" in url or
            "my.steamchina.com" in url or
            "steamchina.com" in url
    )

    if not is_valid_steam_url:
        await message.answer(
            "❌ Неверная ссылка\n\nПожалуйста, отправьте ссылку на профиль Steam (steamcommunity.com или my.steamchina.com)")
        return

    steam_id, normalized_url = await resolve_steam_id(url)

    if not steam_id:
        await message.answer(
            "❌ Не удалось определить Steam ID\n\nПожалуйста, убедитесь что ссылка правильная и попробуйте снова")
        return

    logger.info(f"Received link: {raw_url}")
    logger.info(f"Normalized url: {normalized_url}")
    logger.info(f"Resolved steam_id: {steam_id}")
    logger.info(f"Is China profile: {is_china_profile(normalized_url)}")

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
        conn.close()
        return

    conn.close()

    await state.update_data(steam_id=steam_id, url=normalized_url)
    await message.answer("💬 Напишите комментарий для этого профиля:")
    await state.set_state(OnlineCheckState.waiting_for_comment)


@router.message(OnlineCheckState.waiting_for_comment)
async def handle_profile_comment(message: Message, state: FSMContext):
    comment = message.text.strip()
    data = await state.get_data()

    steam_id = data["steam_id"]
    url = data["url"]
    tg_id = message.from_user.id

    is_china = is_china_profile(url)
    logger.info(f"Saving tracking for China profile: {is_china}")

    conn = sqlite3.connect("tracking.db")
    cursor = conn.cursor()

    
    try:
        cursor.execute("ALTER TABLE tracking ADD COLUMN profile_url TEXT")
    except sqlite3.OperationalError:
        pass  

    cursor.execute(
        "INSERT INTO tracking (tg_id, steam_id, comment, last_status, profile_url) VALUES (?, ?, ?, ?, ?)",
        (tg_id, steam_id, comment, "offline", url)
    )

    conn.commit()
    conn.close()

    logger.info(f"Saving tracking: tg_id={tg_id}, steam_id={steam_id}, comment={comment}, url={url}")

    task = asyncio.create_task(check_status(tg_id, steam_id, comment, url))
    tracking_tasks[(tg_id, steam_id)] = task

    await message.answer(f"✅ Начато отслеживание\n\n{url}\n💬 {comment}")
    await state.clear()