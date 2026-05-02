from io import BytesIO
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, BufferedInputFile
from aiogram.fsm.context import FSMContext
from PIL import Image, ImageDraw, ImageFont
import requests

from states.states import FriendState, FriendNotFoundState
from keyboards.main_keyboards import get_friend_page_keyboard, get_back_button
from utils.constants import PHOTO
from utils.steam_parser import parse_steam_profile_images
from utils.logger_util import logger

router = Router(name="friend_page")


def load(dp: Router) -> None:
    dp.include_router(router)


def combine_friend_images(frame_url: str, avatar_url: str, persona_name: str, profile_url: str) -> BytesIO:
    try:
        background_path = "images/friend3.png"
        background_image = Image.open(background_path).convert('RGBA')

        avatar_size = (45, 45)
        frame_size = (55, 55)

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

        main_position = (370, 160)

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

        small_avatar_position = (result_image.width - small_frame_size[0] - 525, 7)
        result_image.paste(small_frame_image, small_avatar_position, small_frame_image)

        draw = ImageDraw.Draw(result_image)

        font = ImageFont.truetype("fonts/NotoSans-Medium.ttf", 20)
        text_x = main_position[0] + frame_size[0] + 10
        text_y = main_position[1] + (frame_size[1] - 20) // 2 - 10
        draw.text((text_x, text_y), persona_name, fill=(220, 220, 220), font=font)

        font3 = ImageFont.truetype("fonts/NotoSans-Medium.ttf", 10)
        base_small_avatar_position = (result_image.width - small_avatar_size[0] - 560, 9)

        text_length = len(persona_name)
        if text_length > 4:
            compensation = (text_length - 4) * 5 + 2
            small_avatar_position_text = (base_small_avatar_position[0] - compensation, base_small_avatar_position[1])
        else:
            small_avatar_position_text = base_small_avatar_position

        draw.text(small_avatar_position_text, persona_name, fill=(205, 205, 205), font=font3)

        url_font = ImageFont.truetype("fonts/NotoSans-Medium.ttf", 13)

        url_bbox = draw.textbbox((0, 0), profile_url, font=url_font)
        url_width = url_bbox[2] - url_bbox[0]
        url_height = url_bbox[3] - url_bbox[1]

        url_position_x = 670
        url_position_y = (result_image.height - url_height) // 2 + 117

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
        logger.error(f"Error combining images: {e}")
        raise


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

        font_small = ImageFont.truetype("fonts/NotoSans-Medium.ttf", 9)

        base_small_avatar_position = (result_image.width - small_avatar_size[0] - 375, 6)

        text_length = len(persona_name)
        if text_length > 4:
            compensation = (text_length - 4) * 5 + 2
            small_avatar_position_text = (base_small_avatar_position[0] - compensation, base_small_avatar_position[1])
        else:
            small_avatar_position_text = base_small_avatar_position

        draw.text(small_avatar_position_text, persona_name, fill=(205, 205, 205), font=font_small)

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
        logger.error(f"Error combining friend not found images: {e}")
        raise


@router.callback_query(F.data == "friend_page")
async def on_friend_page(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()
    caption = (
        "<blockquote>📨Friend Page\n         ╰ Отрисовка страницы с кодом друга и с дружественной ссылкой на странице Steam.</blockquote>\n\n"
        "<blockquote>🚫 Friend Page not found:\n         ╰ Отрисовка не найденного кода друга из за разных регионов.</blockquote>"
    )

    await callback.message.answer_photo(
        photo=PHOTO,
        caption=caption,
        parse_mode="HTML",
        reply_markup=get_friend_page_keyboard()
    )


@router.callback_query(F.data == "friend_page_image")
async def on_friend_page_image(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()
    caption = (
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
    await state.set_state(FriendState.waiting_for_link)


@router.message(FriendState.waiting_for_link)
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
        logger.error(f"Error in friend page: {e}")
        await message.answer("❌ Произошла ошибка при обработке профиля. Попробуйте еще раз.")
        await state.clear()


@router.callback_query(F.data == "friend_not_found")
async def on_friend_not_found(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()
    caption = (
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
    await state.set_state(FriendNotFoundState.waiting_for_link)


@router.message(FriendNotFoundState.waiting_for_link)
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

        await message.answer(
            caption,
            parse_mode="HTML",
            reply_markup=get_back_button("friend_page")
        )
        await state.set_state(FriendNotFoundState.waiting_for_id)

    except Exception as e:
        logger.error(f"Error in friend not found link processing: {e}")
        await message.answer("❌ Произошла ошибка при обработке профиля. Попробуйте еще раз.")
        await state.clear()


@router.message(FriendNotFoundState.waiting_for_id)
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
        logger.error(f"Error in friend not found ID processing: {e}")
        await message.answer("❌ Произошла ошибка при создании изображения. Попробуйте еще раз.")
        await state.clear()