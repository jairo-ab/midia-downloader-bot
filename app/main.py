import asyncio
import logging

from telegram.ext import Application, CommandHandler

from app.config import load_token
from app.constants import DOWNLOAD_SEMAPHORE_KEY, MAX_CONCURRENT_DOWNLOADS
from app.handlers.commands import about_command, build_format_handler, help_command, settings_command
from app.handlers.conversation import build_conversation_handler, cancel


def configure_logging() -> None:
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO,
    )


def create_application() -> Application:
    token = load_token()
    app = Application.builder().token(token).build()
    app.bot_data[DOWNLOAD_SEMAPHORE_KEY] = asyncio.Semaphore(MAX_CONCURRENT_DOWNLOADS)
    app.add_handler(build_conversation_handler())
    app.add_handler(build_format_handler())
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("about", about_command))
    app.add_handler(CommandHandler("settings", settings_command))
    app.add_handler(CommandHandler("cancel", cancel))
    return app


def run() -> None:
    configure_logging()
    app = create_application()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    app.run_polling(close_loop=False)
