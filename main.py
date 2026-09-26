import asyncio
import logging

from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, filters
)

from config import BOT_TOKEN, WEBHOOK_URL, PORT
from handlers import start_cmd, text_handler, callback_handler

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)


async def main_async():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    await app.initialize()
    await app.bot.set_webhook(f"{WEBHOOK_URL}/{BOT_TOKEN}")
    await app.start()
    await app.updater.start_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=BOT_TOKEN,
        webhook_url=f"{WEBHOOK_URL}/{BOT_TOKEN}",
    )
    logger.info("🔥 Pool Bot آنلاین شد...")
    stop = asyncio.Event()
    await stop.wait()


def main():
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
