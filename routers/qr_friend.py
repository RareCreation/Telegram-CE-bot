from io import BytesIO
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, BufferedInputFile
from aiogram.fsm.context import FSMContext
from PIL import Image, ImageDraw, ImageFont
import requests

from states.states import QrFriendState
from keyboards.main_keyboards import get_back_button
from utils.constants import PHOTO
from utils.steam_parser import parse_steam_profile_images, get_requests_session, download_image
from utils.qrgenerate import generate_styled_qr
from utils.logger_util import logger

router = Router(name="qr_friend")


def load(dp: Router) -> None:
    dp.include_router(router)


def combine_images(frame_url: str, avatar_url: str, persona_name: str, time_text: str, profile_url: str) -> BytesIO:
    try:
        background_path = "images/photo.jpg"
        background_image = Image.open(background_path).convert('RGBA')

        avatar_size = (95, 95)
        frame_size = (115, 115)

        if avatar_url:
            session = get_requests_session()

            avatar_image = download_image(session, avatar_url)
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
            try:
                frame_image = download_image(session, frame_url)

                frame_image = frame_image.resize(
                    frame_size,
                    Image.Resampling.LANCZOS
                )

                combined_image = Image.alpha_composite(
                    combined_image,
                    frame_image
                )

            except Exception as e:
                logger.warning(
                    f"Failed to load frame image: {e}"
                )

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
        logger.error(f"Error combining images: {e}")
        raise


@router.callback_query(F.data == "qr_friend_page")
async def on_qr_friend_page(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()
    caption = (
        "<blockquote>📱QR Friend Page\n         ╰ отрисовка QR-кода на странице друзей с твоим фейком</blockquote>\n\n"
        "👀 Отправь fake-invite ссылку:\n\n"
        "❗️ Для корректной работы отрисовщика, сначала зайдите сами на ссылку и следом скопируйте адрес из адресной строки\n\n"
        "❗️ Проверяйте так всегда, ибо клоака — вещь нетулочная"
    )

    await callback.message.answer_photo(
        photo=PHOTO,
        caption=caption,
        parse_mode="HTML",
        reply_markup=get_back_button()
    )
    await state.set_state(QrFriendState.waiting_for_link)


@router.message(QrFriendState.waiting_for_link)
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
        logger.error(f"Error in QR friend page: {e}")
        await message.answer("❌ Произошла ошибка при обработке профиля. Попробуйте еще раз.")
        await state.clear()


@router.message(QrFriendState.waiting_for_time)
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
        logger.error(f"Error in QR friend page: {e}")
        await message.answer("❌ Произошла ошибка при обработке профиля. Попробуйте еще раз.")
        await state.clear()