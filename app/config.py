import os

from dotenv import load_dotenv


def load_token() -> str:
    load_dotenv()
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("Defina TELEGRAM_BOT_TOKEN no ambiente (.env).")
    return token


def load_admin_chat_id() -> int | None:
    load_dotenv()
    value = os.getenv("ADMIN_CHAT_ID")
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        raise RuntimeError("ADMIN_CHAT_ID deve ser um numero inteiro (chat id do Telegram).")
