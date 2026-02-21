from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import CommandHandler, ContextTypes, ConversationHandler, MessageHandler, filters

from app.constants import PREF_MP3, PREF_VIDEO
from app.handlers.conversation import get_default_format
from app.utils.text_utils import normalize_text

WAITING_DEFAULT_FORMAT = 10


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "Como usar:\n"
        "1. Use /start\n"
        "2. Escolha Video ou MP3\n"
        "3. Envie a URL\n"
        "4. Confira o resumo e confirme\n\n"
        "Comandos:\n"
        "/start - Inicia novo download\n"
        "/help - Mostra ajuda\n"
        "/about - Sobre o bot\n"
        "/settings - Mostra configuracoes atuais\n"
        "/format <video|mp3> - Define formato padrao\n"
        "/cancel - Cancela o fluxo atual"
    )
    await update.message.reply_text(text)


async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "Bot de download de midia para Telegram.\n"
        "Envie uma URL, escolha Video ou MP3, confira o resumo e confirme antes do download."
    )
    await update.message.reply_text(text)


async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    default_format = get_default_format(context).upper()
    text = (
        "Configuracoes atuais:\n"
        f"- Formato padrao: {default_format}\n\n"
        "Para alterar: /format"
    )
    await update.message.reply_text(text)


async def start_format_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if context.args:
        value = normalize_text(context.args[0])
        if value in {PREF_VIDEO, PREF_MP3}:
            context.user_data["default_format"] = value
            await update.message.reply_text(f"Formato padrao atualizado para: {value.upper()}")
            return ConversationHandler.END

        await update.message.reply_text(
            "Valor invalido. Toque em uma opcao valida:",
            reply_markup=ReplyKeyboardMarkup([["Video", "MP3"]], resize_keyboard=True, one_time_keyboard=True),
        )
        return WAITING_DEFAULT_FORMAT

    current = get_default_format(context).upper()
    await update.message.reply_text(
        f"Formato padrao atual: {current}\nEscolha o novo formato:",
        reply_markup=ReplyKeyboardMarkup([["Video", "MP3"]], resize_keyboard=True, one_time_keyboard=True),
    )
    return WAITING_DEFAULT_FORMAT


async def receive_format_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    value = normalize_text(update.message.text or "")
    if value not in {PREF_VIDEO, PREF_MP3}:
        await update.message.reply_text(
            "Escolha invalida. Toque em Video ou MP3.",
            reply_markup=ReplyKeyboardMarkup([["Video", "MP3"]], resize_keyboard=True, one_time_keyboard=True),
        )
        return WAITING_DEFAULT_FORMAT

    context.user_data["default_format"] = value
    await update.message.reply_text(
        f"Formato padrao atualizado para: {value.upper()}",
        reply_markup=ReplyKeyboardRemove(),
    )
    return ConversationHandler.END


async def cancel_format_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Operacao cancelada.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


def build_format_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[CommandHandler("format", start_format_command)],
        states={
            WAITING_DEFAULT_FORMAT: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_format_choice)],
        },
        fallbacks=[CommandHandler("cancel", cancel_format_command)],
    )
