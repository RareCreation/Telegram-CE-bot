import asyncio
import aiohttp
import re

from handlers.bot_instance import bot
from settings.config import STEAM_API_KEY
from utils.database import check_tracking_exists, get_tracking_status, update_tracking_status
from utils.logger_util import logger
from utils.steam_parser import parse_steam_profile_status, is_china_profile

tracking_tasks = {}


def extract_steam_id_from_china_url(url: str) -> str:

    match = re.search(r"/profiles/(\d{17})/?", url)
    if match:
        return match.group(1)

    
    match = re.search(r"/id/([^/]+)/?", url)
    if match:
        return match.group(1)  

    return None


async def fetch_status_from_api(steam_id: str) -> int:
    try:
        url = "https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v2/"
        params = {"key": STEAM_API_KEY, "steamids": steam_id}

        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as resp:
                data = await resp.json()

        players = data.get("response", {}).get("players", [])
        if not players:
            logger.warning(f"No player data for {steam_id}")
            return None

        return players[0].get("personastate", 0)

    except Exception as e:
        logger.error(f"fetch_status_from_api error {steam_id}: {e}")
        return None


async def fetch_status_from_web(profile_url: str) -> int:
    try:
        result = parse_steam_profile_status(profile_url)

        if is_china_profile(profile_url):
            logger.info(f"China profile parse result: {result}")
            if result:
                logger.info(f"China profile status_code: {result.get('status_code')}, status_text: {result.get('status_text')}")

        if result and result.get("status_code") is not None:
            logger.debug(f"Web parse for {profile_url}: {result}")
            return result["status_code"]

        return None

    except Exception as e:
        logger.error(f"fetch_status_from_web error {profile_url}: {e}")
        return None

async def fetch_status(steam_id: str, profile_url: str = None) -> int:

    
    if profile_url and is_china_profile(profile_url):
        web_status = await fetch_status_from_web(profile_url)

        if web_status is not None:
            return web_status

        return 0

    
    api_status = await fetch_status_from_api(steam_id)

    if api_status is not None:
        return api_status

    
    if profile_url:
        web_status = await fetch_status_from_web(profile_url)

        if web_status is not None:
            return web_status

    return None


def map_status(state: int) -> str:
    if state == 1:
        return "online"
    elif state == 2:
        return "away"  
    elif state == 3:
        return "away"  
    elif state == 4:
        return "away"  
    else:
        return "offline"


def get_status_text(state: int) -> tuple:

    if state == 1:
        return "🟢", "Мамонт зашёл в сеть"
    elif state in (2, 3, 4):
        return "🟡", "Мамонт отошёл (Away)"
    else:
        return "🔴", "Мамонт вышел из сети"


async def check_status(tg_id: int, steam_id: str, comment: str, profile_url: str):
    is_china = is_china_profile(profile_url)
    logger.info(
        f"Started tracking {'CHINA' if is_china else 'STEAM'} profile: tg_id={tg_id} steam_id={steam_id} url={profile_url}")

    while True:
        try:
            if not check_tracking_exists(tg_id, steam_id):
                logger.info(f"Stopped tracking (DB removed) {steam_id}")
                break


            state = await fetch_status(steam_id, profile_url)

            if state is None:
                logger.warning(f"State is None for {steam_id}")
                await asyncio.sleep(60)
                continue

            simplified_status = map_status(state)


            db_last_status = get_tracking_status(tg_id, steam_id)


            profile_type = "CHINA" if is_china else "STEAM"
            logger.info(f"[{profile_type}] {steam_id} state={state} -> {simplified_status} (last: {db_last_status})")


            if db_last_status != simplified_status:
                update_tracking_status(tg_id, steam_id, simplified_status)

                emoji, status_text = get_status_text(state)


                if state == 1:
                    text = f"{emoji} {status_text}\n\n"
                elif state in (2, 3, 4):
                    text = f"{emoji} {status_text}\n\n"
                else:
                    text = f"{emoji} {status_text}\n\n"

                text += f"💬 {comment}\n📎 {profile_url}"


                await bot.send_message(tg_id, text)

                logger.info(
                    f"Status change sent to tg_id={tg_id} for {'CHINA' if is_china else 'STEAM'} profile {steam_id}")


            sleep_interval = 45 if is_china else 30
            await asyncio.sleep(sleep_interval)

        except asyncio.CancelledError:
            logger.info(f"Tracking cancelled for {steam_id}")
            break
        except Exception as e:
            logger.error(f"check_status loop error {steam_id}: {e}")
            await asyncio.sleep(10)


async def restore_tracking():
    import sqlite3

    conn = sqlite3.connect("tracking.db")
    cursor = conn.cursor()
    cursor.execute("SELECT tg_id, steam_id, comment, profile_url FROM tracking")
    rows = cursor.fetchall()
    conn.close()

    logger.info(f"Restoring tracking tasks: {len(rows)}")

    for tg_id, steam_id, comment, profile_url in rows:
        task = asyncio.create_task(check_status(tg_id, steam_id, comment, profile_url))
        tracking_tasks[(tg_id, steam_id)] = task