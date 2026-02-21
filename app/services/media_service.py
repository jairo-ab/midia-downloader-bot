import os
import shutil
from pathlib import Path
from typing import Any

import yt_dlp

from app.constants import PREF_MP3


def resolve_ffmpeg_location() -> str | None:
    ffmpeg_on_path = shutil.which("ffmpeg")
    if ffmpeg_on_path:
        return str(Path(ffmpeg_on_path).parent)

    local_app_data = os.getenv("LOCALAPPDATA")
    if not local_app_data:
        return None

    winget_root = Path(local_app_data) / "Microsoft" / "WinGet" / "Packages"
    if not winget_root.exists():
        return None

    candidates = sorted(winget_root.glob("Gyan.FFmpeg*"), key=lambda p: p.stat().st_mtime, reverse=True)
    for candidate in candidates:
        ffmpeg_bins = list(candidate.rglob("ffmpeg.exe"))
        if ffmpeg_bins:
            return str(ffmpeg_bins[0].parent)
    return None


def extract_media_info(url: str) -> dict[str, Any]:
    opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "noplaylist": True,
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)

    if "entries" in info and info["entries"]:
        info = info["entries"][0]

    return {
        "title": info.get("title") or "Sem título",
        "duration": info.get("duration"),
        "uploader": info.get("uploader") or "desconhecido",
        "webpage_url": info.get("webpage_url") or url,
    }


def download_media(url: str, media_format: str, temp_dir: str) -> Path:
    outtmpl = str(Path(temp_dir) / "%(title).200B.%(ext)s")
    opts: dict[str, Any] = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "outtmpl": outtmpl,
    }

    if media_format == PREF_MP3:
        ffmpeg_location = os.getenv("FFMPEG_LOCATION") or resolve_ffmpeg_location()
        opts.update(
            {
                "format": "bestaudio/best",
                "postprocessors": [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": "192",
                    }
                ],
            }
        )
        if ffmpeg_location:
            opts["ffmpeg_location"] = ffmpeg_location
    else:
        opts.update({"format": "bestvideo+bestaudio/best"})

    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.extract_info(url, download=True)

    candidates = sorted(Path(temp_dir).glob("*"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not candidates:
        raise RuntimeError("Não foi possível localizar o arquivo baixado.")
    return candidates[0]
