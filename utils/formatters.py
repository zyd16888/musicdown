from pathlib import Path
from typing import Dict, List
from urllib.parse import urlparse

from utils.config import config


def format_singers(singers: List[Dict]) -> str:
    """格式化歌手列表为字符串"""
    return ", ".join([singer['name'] for singer in singers])


def format_interval(interval: int) -> str:
    minutes = interval // 60  # 计算分钟
    seconds = interval % 60  # 计算剩余秒数
    duration = f"{minutes}:{seconds:02d}"  # 格式化成 mm:ss
    return duration


def get_audio_extension(url: str) -> str:
    """获取音频文件扩展名"""
    ext = Path(urlparse(url).path).suffix.lower()

    valid_extensions = {".mp3", ".flac", ".wav", ".aac", ".ogg", ".m4a"}
    if ext not in valid_extensions:
        ext = ".mp3"  # 默认值

    return ext


async def get_file_path(selected_song: Dict, song_url: str):
    """获取下载文件路径"""
    ext = get_audio_extension(song_url)
    filename = f"{selected_song['name']} - {format_singers(selected_song['singer'])}{ext}"
    safe_filename = "".join(
        c for c in filename if c.isalnum() or c in " -_.").strip()
    filepath = config.DOWNLOADS_DIR / safe_filename
    return filepath
