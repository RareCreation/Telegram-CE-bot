import os
import uuid
from aiogram import F, Dispatcher
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext

from states.states import LinkState
from keyboards.main_keyboards import get_add_friend_keyboard, get_back_button
from utils.screenshot import take_screenshot, take_screenshot_second
from utils.constants import SCREENSHOTS_DIR, PHOTO
from utils.logger_util import logger
from handlers.bot_instance import bot


async def on_add_friend(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()
    await callback.message.answer_photo(
        photo=PHOTO,
        caption=(
            "> 🗒 *AF Classic*\n"
            "> ╰ отрисовка ошибки добавления в друзья\n\n"
            "> ⚡️*AF Quick Link*\n"
            "> ╰ отрисовка Add Friend через линк мамонта\n\n"
            "🧠 *Выберите*, какой способ вам нужен"
        ),
        parse_mode="MarkdownV2",
        reply_markup=get_add_friend_keyboard()
    )
    await state.set_state(LinkState.waiting_for_action)


async def on_choose_mode(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer(
        "Отправь ссылку на Steam профиль.",
        reply_markup=get_back_button("add_friend")
    )
    await state.update_data(action=callback.data)
    await state.set_state(LinkState.link_saved)


async def handle_link(message: Message, state: FSMContext):
    data = await state.get_data()
    action = data.get("action")
    url = message.text.strip()

    if "steamcommunity.com" not in url:
        await message.answer("❌ Некорректная ссылка. Пожалуйста, отправьте ссылку на профиль Steam.")
        return

    
    os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

    filename = os.path.join(SCREENSHOTS_DIR, f"steam_profile_{uuid.uuid4().hex}.png")
    wait_msg = await message.answer("⏳ Секунду, обрабатываю...")

    try:
        if action == "af_classic":
            await take_screenshot(url, filename)
        else:
            await take_screenshot_second(url, filename)

        
        if os.path.exists(filename):
            photo = FSInputFile(filename)
            await message.answer_photo(photo)
        else:
            await message.answer("❌ Не удалось создать скриншот. Попробуйте позже.")
            logger.error(f"Screenshot file not created: {filename}")

    except Exception as e:
        logger.error(f"AF error: {e}")
        await message.answer(f"❌ Произошла ошибка: {str(e)}")
    finally:
        
        if os.path.exists(filename):
            try:
                os.remove(filename)
            except Exception as e:
                logger.error(f"Failed to remove file {filename}: {e}")
        
        try:
            await bot.delete_message(chat_id=message.chat.id, message_id=wait_msg.message_id)
        except Exception:
            pass  

    await state.clear()


def register_handlers(dp: Dispatcher):
    dp.callback_query.register(on_add_friend, F.data == "add_friend")
    dp.callback_query.register(on_choose_mode, F.data.in_({"af_classic", "af_quick"}))
    dp.message.register(handle_link, LinkState.link_saved)