from typing import Dict, List, Tuple

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from .formatters import format_singers, format_interval


def build_search_results_message(songs: List[Dict], header: str = "") -> Tuple[str, InlineKeyboardMarkup]:
    """构建搜索结果消息和键盘"""
    if not header:
        text = "🔍 搜索结果:\n\n"
    else:
        text = header

    keyboard = []

    for i, song in enumerate(songs):
        text += (
            f"{i + 1}. {song['name']} - {format_singers(song['singer'])} "
            f"| 专辑: {song['album']['name']} | 时长: {format_interval(song['interval'])} \n"
        )
        keyboard.append([
            InlineKeyboardButton(
                f"{i + 1}. {song['name']} - {format_singers(song['singer'])} | 时长: {format_interval(song['interval'])}",
                callback_data=f"song:{i}"
            )
        ])

    nav_buttons = [
        InlineKeyboardButton("⬅️ 上一页", callback_data="page:prev"),
        InlineKeyboardButton("➡️ 下一页", callback_data="page:next"),
    ]
    keyboard.append(nav_buttons)

    return text, InlineKeyboardMarkup(keyboard)


def build_playlist_results_message(playlists: List[Dict], header: str = "") -> Tuple[str, InlineKeyboardMarkup]:
    if not header:
        text = "🎵 歌单搜索结果:\n\n"
    else:
        text = header

    keyboard = []

    for i, playlist in enumerate(playlists):
        name = str(playlist.get("dissname") or playlist.get("name") or "未知歌单")
        creator = str(playlist.get("nickname") or playlist.get("creator") or "未知")
        count = playlist.get("songnum") or playlist.get("song_count") or 0
        text += f"{i + 1}. {name} | 创建者: {creator} | 歌曲数: {count}\n"
        keyboard.append([
            InlineKeyboardButton(
                f"{i + 1}. {name} ({count})",
                callback_data=f"plist:{i}",
            )
        ])

    return text, InlineKeyboardMarkup(keyboard)


def build_song_list_preview(songs: List[Dict], limit: int = 20) -> str:
    total = len(songs)
    shown = min(total, limit)
    lines = [f"🎵 歌单包含 {total} 首歌曲，预览前 {shown} 首："]

    for i, song in enumerate(songs[:limit], start=1):
        name = str(song.get("name") or "未知歌曲")
        singer_info = song.get("singer")
        if isinstance(singer_info, list):
            singers = format_singers(singer_info)
        elif isinstance(singer_info, str):
            singers = singer_info
        else:
            singers = "未知歌手"
        lines.append(f"{i}. {name} - {singers}")

    if total > limit:
        lines.append("...（仅展示部分歌曲）")

    return "\n".join(lines)
