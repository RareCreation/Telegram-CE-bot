import asyncio
from aiogram import F, types, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from states.states import MessageState
from utils.database import get_all_users
from handlers.bot_instance import bot
from settings.config import ADMINS


async def start_message_broadcast(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMINS:
        await message.reply("🚫 У вас нет прав для использования этой команды.")
        return

    await message.answer("📝 Введите сообщение, которое хотите отправить всем пользователям.")
    await state.set_state(MessageState.waiting_for_text)


async def process_broadcast_text(message: types.Message, state: FSMContext):
    text = message.html_text
    await state.clear()

    await message.answer("📤 Начинаю отправлять сообщения ...")

    users = get_all_users()

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


def register_handlers(dp: Dispatcher):
    dp.message.register(start_message_broadcast, Command("message"))
    dp.message.register(process_broadcast_text, MessageState.waiting_for_text)