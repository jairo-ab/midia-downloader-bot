import asyncio
import logging
import re
import tempfile
from pathlib import Path

from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.constants import ChatAction, ParseMode
from telegram.error import NetworkError, TimedOut
from telegram.ext import CommandHandler, ContextTypes, ConversationHandler, MessageHandler, filters

from app.constants import (
    ACTIVE_DOWNLOADS_KEY,
    CHOOSING_FORMAT,
    CONFIRMING_DOWNLOAD,
    DOWNLOAD_SEMAPHORE_KEY,
    MAX_CONCURRENT_DOWNLOADS,
    NO,
    PENDING_DOWNLOADS_KEY,
    PREF_MP3,
    PREF_VIDEO,
    WAITING_URL,
    YES,
)
from app.services.media_service import download_media, extract_media_info
from app.utils.text_utils import escape_html, format_duration, is_probably_url, normalize_text

logger = logging.getLogger(__name__)


def get_default_format(context: ContextTypes.DEFAULT_TYPE) -> str:
    value = normalize_text(str(context.user_data.get("default_format", PREF_VIDEO)))
    if value in {PREF_VIDEO, PREF_MP3}:
        return value
    return PREF_VIDEO


def get_rename_enabled(context: ContextTypes.DEFAULT_TYPE) -> bool:
    value = normalize_text(str(context.user_data.get("rename_enabled", "off")))
    return value in {"on", "sim", "true", "1"}


def is_instagram_block_error(url: str, exc: Exception) -> bool:
    if "instagram.com" not in url.lower():
        return False
    message = str(exc).lower()
    indicators = (
        "rate-limit reached",
        "login required",
        "requested content is not available",
    )
    return any(indicator in message for indicator in indicators)


def clear_flow_data(context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data.pop("selected_format", None)
    context.user_data.pop("url", None)
    context.user_data.pop("info", None)


def _decrement_bot_counter(context: ContextTypes.DEFAULT_TYPE, key: str) -> None:
    current = int(context.application.bot_data.get(key, 0))
    context.application.bot_data[key] = max(current - 1, 0)


def build_safe_file_stem(raw_title: str) -> str:
    cleaned = raw_title.strip()[:120]
    cleaned = re.sub(r'[\\/:*?"<>|\r\n\t]+', "_", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .")
    return cleaned or "midia"


def rename_downloaded_file(file_path: Path, title: str) -> Path:
    safe_stem = build_safe_file_stem(title)
    target = file_path.with_name(f"{safe_stem}{file_path.suffix}")
    if target == file_path:
        return file_path

    if not target.exists():
        return file_path.rename(target)

    for idx in range(2, 1000):
        candidate = file_path.with_name(f"{safe_stem}_{idx}{file_path.suffix}")
        if not candidate.exists():
            return file_path.rename(candidate)
    return file_path


def get_download_semaphore(context: ContextTypes.DEFAULT_TYPE) -> asyncio.Semaphore:
    semaphore = context.application.bot_data.get(DOWNLOAD_SEMAPHORE_KEY)
    if isinstance(semaphore, asyncio.Semaphore):
        return semaphore

    semaphore = asyncio.Semaphore(MAX_CONCURRENT_DOWNLOADS)
    context.application.bot_data[DOWNLOAD_SEMAPHORE_KEY] = semaphore
    return semaphore


async def safe_send_chat_action(context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> None:
    try:
        await context.bot.send_chat_action(
            chat_id=chat_id,
            action=ChatAction.UPLOAD_DOCUMENT,
            connect_timeout=20,
            read_timeout=20,
            write_timeout=20,
            pool_timeout=20,
        )
    except (TimedOut, NetworkError):
        logger.warning("Falha temporaria ao enviar chat action; seguindo o envio.")


async def send_media_with_retries(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    file_path: Path,
    media_format: str,
    attempts: int = 3,
) -> None:
    for attempt in range(1, attempts + 1):
        try:
            if media_format == PREF_MP3:
                with file_path.open("rb") as media_file:
                    await context.bot.send_audio(
                        chat_id=chat_id,
                        audio=media_file,
                        title=file_path.stem,
                        connect_timeout=30,
                        read_timeout=300,
                        write_timeout=300,
                        pool_timeout=30,
                    )
            else:
                with file_path.open("rb") as media_file:
                    await context.bot.send_video(
                        chat_id=chat_id,
                        video=media_file,
                        supports_streaming=True,
                        connect_timeout=30,
                        read_timeout=300,
                        write_timeout=300,
                        pool_timeout=30,
                    )
            return
        except (TimedOut, NetworkError) as exc:
            if attempt >= attempts:
                raise
            wait_seconds = attempt * 2
            logger.warning(
                "Timeout/rede no envio da midia (tentativa %s/%s): %s",
                attempt,
                attempts,
                exc,
            )
            await asyncio.sleep(wait_seconds)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    clear_flow_data(context)
    default_format = get_default_format(context)
    keyboard = [["Video", "MP3"]]
    await update.message.reply_text(
        f"Escolha o formato deste download (padrao: {default_format.upper()}): Video ou MP3.",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True),
    )
    return CHOOSING_FORMAT


async def choose_format(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    choice = normalize_text(update.message.text or "")
    if choice not in {PREF_VIDEO, PREF_MP3}:
        await update.message.reply_text("Escolha invalida. Responda apenas com Video ou MP3.")
        return CHOOSING_FORMAT

    context.user_data["selected_format"] = choice
    await update.message.reply_text("Agora envie a URL da midia.", reply_markup=ReplyKeyboardRemove())
    return WAITING_URL


async def receive_url(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    url = (update.message.text or "").strip()
    if not is_probably_url(url):
        await update.message.reply_text("URL invalida. Envie um link comecando com http:// ou https://")
        return WAITING_URL

    await update.message.reply_text("Analisando link...")

    try:
        info = await asyncio.to_thread(extract_media_info, url)
    except Exception as exc:
        logger.exception("Falha ao extrair info")
        if is_instagram_block_error(url, exc):
            await update.message.reply_text(
                "Nao consegui acessar essa midia no Instagram agora. "
                "O Instagram bloqueou temporariamente esse video. "
                "Tente novamente em alguns instantes ou envie outro link."
            )
            return WAITING_URL
        await update.message.reply_text(
            "Nao consegui ler essa URL no momento. "
            "Tente novamente em alguns instantes ou envie outro link."
        )
        return WAITING_URL

    selected_format = context.user_data.get("selected_format") or get_default_format(context)
    context.user_data["url"] = url
    context.user_data["info"] = info
    context.user_data["selected_format"] = selected_format

    summary = (
        "Resumo da midia:\n"
        f"- Titulo: {escape_html(info['title'])}\n"
        f"- Canal/Autor: {escape_html(info['uploader'])}\n"
        f"- Duracao: {format_duration(info['duration'])}\n"
        f"- Formato escolhido: {selected_format.upper()}\n\n"
        "Confirma o download? (sim/nao)"
    )
    await update.message.reply_text(
        summary,
        parse_mode=ParseMode.HTML,
        reply_markup=ReplyKeyboardMarkup([["Sim", "Nao"]], resize_keyboard=True, one_time_keyboard=True),
    )
    return CONFIRMING_DOWNLOAD


async def confirm_download(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    decision = normalize_text(update.message.text or "")
    if decision not in {YES, NO}:
        await update.message.reply_text("Responda apenas com Sim ou Nao.")
        return CONFIRMING_DOWNLOAD

    if decision == NO:
        await update.message.reply_text(
            "Cancelado. Envie /start para baixar outra midia.",
            reply_markup=ReplyKeyboardRemove(),
        )
        clear_flow_data(context)
        return ConversationHandler.END

    url = context.user_data.get("url")
    media_format = context.user_data.get("selected_format") or get_default_format(context)
    if not url or not media_format:
        await update.message.reply_text(
            "Dados da sessao nao encontrados. Envie /start novamente.",
            reply_markup=ReplyKeyboardRemove(),
        )
        clear_flow_data(context)
        return ConversationHandler.END

    semaphore = get_download_semaphore(context)
    context.application.bot_data[PENDING_DOWNLOADS_KEY] = int(
        context.application.bot_data.get(PENDING_DOWNLOADS_KEY, 0)
    ) + 1
    entered_semaphore = False

    if semaphore.locked():
        await update.message.reply_text(
            f"Temos {MAX_CONCURRENT_DOWNLOADS} downloads em andamento. "
            "Seu pedido entrou na fila e vai iniciar automaticamente."
        )

    try:
        async with semaphore:
            entered_semaphore = True
            _decrement_bot_counter(context, PENDING_DOWNLOADS_KEY)
            context.application.bot_data[ACTIVE_DOWNLOADS_KEY] = int(
                context.application.bot_data.get(ACTIVE_DOWNLOADS_KEY, 0)
            ) + 1
            context.user_data["is_downloading"] = True

            await update.message.reply_text("Baixando midia, aguarde...")
            try:
                with tempfile.TemporaryDirectory() as temp_dir:
                    file_path = await asyncio.to_thread(download_media, url, media_format, temp_dir)
                    if get_rename_enabled(context):
                        info = context.user_data.get("info") or {}
                        file_path = rename_downloaded_file(file_path, str(info.get("title") or "midia"))
                    await safe_send_chat_action(context, update.effective_chat.id)
                    await send_media_with_retries(
                        context=context,
                        chat_id=update.effective_chat.id,
                        file_path=file_path,
                        media_format=media_format,
                    )

            except Exception as exc:
                logger.exception("Falha no download/envio")
                await update.message.reply_text(f"Erro ao baixar/enviar a midia: {exc}")
                clear_flow_data(context)
                return ConversationHandler.END
    finally:
        if entered_semaphore:
            _decrement_bot_counter(context, ACTIVE_DOWNLOADS_KEY)
        else:
            _decrement_bot_counter(context, PENDING_DOWNLOADS_KEY)
        context.user_data.pop("is_downloading", None)

    await update.message.reply_text(
        "Download concluido. Envie /start para outro link.",
        reply_markup=ReplyKeyboardRemove(),
    )
    clear_flow_data(context)
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "Operacao cancelada. Envie /start para reiniciar.",
        reply_markup=ReplyKeyboardRemove(),
    )
    clear_flow_data(context)
    return ConversationHandler.END


def build_conversation_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CHOOSING_FORMAT: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_format)],
            WAITING_URL: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_url)],
            CONFIRMING_DOWNLOAD: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_download)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,
    )
