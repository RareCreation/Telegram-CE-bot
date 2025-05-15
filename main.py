import asyncio
from handlers.bot_instance import dp, bot
from utils.logger_util import logger
from impl import start


if __name__ == '__main__':
    logger("Bot has been launched")
    asyncio.run(dp.start_polling(bot, skip_updates=True))
