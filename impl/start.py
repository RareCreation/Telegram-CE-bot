import os
import uuid
from io import BytesIO

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from aiogram import F
from aiogram.filters import Command
from aiogram.types import Message, FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, BufferedInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from utils.screenshot import take_screenshot, take_screenshot_second
from handlers.bot_instance import bot, dp
from utils.logger_util import logger
from utils.qr_image_handler import process_qr_image, add_noise_to_center_area, darken_image, \
    rotate_image_with_transparency, process_qr_image2

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

@dp.message(Command("start"))
async def start_handler(message: Message, state: FSMContext):
    await message.answer(
        "Выбери одну из функций отрисовки.",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🫂 Add Friend", callback_data="add_friend")],
                [InlineKeyboardButton(text="⚠️ Ban MM", callback_data="ban_mm")],
                [InlineKeyboardButton(text="🔷 QR PWA", callback_data="qr_code")],
                [InlineKeyboardButton(text="🔷 5e QR-code", callback_data="qr_code_e")]
            ]
        )
    )
    await state.clear()

@dp.callback_query(F.data == "add_friend")
async def on_add_friend(callback: CallbackQuery, state: FSMContext):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🗒 AF Classic", callback_data="af_classic")],
            [InlineKeyboardButton(text="⚡️ AF Quick", callback_data="af_quick")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main")]
        ]
    )
    await callback.message.edit_text("Выбери действие:", reply_markup=keyboard)
    await state.set_state(LinkState.waiting_for_action)

@dp.callback_query(F.data == "back_to_main")
async def back_to_main(callback: CallbackQuery, state: FSMContext):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🫂 Add Friend", callback_data="add_friend")],
            [InlineKeyboardButton(text="⚠️ Ban MM", callback_data="ban_mm")],
            [InlineKeyboardButton(text="🔷 QR PWA", callback_data="qr_code")],
            [InlineKeyboardButton(text="🔷 5e QR-code", callback_data="qr_code_e")]
        ]
    )
    await callback.message.edit_text("Выбери одну из функций отрисовки.", reply_markup=keyboard)
    await state.clear()

@dp.callback_query(F.data.in_({"af_classic", "af_quick"}))
async def on_choose_mode(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Отправь ссылку на Steam профиль.",
                                     reply_markup=InlineKeyboardMarkup(
                                         inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data="add_friend")]]
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

@dp.callback_query(F.data == "ban_mm")
async def on_ban_mm(callback: CallbackQuery, state: FSMContext):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⌛️ 30 mins", callback_data="ban_30m")],
            [InlineKeyboardButton(text="⌛️ 1 hour", callback_data="ban_1h")],
            [InlineKeyboardButton(text="⌛️ 2 hours", callback_data="ban_2h")],
            [InlineKeyboardButton(text="⌛️ 24 hours", callback_data="ban_24h")],
            [InlineKeyboardButton(text="⌛️ 7 days", callback_data="ban_7d")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main")]
        ]
    )
    await callback.message.edit_text("Выбери длительность блокировки:", reply_markup=keyboard)

@dp.callback_query(F.data.startswith("ban_"))
async def on_ban_duration_selected(callback: CallbackQuery, state: FSMContext):
    duration_map = {
        "ban_30m": "30 Mins",
        "ban_1h": "1 Hour",
        "ban_2h": "2 Hours",
        "ban_24h": "24 Hours",
        "ban_7d": "7 Days"
    }
    duration = duration_map.get(callback.data, "Unknown duration")
    await state.update_data(ban_duration=duration)

    await callback.message.edit_text("Отправь изображение для обработки.",
                                     reply_markup=InlineKeyboardMarkup(
                                         inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data="ban_mm")]]
                                     ))
    await state.set_state(BanMMState.waiting_for_photo)

@dp.message(BanMMState.waiting_for_photo)
async def handle_ban_mm_photo(message: Message, state: FSMContext):
    if not message.photo:
        await message.answer("Отправь изображение.")
        return

    data = await state.get_data()
    duration = data.get("ban_duration", "")

    photo = message.photo[-1]
    file = await bot.get_file(photo.file_id)
    filepath = file.file_path
    file_on_disk = os.path.join(SCREENSHOTS_DIR, f"banmm_{uuid.uuid4().hex}.png")

    await bot.download_file(filepath, destination=file_on_disk)

    try:
        img = Image.open(file_on_disk).convert("RGB")
        new_img = Image.new("RGB", (img.width, img.height + 20), color=(223, 191, 6))
        new_img.paste(img, (0, 20))
        draw = ImageDraw.Draw(new_img)
        font_path = "fonts/NotoSans-Regular.ttf"
        font_size = 13
        font = ImageFont.truetype(font_path, font_size)
        text = f"Competitive Cooldown {duration}"
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        x = (new_img.width - text_width) // 2
        y = (20 - text_height) // 2
        draw.text((x, y - 1), text, font=font, fill=(22, 22, 22, 210))
        underline_y = y + text_height
        draw.line((x, underline_y, x + text_width, underline_y), fill=(22, 22, 22, 210), width=1)
        new_img.save(file_on_disk)
        await message.answer_photo(FSInputFile(file_on_disk))
    except Exception as e:
        logger(f"Error processing Ban MM image: {e}")
    finally:
        if os.path.exists(file_on_disk):
            os.remove(file_on_disk)
    await state.clear()

@dp.callback_query(F.data == "qr_code")
async def on_qr_code(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Отправь изображение с QR кодом.",
                                     reply_markup=InlineKeyboardMarkup(
                                         inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main")]]
                                     ))
    await state.set_state(QrCodeState.waiting_for_photo)

@dp.callback_query(F.data == "qr_code_e")
async def on_qr_code_e(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Отправь изображение с QR кодом.",
                                     reply_markup=InlineKeyboardMarkup(
                                         inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main")]]
                                     ))
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
    await message.answer_document(document=qr_output)

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
    await message.answer_document(document=qr_output)

    await state.clear()
