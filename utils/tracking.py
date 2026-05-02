import asyncio
import requests
from bs4 import BeautifulSoup
from typing import Dict, Tuple

from utils.database import (
    get_tracking_status, update_tracking_status,
    check_tracking_exists, get_all_tracking
)
from handlers.bot_instance import bot
from utils.logger_util import logger

tracking_tasks: Dict[Tuple[int, str], asyncio.Task] = {}


async def check_status(tg_id: int, steam_id: str, comment: str):
    url = f"https://steamcommunity.com/profiles/{steam_id}/"

    while True:
        try:
            if not check_tracking_exists(tg_id, steam_id):
                break

            headers = {"User-Agent": "Mozilla/5.0"}
            response = requests.get(url, headers=headers)
            soup = BeautifulSoup(response.text, "html.parser")

            persona_name_element = soup.find("span", class_="actual_persona_name")
            persona_name = persona_name_element.text.strip() if persona_name_element else "Неизвестный пользователь"

            status_element = soup.find("div", class_="profile_in_game_header")
            current_status = status_element.text.strip() if status_element else "Currently Offline"

            simplified_status = "Currently Online" if "in-game" in current_status.lower() or "online" in current_status.lower() else "Currently Offline"

            db_last_status = get_tracking_status(tg_id, steam_id)

            if db_last_status != simplified_status:
                update_tracking_status(tg_id, steam_id, simplified_status)

                if simplified_status == "Currently Online":
                    message = (
                        "🟢 Мамонт зашёл в сеть\n\n"
                        f"🪪 {persona_name}\n"
                        f"💬 \"{comment}\"\n"
                        f"📎 {url}"
                    )
                else:
                    message = (
                        "🔴 Мамонт вышел из сети\n\n"
                        f"🪪 {persona_name}\n"
                        f"💬 \"{comment}\"\n"
                        f"📎 {url}"
                    )

                await bot.send_message(tg_id, message)

            await asyncio.sleep(30)

        except Exception as e:
            print(f"[ERROR] Ошибка при проверке статуса: {e}")
            await asyncio.sleep(60)


async def restore_tracking_tasks():
    rows = get_all_tracking()

    for tg_id, steam_id, comment in rows:
        task = asyncio.create_task(check_status(tg_id, steam_id, comment))
        tracking_tasks[(tg_id, steam_id)] = task