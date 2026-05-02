import os
import cv2
import numpy as np
from io import BytesIO
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, BufferedInputFile
from aiogram.fsm.context import FSMContext

from states.states import QrCodeState, QrCodeEState
from keyboards.main_keyboards import get_back_button
from utils.constants import PHOTO
from utils.qr_image_handler import process_qr_image2, rotate_image_with_transparency
from handlers.bot_instance import bot

router = Router(name="qr_code")


def load(dp: Router) -> None:
    dp.include_router(router)


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


@router.callback_query(F.data == "qr_code")
async def on_qr_code(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()

    await callback.message.answer_photo(
        photo=PHOTO,
        caption="Отправь изображение с QR кодом.",
        reply_markup=get_back_button()
    )
    await state.set_state(QrCodeState.waiting_for_photo)


@router.callback_query(F.data == "qr_code_e")
async def on_qr_code_e(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()

    await callback.message.answer_photo(
        photo=PHOTO,
        caption="Отправь изображение с QR кодом.",
        reply_markup=get_back_button()
    )
    await state.set_state(QrCodeEState.waiting_for_photo)


@router.message(QrCodeState.waiting_for_photo)
async def handle_qr_code_photo(message: Message, state: FSMContext):
    photo = message.photo[-1]
    file = await bot.get_file(photo.file_id)
    file_bytes = await bot.download_file(file.file_path)
    np_img = np.frombuffer(file_bytes.read(), np.uint8)
    img = cv2.imdecode(np_img, cv2.IMREAD_COLOR)

    processed_img, qr_img = process_qr_image2(img)
    if processed_img is None:
        return

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

    await state.clear()


@router.message(QrCodeEState.waiting_for_photo)
async def handle_qr_code_e_photo(message: Message, state: FSMContext):
    photo = message.photo[-1]
    file = await bot.get_file(photo.file_id)
    file_bytes = await bot.download_file(file.file_path)
    np_img = np.frombuffer(file_bytes.read(), np.uint8)
    img = cv2.imdecode(np_img, cv2.IMREAD_COLOR)

    processed_img, qr_img = process_qr_image2(img)
    if processed_img is None:
        return

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

    await state.clear()