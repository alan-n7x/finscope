import logging
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from app.config import get_settings
from app.bot.handlers import router

logger = logging.getLogger(__name__)

# Global instances that will be managed by FastAPI lifespan
bot: Bot | None = None
dp: Dispatcher | None = None
polling_task: asyncio.Task | None = None

async def start_bot() -> None:
    """
    Initializes the Telegram Bot and starts polling in the background.
    """
    global bot, dp, polling_task
    settings = get_settings()
    
    if not settings.telegram_bot_token:
        logger.warning("TELEGRAM_BOT_TOKEN not set. Telegram Bot will not start.")
        return

    logger.info("Starting Telegram Bot...")
    bot = Bot(token=settings.telegram_bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    
    # Include the routers
    dp.include_router(router)
    
    # Start polling in a background task
    polling_task = asyncio.create_task(dp.start_polling(bot))


async def stop_bot() -> None:
    """
    Stops the Telegram Bot gracefully.
    """
    global bot, dp, polling_task
    if bot and dp:
        logger.info("Stopping Telegram Bot...")
        await dp.stop_polling()
        if polling_task:
            polling_task.cancel()
        await bot.session.close()
        logger.info("Telegram Bot stopped.")
