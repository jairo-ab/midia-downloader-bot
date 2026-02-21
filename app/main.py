import asyncio
import logging

from telegram import ReplyKeyboardRemove, Update
from telegram.ext import Application, CommandHandler, ContextTypes

from app.config import load_token
from app.constants import DOWNLOAD_SEMAPHORE_KEY, MAX_CONCURRENT_DOWNLOADS
from app.handlers.commands import about_command, build_format_handler, help_command, settings_command
from app.handlers.conversation import build_conversation_handler, cancel, clear_flow_data

logger = logging.getLogger(__name__)


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
    app.add_error_handler(handle_unexpected_error)
    return app


async def handle_unexpected_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.exception("Erro nao tratado durante processamento de update", exc_info=context.error)

    if isinstance(update, Update):
        clear_flow_data(context)
        message = (
            "Ocorreu um erro inesperado ao processar sua solicitacao.\n"
            "Pode tentar outro link agora. Se preferir, use /start para reiniciar."
        )
        try:
            if update.effective_message is not None:
                await update.effective_message.reply_text(
                    message,
                    reply_markup=ReplyKeyboardRemove(),
                )
                return
            if update.effective_chat is not None:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=message,
                    reply_markup=ReplyKeyboardRemove(),
                )
        except Exception:
            logger.exception("Falha ao enviar mensagem de erro para o usuario")


def run() -> None:
    configure_logging()
    app = create_application()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    app.run_polling(close_loop=False)
