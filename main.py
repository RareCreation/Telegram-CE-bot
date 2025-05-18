import asyncio
from handlers.bot_instance import dp, bot
from utils.logger_util import logger
from utils.setup_commands import setup_bot_commands
from impl import start

async def main():
    logger("Bot has been launched")
    await setup_bot_commands(bot)
    await dp.start_polling(bot, skip_updates=True)

if __name__ == '__main__':
    asyncio.run(main())
