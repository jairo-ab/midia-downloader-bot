import html


def normalize_text(value: str) -> str:
    return (
        value.strip()
        .lower()
        .replace("á", "a")
        .replace("ã", "a")
        .replace("â", "a")
        .replace("é", "e")
        .replace("ê", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ô", "o")
        .replace("õ", "o")
        .replace("ú", "u")
        .replace("ç", "c")
    )


def is_probably_url(text: str) -> bool:
    text = text.strip().lower()
    return text.startswith("http://") or text.startswith("https://")


def format_duration(seconds: int | float | None) -> str:
    if seconds is None:
        return "desconhecida"

    try:
        total_seconds = int(seconds)
    except (TypeError, ValueError):
        return "desconhecida"

    if total_seconds < 0:
        return "desconhecida"

    hours, rem = divmod(total_seconds, 3600)
    minutes, secs = divmod(rem, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def escape_html(text: str) -> str:
    return html.escape(text)
