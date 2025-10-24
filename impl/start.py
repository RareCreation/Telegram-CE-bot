import os
import re
import uuid
from io import BytesIO
import sqlite3
from typing import Dict, Tuple
import asyncio
import cv2
import numpy as np
import requests
from PIL import Image, ImageDraw, ImageFont
from aiogram import F, types
from aiogram.filters import Command
from aiogram.types import Message, FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, BufferedInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

from settings.config import ADMINS
from utils.qrgenerate import generate_styled_qr
from utils.screenshot import take_screenshot, take_screenshot_second
from handlers.bot_instance import bot, dp
from utils.logger_util import logger
from utils.qr_image_handler import process_qr_image, add_noise_to_center_area, darken_image, \
    rotate_image_with_transparency, process_qr_image2

photo = FSInputFile("images/banner.png")

def init_db():
    conn = sqlite3.connect('tracking.db')
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS tracking (
        tg_id INTEGER,
        steam_id TEXT,
        comment TEXT,
        last_status TEXT,
        PRIMARY KEY (tg_id, steam_id)
    )
    ''')
    conn.commit()
    conn.close()

def init_users_db():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        tg_id INTEGER PRIMARY KEY
    )
    ''')
    conn.commit()
    conn.close()

init_db()
init_users_db()

def add_user(tg_id: int):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT tg_id FROM users WHERE tg_id = ?', (tg_id,))
    if cursor.fetchone() is None:
        cursor.execute('INSERT INTO users (tg_id) VALUES (?)', (tg_id,))
    conn.commit()
    conn.close()

def get_user_count() -> int:
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM users')
    count = cursor.fetchone()[0]
    conn.close()
    return count

SCREENSHOTS_DIR = "screenshots"

if not os.path.exists(SCREENSHOTS_DIR):
    os.makedirs(SCREENSHOTS_DIR)

class LinkState(StatesGroup):
    waiting_for_action = State()
    link_saved = State()

class BanMMState(StatesGroup):
    waiting_for_photo = State()

class QrCodeState(StatesGroup):
    waiting_for_photo = State()

class QrCodeEState(StatesGroup):
    waiting_for_photo = State()

class OnlineCheckState(StatesGroup):
    waiting_for_profile_link = State()
    waiting_for_comment = State()

users = 0

class BanDefDotaState(StatesGroup):
    waiting_for_photo = State()

@dp.message(Command("start"))
async def start_handler(message: Message, state: FSMContext):
    add_user(message.from_user.id)
    user_count = get_user_count()

    await message.answer_photo(
        photo=photo,
        caption=(
            "🖐 Добро пожаловать в лучший отрисовщик для ворка по CN/EU\n\n"
            "🤝<b> Спасибо что выбрали именно нас!</b>\n\n"
            f"🥷🏻<b> Число</b> юзеров в данном боте - {user_count} 👤"
        ),
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🫂 Add Friend", callback_data="add_friend")],
                [InlineKeyboardButton(text="⚠️ Ban DOTA2", callback_data="ban_dota")],
                [InlineKeyboardButton(text="🟢 Check-online", callback_data="online_status")],
                [InlineKeyboardButton(text="📱 QR Friend Page", callback_data="qr_friend_page")],
                [InlineKeyboardButton(text="📨 Friend Page", callback_data="friend_page")],
            ]
        )
    )

    await state.clear()

@dp.callback_query(F.data == "default_ban")
async def ask_for_ban_default_dota_photo(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Отправьте фотографию с лобби в DOTA2:")
    await state.set_state(BanDefDotaState.waiting_for_photo)
    await callback.answer()

@dp.message(BanDefDotaState.waiting_for_photo)
async def process_ban_default_dota_photo(message: Message, state: FSMContext):
    if not message.photo:
        await message.answer("❌ Пожалуйста, пришлите именно фото.")
        return

    photo = message.photo[-1]
    photo_file = await bot.get_file(photo.file_id)
    photo_bytes = await bot.download_file(photo_file.file_path)
    img = Image.open(photo_bytes)


    left_cut = 21
    right_cut = 1015
    top_cut = 66
    bottom_cut = 13

    width, height = img.size


    cropped = img.crop((
        left_cut,
        top_cut,
        width - right_cut,
        height - bottom_cut
    ))

    new_width = cropped.width + 4
    new_height = cropped.height + 10

    stretched = cropped.resize((new_width, new_height), Image.LANCZOS)

    template_path = "images/ban.jpg"
    ban_img = Image.open(template_path).convert("RGBA")

    ban_img.paste(stretched, (18, 63))

    output_buffer = BytesIO()
    ban_img.save(output_buffer, format="PNG")
    output_buffer.seek(0)

    await message.answer_photo(
        BufferedInputFile(output_buffer.getvalue(), filename="ban_preview.png")
    )

    await state.clear()



class MessageState(StatesGroup):
    waiting_for_text = State()


@dp.message(Command("message"))
async def start_message_broadcast(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMINS:
        await message.reply("🚫 У вас нет прав для использования этой команды.")
        return

    await message.answer("📝 Введите сообщение, которое хотите отправить всем пользователям.")
    await state.set_state(MessageState.waiting_for_text)


@dp.message(MessageState.waiting_for_text)
async def process_broadcast_text(message: types.Message, state: FSMContext):
    text = message.html_text
    await state.clear()

    await message.answer("📤 Начинаю отправлять сообщения ...")


    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("SELECT tg_id FROM users")
    users = [row[0] for row in cursor.fetchall()]
    conn.close()

    success = 0
    failed = 0

    for user_id in users:
        try:
            await bot.send_message(chat_id=user_id, text=text, parse_mode="HTML")
            success += 1
            await asyncio.sleep(0.05)
        except Exception:
            failed += 1
            continue

    await message.answer(f"✅ Рассылка завершена!\n\n"
                         f"📨 Успешно: {success}\n"
                         f"⚠️ Ошибок: {failed}")

tracking_tasks: Dict[Tuple[int, str], asyncio.Task] = {}

async def check_status(tg_id: int, steam_id: str, comment: str):
    url = f"https://steamcommunity.com/profiles/{steam_id}/"
    last_status = None

    while True:
        try:
            conn = sqlite3.connect('tracking.db')
            cursor = conn.cursor()

            cursor.execute('SELECT 1 FROM tracking WHERE tg_id = ? AND steam_id = ?', (tg_id, steam_id))
            if not cursor.fetchone():
                break

            headers = {"User-Agent": "Mozilla/5.0"}
            response = requests.get(url, headers=headers)
            soup = BeautifulSoup(response.text, "html.parser")

            persona_name_element = soup.find("span", class_="actual_persona_name")
            persona_name = persona_name_element.text.strip() if persona_name_element else "Неизвестный пользователь"

            status_element = soup.find("div", class_="profile_in_game_header")
            current_status = status_element.text.strip() if status_element else "Currently Offline"

            simplified_status = "Currently Online" if "in-game" in current_status.lower() or "online" in current_status.lower() else "Currently Offline"

            cursor.execute('SELECT last_status FROM tracking WHERE tg_id = ? AND steam_id = ?', (tg_id, steam_id))
            row = cursor.fetchone()
            db_last_status = row[0] if row else None

            if db_last_status != simplified_status:
                cursor.execute('UPDATE tracking SET last_status = ? WHERE tg_id = ? AND steam_id = ?',
                               (simplified_status, tg_id, steam_id))
                conn.commit()

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
        finally:
            conn.close()


class QrFriendState(StatesGroup):
    waiting_for_link = State()
    waiting_for_time = State()

class FriendState(StatesGroup):
    waiting_for_link = State()

@dp.callback_query(F.data == "friend_page")
async def on_friend_page(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()
    caption = (
        "<blockquote>📨Friend Page\n         ╰ Отрисовка  страницы с кодом друга и с дружественной ссылкой на странице Steam.\n         ╰  🚫 Friend Page not found - отрисовка не найденного кода друга из за разных регионов.</blockquote>"

    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📨 Friend Page", callback_data="friend_page_image")],
            [InlineKeyboardButton(text="🚫 Friend Page not found", callback_data="friend_not_found")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main")]
        ]
    )
    await callback.message.answer_photo(
        photo,
        caption=caption,
        parse_mode="HTML",
        reply_markup=keyboard
    )


class FriendNotFoundState(StatesGroup):
    waiting_for_link = State()
    waiting_for_id = State()


@dp.callback_query(F.data == "friend_not_found")
async def on_friend_not_found(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()
    caption = (
        "👀 Отправь fake-invite ссылку:\n\n"
        "❗️ Для корректной работы отрисовщика, сначала зайдите сами на ссылку и следом скопируйте адрес из адресной строки\n\n❗️ Проверяйте так всегда, ибо клоака — вещь нетулочная"
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main")]]
    )
    await callback.message.answer_photo(
        photo,
        caption=caption,
        parse_mode="HTML",
        reply_markup=keyboard
    )
    await state.set_state(FriendNotFoundState.waiting_for_link)


@dp.message(FriendNotFoundState.waiting_for_link)
async def process_friend_not_found_link(message: Message, state: FSMContext):
    try:
        url = message.text.strip()

        processing_msg = await message.answer("⏳ Обработка...")

        frame_url, avatar_url, persona_name = parse_steam_profile_images(url)

        if not avatar_url:
            await processing_msg.delete()
            await message.answer("❌ Не удалось найти аватарку в профиле. Проверьте ссылку.")
            return

        await state.update_data(
            frame_url=frame_url,
            avatar_url=avatar_url,
            persona_name=persona_name,
            profile_url=url
        )

        await processing_msg.delete()


        caption = "Отправьте код друга китайца:"

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data="friend_page")]]
        )

        await message.answer(
            caption,
            parse_mode="HTML",
            reply_markup=keyboard
        )
        await state.set_state(FriendNotFoundState.waiting_for_id)

    except Exception as e:
        logger(f"Error in friend not found link processing: {e}")
        await message.answer("❌ Произошла ошибка при обработке профиля. Попробуйте еще раз.")
        await state.clear()


@dp.message(FriendNotFoundState.waiting_for_id)
async def process_friend_not_found_id(message: Message, state: FSMContext):
    try:
        user_id = message.text.strip()

        processing_msg = await message.answer("⏳ Обработка...")

        data = await state.get_data()
        frame_url = data.get('frame_url')
        avatar_url = data.get('avatar_url')
        persona_name = data.get('persona_name')
        profile_url = data.get('profile_url')

        await processing_msg.edit_text("⏳ Обработка изображений...")


        combined_image = combine_friend_not_found_images(
            frame_url,
            avatar_url,
            persona_name,
            profile_url,
            user_id
        )

        await processing_msg.edit_text("⏳ Отправка результата...")

        result_file = BufferedInputFile(combined_image.getvalue(), filename="friend_not_found_result.png")

        await message.answer_photo(
            result_file,
            parse_mode="MarkdownV2"
        )

        await processing_msg.delete()
        await state.clear()

    except Exception as e:
        logger(f"Error in friend not found ID processing: {e}")
        await message.answer("❌ Произошла ошибка при создании изображения. Попробуйте еще раз.")
        await state.clear()


def combine_friend_not_found_images(frame_url: str, avatar_url: str, persona_name: str, profile_url: str,
                                    user_id: str) -> BytesIO:
    try:

        background_path = "images/photo3.jpg"
        background_image = Image.open(background_path).convert('RGBA')

        avatar_size = (40, 40)
        frame_size = (50, 50)

        if avatar_url:
            avatar_response = requests.get(avatar_url)
            avatar_image = Image.open(BytesIO(avatar_response.content)).convert('RGBA')
            avatar_image = avatar_image.resize(avatar_size, Image.Resampling.LANCZOS)
        else:
            raise ValueError("Avatar URL is required")

        combined_image = Image.new('RGBA', frame_size, (0, 0, 0, 0))

        avatar_position = (
            (frame_size[0] - avatar_size[0]) // 2,
            (frame_size[1] - avatar_size[1]) // 2
        )

        combined_image.paste(avatar_image, avatar_position)

        if frame_url:
            frame_response = requests.get(frame_url)
            frame_image = Image.open(BytesIO(frame_response.content)).convert('RGBA')
            frame_image = frame_image.resize(frame_size, Image.Resampling.LANCZOS)
            combined_image = Image.alpha_composite(combined_image, frame_image)

        main_position = (250, 90)

        result_image = background_image.copy()
        result_image.paste(combined_image, main_position, combined_image)

        small_avatar_size = (avatar_size[0] // 2, avatar_size[1] // 2)
        small_avatar_image = avatar_image.resize(small_avatar_size, Image.Resampling.LANCZOS)

        small_frame_size = (small_avatar_size[0] + 4, small_avatar_size[1] + 4)
        small_frame_image = Image.new('RGBA', small_frame_size, (80, 80, 80, 255))

        small_avatar_position_in_frame = (
            (small_frame_size[0] - small_avatar_size[0]) // 2,
            (small_frame_size[1] - small_avatar_size[1]) // 2
        )

        small_frame_image.paste(small_avatar_image, small_avatar_position_in_frame, small_avatar_image)

        small_avatar_position = (result_image.width - small_frame_size[0] - 335, 7)

        result_image.paste(small_frame_image, small_avatar_position, small_frame_image)

        draw = ImageDraw.Draw(result_image)


        font = ImageFont.truetype("fonts/NotoSans-Medium.ttf", 20)
        text_x = main_position[0] + frame_size[0] + 10
        text_y = main_position[1] + (frame_size[1] - 20) // 2 - 10
        draw.text((text_x, text_y), persona_name, fill=(220, 220, 220), font=font)

        font = ImageFont.truetype("fonts/NotoSans-Medium.ttf", 9)

        base_small_avatar_position = (result_image.width - small_avatar_size[0] - 375, 6)

        text_length = len(persona_name)
        if text_length > 4:
            compensation = (text_length - 4) * 5 + 2
            small_avatar_position = (base_small_avatar_position[0] - compensation, base_small_avatar_position[1])
        else:
            small_avatar_position = base_small_avatar_position

        draw.text(small_avatar_position, persona_name, fill=(205, 205, 205), font=font)




        id_font = ImageFont.truetype("fonts/NotoSans-Medium.ttf", 10)


        id_bbox = draw.textbbox((0, 0), user_id, font=id_font)
        id_width = id_bbox[2] - id_bbox[0]
        id_height = id_bbox[3] - id_bbox[1]


        id_position_x = (result_image.width - id_width) // 2 - 165
        id_position_y = (result_image.height - id_height) // 2 - 51


        draw.text(
            (id_position_x, id_position_y),
            user_id,
            fill=(98, 101, 107),
            font=id_font
        )
        url_font = ImageFont.truetype("fonts/NotoSans-Medium.ttf", 10)

        url_bbox = draw.textbbox((0, 0), profile_url, font=url_font)
        url_width = url_bbox[2] - url_bbox[0]
        url_height = url_bbox[3] - url_bbox[1]

        url_position_x = (result_image.width - url_width) // 2 - 82
        url_position_y = (result_image.height - url_height) // 2 + 174

        draw.text(
            (url_position_x, url_position_y),
            profile_url,
            fill=(255, 255, 255),
            font=url_font
        )

        output = BytesIO()
        result_image.save(output, format='PNG')
        output.seek(0)

        return output

    except Exception as e:
        logger(f"Error combining friend not found images: {e}")
        raise

@dp.callback_query(F.data == "friend_page_image")
async def on_friend_page(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()
    caption = (
        "👀 Отправь fake-invite ссылку:\n\n"
        "❗️ Для корректной работы отрисовщика, сначала зайдите сами на ссылку и следом скопируйте адрес из адресной строки\n\n❗️ Проверяйте так всегда, ибо клоака — вещь нетулочная"
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main")]]
    )
    await callback.message.answer_photo(
        photo,
        caption=caption,
        parse_mode="HTML",
        reply_markup=keyboard
    )
    await state.set_state(FriendState.waiting_for_link)


def combine_friend_images(frame_url: str, avatar_url: str, persona_name: str, profile_url: str) -> BytesIO:
    try:
        background_path = "images/photo2.jpg"
        background_image = Image.open(background_path).convert('RGBA')

        avatar_size = (40, 40)
        frame_size = (50, 50)

        if avatar_url:
            avatar_response = requests.get(avatar_url)
            avatar_image = Image.open(BytesIO(avatar_response.content)).convert('RGBA')
            avatar_image = avatar_image.resize(avatar_size, Image.Resampling.LANCZOS)
        else:
            raise ValueError("Avatar URL is required")

        combined_image = Image.new('RGBA', frame_size, (0, 0, 0, 0))

        avatar_position = (
            (frame_size[0] - avatar_size[0]) // 2,
            (frame_size[1] - avatar_size[1]) // 2
        )

        combined_image.paste(avatar_image, avatar_position)

        if frame_url:
            frame_response = requests.get(frame_url)
            frame_image = Image.open(BytesIO(frame_response.content)).convert('RGBA')
            frame_image = frame_image.resize(frame_size, Image.Resampling.LANCZOS)
            combined_image = Image.alpha_composite(combined_image, frame_image)


        main_position = (250, 90)

        result_image = background_image.copy()
        result_image.paste(combined_image, main_position, combined_image)

        small_avatar_size = (avatar_size[0] // 2, avatar_size[1] // 2)
        small_avatar_image = avatar_image.resize(small_avatar_size, Image.Resampling.LANCZOS)

        small_frame_size = (small_avatar_size[0] + 4, small_avatar_size[1] + 4)
        small_frame_image = Image.new('RGBA', small_frame_size, (80, 80, 80, 255))

        small_avatar_position_in_frame = (
            (small_frame_size[0] - small_avatar_size[0]) // 2,
            (small_frame_size[1] - small_avatar_size[1]) // 2
        )


        small_frame_image.paste(small_avatar_image, small_avatar_position_in_frame, small_avatar_image)


        small_avatar_position = (result_image.width - small_frame_size[0] - 335, 7)


        result_image.paste(small_frame_image, small_avatar_position, small_frame_image)

        draw = ImageDraw.Draw(result_image)


        font = ImageFont.truetype("fonts/NotoSans-Medium.ttf", 20)
        text_x = main_position[0] + frame_size[0] + 10
        text_y = main_position[1] + (frame_size[1] - 20) // 2 - 10
        draw.text((text_x, text_y), persona_name, fill=(220, 220, 220), font=font)

        font = ImageFont.truetype("fonts/NotoSans-Medium.ttf", 9)


        base_small_avatar_position = (result_image.width - small_avatar_size[0] - 375, 6)


        text_length = len(persona_name)
        if text_length > 4:

            compensation = (text_length - 4) * 5 + 2
            small_avatar_position = (base_small_avatar_position[0] - compensation, base_small_avatar_position[1])
        else:
            small_avatar_position = base_small_avatar_position

        draw.text(small_avatar_position, persona_name, fill=(205, 205, 205), font=font)

        url_font = ImageFont.truetype("fonts/NotoSans-Medium.ttf", 10)


        url_bbox = draw.textbbox((0, 0), profile_url, font=url_font)
        url_width = url_bbox[2] - url_bbox[0]
        url_height = url_bbox[3] - url_bbox[1]

        url_position_x = (result_image.width - url_width) // 2 - 82
        url_position_y = (result_image.height - url_height) // 2 + 77

        draw.text(
            (url_position_x, url_position_y),
            profile_url,
            fill=(255, 255, 255),
            font=url_font
        )

        output = BytesIO()
        result_image.save(output, format='PNG')
        output.seek(0)

        return output

    except Exception as e:
        logger(f"Error combining friend images: {e}")
        raise


@dp.message(FriendState.waiting_for_link)
async def process_friend_link(message: Message, state: FSMContext):
    try:
        url = message.text.strip()

        processing_msg = await message.answer("⏳ Обработка...")

        frame_url, avatar_url, persona_name = parse_steam_profile_images(url)

        if not avatar_url:
            await processing_msg.delete()
            await message.answer("❌ Не удалось найти аватарку в профиле. Проверьте ссылку.")
            return

        await processing_msg.edit_text("⏳ Обработка изображений...")


        combined_image = combine_friend_images(frame_url, avatar_url, persona_name, url)

        await processing_msg.edit_text("⏳ Отправка результата...")

        result_file = BufferedInputFile(combined_image.getvalue(), filename="friend_result.png")

        await message.answer_photo(
            result_file,
            parse_mode="MarkdownV2"
        )

        await processing_msg.delete()
        await state.clear()

    except Exception as e:
        logger(f"Error in friend page: {e}")
        await message.answer("❌ Произошла ошибка при обработке профиля. Попробуйте еще раз.")
        await state.clear()

@dp.callback_query(F.data == "qr_friend_page")
async def on_qr_friend_page(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()
    caption = (
        "<blockquote>📱QR Friend Page\n         ╰ отрисовка QR-кода на странице друзей с твоим фейком</blockquote>\n\n👀 Отправь fake-invite ссылку:\n\n"
        "❗️ Для корректной работы отрисовщика, сначала зайдите сами на ссылку и следом скопируйте адрес из адресной строки\n\n❗️ Проверяйте так всегда, ибо клоака — вещь нетулочная"
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main")]]
    )
    await callback.message.answer_photo(
        photo,
        caption=caption,
        parse_mode="HTML",
        reply_markup=keyboard
    )
    await state.set_state(QrFriendState.waiting_for_link)


def resolve_image_url(img_src: str, profile_url: str) -> str:
    if not img_src:
        return None

    parsed_src = urlparse(img_src)

    if parsed_src.scheme in ("http", "https"):
        return img_src


    parsed_profile = urlparse(profile_url)
    base_url = f"{parsed_profile.scheme}://{parsed_profile.netloc}"


    if not profile_url.endswith("/"):
        profile_url += "/"


    full_url = urljoin(profile_url, img_src)


    if not full_url.startswith("http"):
        full_url = urljoin(base_url + "/", img_src)

    return full_url

def parse_steam_profile_images(profile_url: str) -> tuple:

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        response = requests.get(profile_url, headers=headers)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        avatar_container = soup.find("div", class_="playerAvatarAutoSizeInner")

        if not avatar_container:
            return None, None, None


        persona_name_element = soup.find("span", class_="actual_persona_name")
        persona_name = persona_name_element.get_text(strip=True) if persona_name_element else "Unknown"


        frame_url = None
        frame_img = avatar_container.find("div", class_="profile_avatar_frame")
        if frame_img and frame_img.find("img"):
            frame_src = frame_img.find("img")["src"]
            frame_url = resolve_image_url(frame_src, profile_url)


        avatar_url = None
        all_imgs = avatar_container.find_all("img")
        if all_imgs:
            if len(all_imgs) > 1:
                avatar_src = all_imgs[1]["src"]
            else:
                avatar_src = all_imgs[0]["src"]
            avatar_url = resolve_image_url(avatar_src, profile_url)

        return frame_url, avatar_url, persona_name

    except Exception as e:
        logger(f"Error parsing Steam profile: {e}")
        return None, None, None


def combine_images(frame_url: str, avatar_url: str, persona_name: str, time_text: str, profile_url: str) -> BytesIO:
    try:
        background_path = "images/photo.jpg"
        background_image = Image.open(background_path).convert('RGBA')

        avatar_size = (95, 95)
        frame_size = (115, 115)

        if avatar_url:
            avatar_response = requests.get(avatar_url)
            avatar_image = Image.open(BytesIO(avatar_response.content)).convert('RGBA')
            avatar_image = avatar_image.resize(avatar_size, Image.Resampling.LANCZOS)
        else:
            raise ValueError("Avatar URL is required")

        combined_image = Image.new('RGBA', frame_size, (0, 0, 0, 0))

        avatar_position = (
            (frame_size[0] - avatar_size[0]) // 2,
            (frame_size[1] - avatar_size[1]) // 2
        )

        combined_image.paste(avatar_image, avatar_position)

        if frame_url:
            frame_response = requests.get(frame_url)
            frame_image = Image.open(BytesIO(frame_response.content)).convert('RGBA')
            frame_image = frame_image.resize(frame_size, Image.Resampling.LANCZOS)
            combined_image = Image.alpha_composite(combined_image, frame_image)

        position = (40, 170)

        result_image = background_image.copy()
        result_image.paste(combined_image, position, combined_image)

        small_avatar_size = (avatar_size[0] // 2 + 10, avatar_size[1] // 2 + 10)
        small_avatar_image = avatar_image.resize(small_avatar_size, Image.Resampling.LANCZOS)

        small_avatar_position = (result_image.width - small_avatar_size[0] - 30, 88)

        result_image.paste(small_avatar_image, small_avatar_position, small_avatar_image)

        draw = ImageDraw.Draw(result_image)


        font = ImageFont.truetype("fonts/NotoSans-Medium.ttf", 35)
        text_x = position[0] + frame_size[0] + 10
        text_y = position[1] + (frame_size[1] - 20) // 2 - 30
        draw.text((text_x, text_y), persona_name, fill=(220, 220, 220), font=font)


        time_font = ImageFont.truetype("fonts/SFNSDisplay-Bold.otf", 27)
        time_position = (40, 25)
        draw.text(time_position, time_text, fill=(240, 240, 240), font=time_font)


        url_font = ImageFont.truetype("fonts/NotoSans-Medium.ttf", 20)
        url_position_x = 58
        url_position_y = result_image.height - 40 - 300


        max_chars_per_line = 27
        if len(profile_url) > max_chars_per_line:

            lines = []
            for i in range(0, len(profile_url), max_chars_per_line):
                lines.append(profile_url[i:i + max_chars_per_line])


            for i, line in enumerate(lines):
                draw.text(
                    (url_position_x, url_position_y + (i * 25)),
                    line,
                    fill=(255, 255, 255),
                    font=url_font
                )
        else:

            draw.text(
                (url_position_x, url_position_y),
                profile_url,
                fill=(255, 255, 255),
                font=url_font
            )

        qr_image = generate_styled_qr(profile_url, size=205).convert("RGBA")

        qr_position = (
            (result_image.width - qr_image.width) // 2,
            result_image.height - qr_image.height - 610
        )

        result_image.paste(qr_image, qr_position, qr_image)

        output = BytesIO()
        result_image.save(output, format='PNG')
        output.seek(0)

        return output

    except Exception as e:
        logger(f"Error combining images: {e}")
        raise
@dp.message(QrFriendState.waiting_for_link)
async def process_qr_friend_link(message: Message, state: FSMContext):
    try:
        url = message.text.strip()

        processing_msg = await message.answer("⏳ Обработка...")

        frame_url, avatar_url, persona_name = parse_steam_profile_images(url)

        if not avatar_url:
            await processing_msg.delete()
            await message.answer("❌ Не удалось найти аватарку в профиле. Проверьте ссылку.")
            return


        await state.update_data(
            frame_url=frame_url,
            avatar_url=avatar_url,
            persona_name=persona_name,
            profile_url=url
        )
        await processing_msg.delete()

        await message.answer("⏰ Выберите время для отображения:")
        await state.set_state(QrFriendState.waiting_for_time)

    except Exception as e:
        logger(f"Error in QR friend page: {e}")
        await message.answer("❌ Произошла ошибка при обработке профиля. Попробуйте еще раз.")
        await state.clear()

@dp.message(QrFriendState.waiting_for_time)
async def process_qr_friend_time(message: Message, state: FSMContext):
    try:
        time_text = message.text.strip()

        processing_msg = await message.answer("⏳ Обработка изображений...")

        data = await state.get_data()
        frame_url = data.get('frame_url')
        avatar_url = data.get('avatar_url')
        persona_name = data.get('persona_name')
        profile_url = data.get('profile_url')


        combined_image = combine_images(frame_url, avatar_url, persona_name, time_text, profile_url)

        await processing_msg.edit_text("⏳ Отправка результата...")

        result_file = BufferedInputFile(combined_image.getvalue(), filename="qr_friend_result.png")

        await message.answer_photo(
            result_file,
            parse_mode="MarkdownV2"
        )

        await processing_msg.delete()
        await state.clear()

    except Exception as e:
        logger(f"Error in QR friend page: {e}")
        await message.answer("❌ Произошла ошибка при обработке профиля. Попробуйте еще раз.")
        await state.clear()

@dp.callback_query(F.data == "online_status")
async def on_online_status(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()
    caption = (
        "> 🔍 Чекер статуса\n"
        "> ╰ уведомляет об изменениях статуса мамонта\n\n"
        "📎 *Отправь ссылку на профиль мамонта:*\n\n"
        "❗️*Внимание:* Если вписать ссылку на профиль, который вы уже отслеживаете \\- "
        "бот выключит отслеживание данного участника\\."
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main")]]
    )
    await callback.message.answer_photo(
        photo,
        caption=caption,
        parse_mode="MarkdownV2",
        reply_markup=keyboard
    )
    await state.set_state(OnlineCheckState.waiting_for_profile_link)


@dp.message(OnlineCheckState.waiting_for_profile_link)
async def handle_online_status_link(message: Message, state: FSMContext):
    url = message.text.strip()
    match = re.fullmatch(r"https?://steamcommunity\.com/profiles/(\d{17})/?", url)

    if not match:
        await message.answer("❌ Ошибка: Неверный формат ссылки. Пример: https://steamcommunity.com/profiles/7656119...")
        return

    steam_id = match.group(1)
    tg_id = message.from_user.id

    conn = sqlite3.connect('tracking.db')
    cursor = conn.cursor()

    cursor.execute('SELECT 1 FROM tracking WHERE tg_id = ? AND steam_id = ?', (tg_id, steam_id))
    if cursor.fetchone():
        cursor.execute('DELETE FROM tracking WHERE tg_id = ? AND steam_id = ?', (tg_id, steam_id))
        conn.commit()

        task_key = (tg_id, steam_id)
        if task_key in tracking_tasks:
            tracking_tasks[task_key].cancel()
            del tracking_tasks[task_key]

        await message.answer(f"❌ Отслеживание профиля {steam_id} остановлено.")
        await state.clear()
        return

    cursor.execute('SELECT COUNT(*) FROM tracking WHERE tg_id = ?', (tg_id,))
    count = cursor.fetchone()[0]

    if count >= 10:
        await message.answer("❌ Вы достигли лимита отслеживаемых профилей (10).")
        await state.clear()
        return

    await state.update_data(steam_id=steam_id, url=url)
    await message.answer("💬 Напишите комментарий для этого профиля:")
    await state.set_state(OnlineCheckState.waiting_for_comment)


@dp.message(OnlineCheckState.waiting_for_comment)
async def handle_profile_comment(message: Message, state: FSMContext):
    comment = message.text.strip()
    data = await state.get_data()
    steam_id = data['steam_id']
    url = data['url']
    tg_id = message.from_user.id

    conn = sqlite3.connect('tracking.db')
    cursor = conn.cursor()

    cursor.execute('INSERT INTO tracking (tg_id, steam_id, comment, last_status) VALUES (?, ?, ?, ?)',
                   (tg_id, steam_id, comment, "Currently Offline"))
    conn.commit()
    conn.close()

    task = asyncio.create_task(check_status(tg_id, steam_id, comment))
    tracking_tasks[(tg_id, steam_id)] = task

    await message.answer(f"✅ Отслеживание профиля начато\n\n"
                         f"📎 {url}\n"
                         f"💬 Комментарий: \"{comment}\"")
    await state.clear()


async def restore_tracking_tasks():
    conn = sqlite3.connect('tracking.db')
    cursor = conn.cursor()
    cursor.execute('SELECT tg_id, steam_id, comment FROM tracking')
    rows = cursor.fetchall()
    conn.close()

    for tg_id, steam_id, comment in rows:
        task = asyncio.create_task(check_status(tg_id, steam_id, comment))
        tracking_tasks[(tg_id, steam_id)] = task


@dp.callback_query(F.data == "add_friend")
async def on_add_friend(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🗒 AF Classic", callback_data="af_classic")],
            [InlineKeyboardButton(text="⚡️ AF Quick", callback_data="af_quick")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main")]
        ]
    )
    await callback.message.answer_photo(
        photo,
        caption=(
            "> 🗒 *AF Classic*\n"
            "> ╰ отрисовка ошибки добавления в друзья\n\n"
            "> ⚡️*AF Quick Link*\n"
            "> ╰ отрисовка Add Friend через линк мамонта\n\n"
            "🧠 *Выберите*, какой способ вам нужен"
        ),
        parse_mode="MarkdownV2",
        reply_markup=keyboard)
    await state.set_state(LinkState.waiting_for_action)



@dp.callback_query(F.data == "back_to_main")
async def back_to_main(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()
    user_count = get_user_count()

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🫂 Add Friend", callback_data="add_friend")],
            [InlineKeyboardButton(text="⚠️ Ban DOTA2", callback_data="ban_dota")],
            [InlineKeyboardButton(text="🟢 Check-online", callback_data="online_status")],
            [InlineKeyboardButton(text="📱 QR Friend Page", callback_data="qr_friend_page")],
            [InlineKeyboardButton(text="📨 Friend Page", callback_data="friend_page")],
        ]
    )

    await callback.message.answer_photo(
        photo=photo,
        caption=(
            "🖐 Добро пожаловать в лучший отрисовщик для ворка по CN/EU\n\n"
            "🤝<b> Спасибо что выбрали именно нас!</b>\n\n"
            f"🥷🏻<b> Число</b> юзеров в данном боте - {user_count} 👤"
        ),
        parse_mode="HTML",
        reply_markup=keyboard
    )
    await state.clear()

@dp.callback_query(F.data.in_({"af_classic", "af_quick"}))
async def on_choose_mode(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Отправь ссылку на Steam профиль.",
                                  reply_markup=InlineKeyboardMarkup(
                                      inline_keyboard=[
                                          [InlineKeyboardButton(text="⬅️ Назад", callback_data="add_friend")]]
                                  ))
    await state.update_data(action=callback.data)
    await state.set_state(LinkState.link_saved)

@dp.message(LinkState.link_saved)
async def handle_link(message: Message, state: FSMContext):
    data = await state.get_data()
    action = data.get("action")
    url = message.text.strip()

    if "steamcommunity.com" not in url:
        await message.answer("Некорректная ссылка.")
        return

    filename = os.path.join(SCREENSHOTS_DIR, f"steam_profile_{uuid.uuid4().hex}.png")
    wait_msg = await message.answer("Секунду, обрабатываю...")

    try:
        if action == "af_classic":
            await take_screenshot(url, filename)
        else:
            await take_screenshot_second(url, filename)
        photo = FSInputFile(filename)
        await message.answer_photo(photo)
    except Exception as e:
        logger(f"AF error: {e}")
    finally:
        if os.path.exists(filename):
            os.remove(filename)
        await bot.delete_message(chat_id=message.chat.id, message_id=wait_msg.message_id)

    await state.clear()

@dp.callback_query(F.data == "ban_dota")
async def on_ban_dota(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🗒 Default ban", callback_data="default_ban")],
            [InlineKeyboardButton(text="💅 Ban with nails", callback_data="ban_with_nails")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main")]
        ]
    )
    await callback.message.answer_photo(photo, caption="<blockquote>🗒 Default ban:\n ╰ Отрисовка обычного экрана с баном.</blockquote>\n\n<blockquote> 💅Ban with nails:\n ╰ отрисовка бана с пальчиком девочки</blockquote>\n\n🧠 Выберите, какой способ вам нужен:", parse_mode="HTML", reply_markup=keyboard)




@dp.callback_query(F.data == "ban_with_nails")
async def on_ban_with_nails(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()

    photo = FSInputFile("images/nails.jpg")
    await callback.message.answer_photo(photo)

@dp.callback_query(F.data == "qr_code")
async def on_qr_code(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main")]]
    )
    await callback.message.answer_photo(photo, caption="Отправь изображение с QR кодом.", reply_markup=keyboard)
    await state.set_state(QrCodeState.waiting_for_photo)


@dp.callback_query(F.data == "qr_code_e")
async def on_qr_code_e(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main")]]
    )
    await callback.message.answer_photo(photo, caption="Отправь изображение с QR кодом.", reply_markup=keyboard)
    await state.set_state(QrCodeEState.waiting_for_photo)


@dp.message(QrCodeState.waiting_for_photo)
async def handle_qr_code_photo(message: Message, state: FSMContext):
    photo = message.photo[-1]
    file = await bot.get_file(photo.file_id)
    file_bytes = await bot.download_file(file.file_path)
    np_img = np.frombuffer(file_bytes.read(), np.uint8)
    img = cv2.imdecode(np_img, cv2.IMREAD_COLOR)

    processed_img, qr_img = process_qr_image2(img)
    if processed_img is None:
        return

    def overlay_image_alpha(background, overlay, x, y):
        b_h, b_w = background.shape[:2]
        o_h, o_w = overlay.shape[:2]
        if x + o_w > b_w or y + o_h > b_h:
            return
        alpha = overlay[:, :, 3] / 255.0
        for c in range(3):
            background[y:y + o_h, x:x + o_w, c] = (
                    alpha * overlay[:, :, c] + (1 - alpha) * background[y:y + o_h, x:x + o_w, c]
            ).astype(np.uint8)

    base_img_path = os.path.join("images", "background_first.png")
    base_img = cv2.imread(base_img_path)
    if base_img is None:
        return
    if base_img.shape[2] == 4:
        base_img = cv2.cvtColor(base_img, cv2.COLOR_BGRA2BGR)

    rotated_qr = rotate_image_with_transparency(qr_img, -1.4)
    resized_qr = cv2.resize(rotated_qr, (230, 230))

    x_offset, y_offset = 703, 466
    overlay_image_alpha(base_img, resized_qr, x_offset, y_offset)

    _, buffer_main = cv2.imencode('.png', base_img)
    main_output = BufferedInputFile(BytesIO(buffer_main.tobytes()).getvalue(), filename="result.png")
    await message.answer_photo(photo=main_output)

    _, buffer_qr = cv2.imencode('.png', qr_img)

    qr_output = BufferedInputFile(BytesIO(buffer_qr.tobytes()).getvalue(), filename="qr_only.png")

    await state.clear()

@dp.message(QrCodeEState.waiting_for_photo)
async def handle_qr_code_e_photo(message: Message, state: FSMContext):
    photo = message.photo[-1]
    file = await bot.get_file(photo.file_id)
    file_bytes = await bot.download_file(file.file_path)
    np_img = np.frombuffer(file_bytes.read(), np.uint8)
    img = cv2.imdecode(np_img, cv2.IMREAD_COLOR)

    processed_img, qr_img = process_qr_image2(img)
    if processed_img is None:
        return

    def overlay_image_alpha(background, overlay, x, y):
        b_h, b_w = background.shape[:2]
        o_h, o_w = overlay.shape[:2]
        if x + o_w > b_w or y + o_h > b_h:
            return
        alpha = overlay[:, :, 3] / 255.0
        for c in range(3):
            background[y:y+o_h, x:x+o_w, c] = (
                alpha * overlay[:, :, c] + (1 - alpha) * background[y:y+o_h, x:x+o_w, c]
            ).astype(np.uint8)

    base_img_path = os.path.join("images", "background_last.png")
    base_img = cv2.imread(base_img_path)
    if base_img is None:
        return
    if base_img.shape[2] == 4:
        base_img = cv2.cvtColor(base_img, cv2.COLOR_BGRA2BGR)


    rotated_qr = rotate_image_with_transparency(qr_img, -2.6)
    resized_qr = cv2.resize(rotated_qr, (173, 173))

    x_offset, y_offset = 702, 443
    overlay_image_alpha(base_img, resized_qr, x_offset, y_offset)

    _, buffer_main = cv2.imencode('.png', base_img)
    main_output = BufferedInputFile(BytesIO(buffer_main.tobytes()).getvalue(), filename="result.png")
    await message.answer_photo(photo=main_output)

    _, buffer_qr = cv2.imencode('.png', qr_img)

    qr_output = BufferedInputFile(BytesIO(buffer_qr.tobytes()).getvalue(), filename="qr_only.png")


    await state.clear()
