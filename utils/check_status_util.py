import asyncio
import aiohttp

from handlers.bot_instance import bot
from settings.config import STEAM_API_KEY
from utils.database import check_tracking_exists, get_tracking_status, update_tracking_status
from utils.logger_util import logger


tracking_tasks = {}

async def fetch_status(steam_id: str):
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
        logger.error(f"fetch_status error {steam_id}: {e}")
        return None


def map_status(state: int):
    return "Currently Online" if state == 1 else "Currently Offline"


async def check_status(tg_id: int, steam_id: str, comment: str):
    logger.info(f"Started tracking tg_id={tg_id} steam_id={steam_id}")

    while True:
        try:
            if not check_tracking_exists(tg_id, steam_id):
                logger.info(f"Stopped tracking (DB removed) {steam_id}")
                break

            state = await fetch_status(steam_id)

            if state is None:
                logger.warning(f"State is None for {steam_id}")
                await asyncio.sleep(30)
                continue

            if state == 1:
                simplified_status = "online"
            elif state == 3:
                simplified_status = "away"
            elif state == 0:
                state2 = await fetch_status(steam_id)

                if state2 == 3:
                    simplified_status = "away"
                else:
                    simplified_status = "offline"
            else:
                simplified_status = "offline"

            db_last_status = get_tracking_status(tg_id, steam_id)

            logger.info(f"{steam_id} state={state} -> {simplified_status}")

            if db_last_status != simplified_status:
                update_tracking_status(tg_id, steam_id, simplified_status)

                url = f"https://steamcommunity.com/profiles/{steam_id}/"

                if simplified_status == "online":
                    text = "🟢 Мамонт зашёл в сеть\n\n"
                elif simplified_status == "away":
                    text = "🟡 Мамонт отошёл (Away)\n\n"
                else:
                    text = "🔴 Мамонт вышел из сети\n\n"

                text += f"💬 {comment}\n📎 {url}"

                await bot.send_message(tg_id, text)

                logger.info(f"Status change sent to tg_id={tg_id}")

            await asyncio.sleep(30)

        except Exception as e:
            logger.error(f"check_status loop error {steam_id}: {e}")
            await asyncio.sleep(60)


async def restore_tracking():
    import sqlite3

    conn = sqlite3.connect("tracking.db")
    cursor = conn.cursor()
    cursor.execute("SELECT tg_id, steam_id, comment FROM tracking")
    rows = cursor.fetchall()
    conn.close()

    logger.info(f"Restoring tracking tasks: {len(rows)}")

    for tg_id, steam_id, comment in rows:
        task = asyncio.create_task(check_status(tg_id, steam_id, comment))
        tracking_tasks[(tg_id, steam_id)] = task