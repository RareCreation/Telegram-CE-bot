from io import BytesIO
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, BufferedInputFile
from aiogram.fsm.context import FSMContext
from PIL import Image

from states.states import BanDefDotaState
from keyboards.main_keyboards import get_ban_dota_keyboard
from utils.constants import PHOTO, NAILS_PHOTO
from handlers.bot_instance import bot

router = Router(name="ban_dota")


def load(dp: Router) -> None:
    dp.include_router(router)


@router.callback_query(F.data == "ban_dota")
async def on_ban_dota(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()

    await callback.message.answer_photo(
        photo=PHOTO,
        caption=(
            "<blockquote>🗒 Default ban:\n ╰ Отрисовка обычного экрана с баном.</blockquote>\n\n"
            "<blockquote> 💅Ban with nails:\n ╰ отрисовка бана с пальчиком девочки</blockquote>\n\n"
            "🧠 Выберите, какой способ вам нужен:"
        ),
        parse_mode="HTML",
        reply_markup=get_ban_dota_keyboard()
    )


@router.callback_query(F.data == "default_ban")
async def ask_for_ban_default_dota_photo(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Отправьте фотографию с лобби в DOTA2:")
    await state.set_state(BanDefDotaState.waiting_for_photo)
    await callback.answer()


@router.message(BanDefDotaState.waiting_for_photo)
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


@router.callback_query(F.data == "ban_with_nails")
async def on_ban_with_nails(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()
    await callback.message.answer_photo(NAILS_PHOTO)