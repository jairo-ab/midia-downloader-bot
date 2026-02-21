import asyncio
import logging

from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.error import NetworkError, TimedOut
from telegram.ext import CommandHandler, ContextTypes, ConversationHandler, MessageHandler, filters

from app.constants import ACTIVE_DOWNLOADS_KEY, MAX_CONCURRENT_DOWNLOADS, PENDING_DOWNLOADS_KEY, PREF_MP3, PREF_VIDEO
from app.handlers.conversation import get_default_format
from app.utils.text_utils import normalize_text

WAITING_DEFAULT_FORMAT = 10
WAITING_RENAME_CHOICE = 11
logger = logging.getLogger(__name__)


async def safe_reply_text(update: Update, text: str, **kwargs) -> None:
    message = update.effective_message
    if message is None:
        return

    for attempt in range(2):
        try:
            await message.reply_text(text, **kwargs)
            return
        except (TimedOut, NetworkError) as exc:
            if attempt == 0:
                await asyncio.sleep(1)
                continue
            logger.warning("Falha de conexao ao responder comando: %s", exc)
            try:
                await message.reply_text(
                    "⚠️ Conexao instavel com o Telegram no momento. "
                    "Tente novamente em alguns instantes."
                )
            except (TimedOut, NetworkError):
                logger.warning("Nao foi possivel enviar mensagem amigavel de erro de conexao.")
            return


def get_rename_enabled(context: ContextTypes.DEFAULT_TYPE) -> bool:
    value = normalize_text(str(context.user_data.get("rename_enabled", "off")))
    return value in {"on", "sim", "true", "1"}


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "📌 Como usar:\n"
        "1. Use /start\n"
        "2. Escolha Video ou MP3\n"
        "3. Envie a URL\n"
        "4. Confira o resumo e confirme\n\n"
        "🧰 Comandos:\n"
        "/start - Inicia novo download\n"
        "/help - Mostra ajuda\n"
        "/about - Sobre o bot\n"
        "/settings - Mostra configuracoes atuais\n"
        "/format <video|mp3> - Define formato padrao\n"
        "/ping - Verifica se o bot esta online\n"
        "/status - Mostra status da sua sessao\n"
        "/queue - Mostra fila/execucao de downloads\n"
        "/rename - Ativa/desativa renomeacao automatica\n"
        "/cancel - Cancela o fluxo atual"
    )
    await safe_reply_text(update, text)


async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "🤖 Bot de download de midia para Telegram.\n"
        "Envie uma URL, escolha Video ou MP3, confira o resumo e confirme antes do download."
    )
    await safe_reply_text(update, text)


async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    default_format = get_default_format(context).upper()
    rename_status = "ON" if get_rename_enabled(context) else "OFF"
    text = (
        "⚙️ Configuracoes atuais:\n"
        f"- Formato padrao: {default_format}\n\n"
        f"- Rename automatico: {rename_status}\n\n"
        "Para alterar: /format e /rename"
    )
    await safe_reply_text(update, text)


async def ping_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await safe_reply_text(update, "🏓 Pong! Bot online.")


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    default_format = get_default_format(context).upper()
    rename_status = "ON" if get_rename_enabled(context) else "OFF"
    flow_active = bool(context.user_data.get("url")) or bool(context.user_data.get("selected_format"))
    downloading = bool(context.user_data.get("is_downloading"))

    text = (
        "📊 Status da sua sessao:\n"
        f"- Formato padrao: {default_format}\n"
        f"- Rename automatico: {rename_status}\n"
        f"- Fluxo ativo: {'SIM' if flow_active else 'NAO'}\n"
        f"- Download em andamento: {'SIM' if downloading else 'NAO'}"
    )
    await safe_reply_text(update, text)


async def queue_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    active = int(context.application.bot_data.get(ACTIVE_DOWNLOADS_KEY, 0))
    pending = int(context.application.bot_data.get(PENDING_DOWNLOADS_KEY, 0))
    free_slots = max(MAX_CONCURRENT_DOWNLOADS - active, 0)
    text = (
        "🧵 Fila de downloads:\n"
        f"- Em andamento: {active}/{MAX_CONCURRENT_DOWNLOADS}\n"
        f"- Aguardando vaga: {pending}\n"
        f"- Vagas livres: {free_slots}"
    )
    await safe_reply_text(update, text)


async def start_rename_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    current = "ON" if get_rename_enabled(context) else "OFF"
    await safe_reply_text(
        update,
        f"✏️ Rename automatico atual: {current}\nEscolha a opcao:",
        reply_markup=ReplyKeyboardMarkup([["ON", "OFF"]], resize_keyboard=True, one_time_keyboard=True),
    )
    return WAITING_RENAME_CHOICE


async def receive_rename_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    value = normalize_text(update.message.text or "")
    if value not in {"on", "off"}:
        await safe_reply_text(
            update,
            "❌ Escolha invalida. Toque em ON ou OFF.",
            reply_markup=ReplyKeyboardMarkup([["ON", "OFF"]], resize_keyboard=True, one_time_keyboard=True),
        )
        return WAITING_RENAME_CHOICE

    context.user_data["rename_enabled"] = value
    await safe_reply_text(
        update,
        f"✅ Rename automatico: {value.upper()}",
        reply_markup=ReplyKeyboardRemove(),
    )
    return ConversationHandler.END


async def start_format_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if context.args:
        value = normalize_text(context.args[0])
        if value in {PREF_VIDEO, PREF_MP3}:
            context.user_data["default_format"] = value
            await safe_reply_text(update, f"✅ Formato padrao atualizado para: {value.upper()}")
            return ConversationHandler.END

        await safe_reply_text(
            update,
            "❌ Valor invalido. Toque em uma opcao valida:",
            reply_markup=ReplyKeyboardMarkup([["Video", "MP3"]], resize_keyboard=True, one_time_keyboard=True),
        )
        return WAITING_DEFAULT_FORMAT

    current = get_default_format(context).upper()
    await safe_reply_text(
        update,
        f"⚙️ Formato padrao atual: {current}\nEscolha o novo formato:",
        reply_markup=ReplyKeyboardMarkup([["Video", "MP3"]], resize_keyboard=True, one_time_keyboard=True),
    )
    return WAITING_DEFAULT_FORMAT


async def receive_format_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    value = normalize_text(update.message.text or "")
    if value not in {PREF_VIDEO, PREF_MP3}:
        await safe_reply_text(
            update,
            "❌ Escolha invalida. Toque em Video ou MP3.",
            reply_markup=ReplyKeyboardMarkup([["Video", "MP3"]], resize_keyboard=True, one_time_keyboard=True),
        )
        return WAITING_DEFAULT_FORMAT

    context.user_data["default_format"] = value
    await safe_reply_text(
        update,
        f"✅ Formato padrao atualizado para: {value.upper()}",
        reply_markup=ReplyKeyboardRemove(),
    )
    return ConversationHandler.END


async def cancel_format_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await safe_reply_text(update, "🛑 Operacao cancelada.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


def build_format_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[CommandHandler("format", start_format_command)],
        states={
            WAITING_DEFAULT_FORMAT: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_format_choice)],
        },
        fallbacks=[CommandHandler("cancel", cancel_format_command)],
    )


def build_rename_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[CommandHandler("rename", start_rename_command)],
        states={
            WAITING_RENAME_CHOICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_rename_choice)],
        },
        fallbacks=[CommandHandler("cancel", cancel_format_command)],
        allow_reentry=True,
    )
