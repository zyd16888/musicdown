from typing import Dict, List, Tuple

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from utils.formatters import format_singers, format_interval


def build_search_results_message(songs: List[Dict], header: str = "") -> Tuple[str, InlineKeyboardMarkup]:
    """构建搜索结果消息和键盘"""
    if not header:
        text = "🔍 搜索结果:\n\n"
    else:
        text = header

    keyboard = []

    for i, song in enumerate(songs):
        text += f"{i + 1}. {song['name']} - {format_singers(song['singer'])} | 专辑: {song['album']['name']} | 时长: {format_interval(song['interval'])} \n"
        keyboard.append([InlineKeyboardButton(
            f"{i + 1}. {song['name']} - {format_singers(song['singer'])} | 时长: {format_interval(song['interval'])}",
            callback_data=f"song:{i}")])

    # 添加翻页按钮
    nav_buttons = []
    nav_buttons.append(InlineKeyboardButton(
        "⬅️ 上一页", callback_data="page:prev"))
    nav_buttons.append(InlineKeyboardButton(
        "➡️ 下一页", callback_data="page:next"))
    keyboard.append(nav_buttons)

    return text, InlineKeyboardMarkup(keyboard)


def build_album_results_message(songs: List[Dict]) -> Tuple[str, InlineKeyboardMarkup]:
    """构建专辑歌曲列表消息和键盘"""
    text = "💿 专辑歌曲列表:\n\n"

    keyboard = []

    for i, song in enumerate(songs):
        song_info = song['songInfo'] if 'songInfo' in song else song
        text += f"{i + 1}. {song_info['name']} - {format_singers(song_info['singer'])}\n"
        keyboard.append([InlineKeyboardButton(
            f"{i + 1}. {song_info['name']}", callback_data=f"song:{i}")])

    return text, InlineKeyboardMarkup(keyboard)
