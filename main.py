import asyncio
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand

from handlers.bot_instance import bot, dp
from settings.config import TOKEN
from utils.database import init_db, init_users_db
from utils.load_routers import load_routers
from utils.logger_util import logger


async def setup_bot_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="▶️ Запуск бота"),
    ]
    await bot.set_my_commands(commands)


async def main():
    logger.info("Initializing databases...")
    init_db()
    init_users_db()

    await setup_bot_commands(bot)

    await load_routers(dp=dp, bot=bot)
    logger.info("routers loaded")

    logger.info("Starting bot...")
    await dp.start_polling(bot, skip_updates=True)




if __name__ == '__main__':
    asyncio.run(main())