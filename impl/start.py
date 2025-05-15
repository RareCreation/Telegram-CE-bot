import asyncio
from aiogram import F
from aiogram.filters import Command
from aiogram.types import Message, FSInputFile
from handlers.bot_instance import dp, bot
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from PIL import Image, ImageEnhance
import os
import uuid

from utils.logger_util import logger

SCREENSHOTS_DIR = "screenshots"
if not os.path.exists(SCREENSHOTS_DIR):
    os.makedirs(SCREENSHOTS_DIR)

async def take_screenshot(url: str, filename: str):
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=chrome_options
    )

    try:
        driver.get(url)
        await asyncio.sleep(5)
        driver.save_screenshot(filename)

        img = Image.open(filename)
        width, height = img.size
        cropped_img = img.crop((0, 105, width, height))

        enhancer = ImageEnhance.Brightness(cropped_img)
        darkened_img = enhancer.enhance(0.6)

        try:

            friend_img = Image.open("images/friend.png").convert("RGBA")

            main_width, main_height = darkened_img.size
            friend_width, friend_height = friend_img.size

            position = (
                (main_width - friend_width) // 2,
                (main_height - friend_height) // 2
            )

            darkened_img_rgba = darkened_img.convert("RGBA")

            darkened_img_rgba.alpha_composite(friend_img, dest=position)

            darkened_img_rgba.convert("RGB").save(filename)
        except Exception as e:
            logger(f"Error overlaying friend image: {str(e)}")
            darkened_img.save(filename)
    finally:
        driver.quit()

@dp.message(Command("start"))
async def start_handler(message: Message):
    await message.answer("Отправь мне ссылку на Steam профиль.")

@dp.message(F.text.contains("steamcommunity.com"))
async def process_steam_link(message: Message):
    url = message.text.strip()
    filename = os.path.join(SCREENSHOTS_DIR, f"steam_profile_{uuid.uuid4().hex}.png")

    wait_msg = await message.answer("Обрабатываю...")

    try:
        await take_screenshot(url, filename)
        photo = FSInputFile(filename)
        await message.answer_photo(photo)
        await bot.delete_message(chat_id=message.chat.id, message_id=wait_msg.message_id)
    except Exception as e:
        logger(f"An error occurred: {str(e)}")
    finally:
        if os.path.exists(filename):
            os.remove(filename)
