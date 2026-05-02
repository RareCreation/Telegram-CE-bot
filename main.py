import asyncio
from handlers.bot_instance import dp, bot
from utils.database import init_db, init_users_db
from utils.tracking import restore_tracking_tasks
from utils.logger_util import logger

# Импортируем все регистраторы напрямую
from handlers.start import register_handlers as register_start
from handlers.add_friend import register_handlers as register_add_friend
from handlers.ban_dota import register_handlers as register_ban_dota
from handlers.online_check import register_handlers as register_online_check
from handlers.qr_friend import register_handlers as register_qr_friend
from handlers.friend_page import register_handlers as register_friend_page
from handlers.qr_code import register_handlers as register_qr_code
from handlers.admin import register_handlers as register_admin


async def main():
    logger.info("Initializing databases...")
    init_db()
    init_users_db()

    logger.info("Restoring tracking tasks...")
    await restore_tracking_tasks()

    logger.info("Registering handlers...")
    register_start(dp)
    register_add_friend(dp)
    register_ban_dota(dp)
    register_online_check(dp)
    register_qr_friend(dp)
    register_friend_page(dp)
    register_qr_code(dp)
    register_admin(dp)

    logger.info("Starting bot...")
    await dp.start_polling(bot, skip_updates=True)


if __name__ == '__main__':
    asyncio.run(main())