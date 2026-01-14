import os
import re
import traceback

from telegram import Update
from telegram.ext import CallbackQueryHandler, ContextTypes

from ..services.download_queue import single_download_queue, download_song_job
from ..services.quota import quota_manager
from ..utils.config import config
from ..utils.formatters import format_singers
from ..utils.logger import logger
from ..utils.permissions import is_admin


def _extract_intro(detail) -> str:
    if not isinstance(detail, dict):
        return ""
    info = detail.get("info")
    if not isinstance(info, dict):
        return ""
    intro_info = info.get("intro")
    if not isinstance(intro_info, dict):
        return ""
    content = intro_info.get("content")
    if not isinstance(content, list) or not content:
        return ""
    value = content[0].get("value") if isinstance(content[0], dict) else ""
    text = re.sub(r"\s+", " ", str(value)).strip()
    return text


async def handle_song_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    callback_query = update.callback_query
    user_id = callback_query.from_user.id
    song_index = int(callback_query.data.split(":")[1])

    await callback_query.answer()

    if user_id not in config.user_sessions or "search_results" not in config.user_sessions[user_id]:
        await callback_query.message.edit_text("会话已过期，请重新搜索")
        return

    songs = config.user_sessions[user_id]["search_results"]
    if song_index >= len(songs):
        await callback_query.message.edit_text("无效的选择，请重新搜索")
        return

    if not is_admin(user_id):
        ok, _, limit = await quota_manager.consume(user_id, "song", amount=1)
        if not ok:
            await callback_query.message.edit_text(
                f"❌ 今日单曲下载额度已用完（上限 {limit} 首）。"
            )
            return

    selected_song = songs[song_index]

    await callback_query.message.edit_text(
        f"⏳ 已加入下载队列: {selected_song['name']} - {format_singers(selected_song['singer'])}..."
    )

    try:
        config.reload_config()
        filetype = config.DEFAULT_QUALITY
        download_dir = config.DOWNLOADS_DIR / filetype
        download_dir.mkdir(parents=True, exist_ok=True)

        dedupe_key = None
        if selected_song.get("mid"):
            dedupe_key = f"{selected_song['mid']}:{filetype}"

        persist_payload = {
            "song_info": selected_song,
            "download_dir": str(download_dir),
            "filetype": filetype,
            "cookie": None,
            "fetch_detail": True,
        }

        filepath = await single_download_queue.submit(
            download_song_job,
            selected_song,
            download_dir,
            filetype,
            None,
            True,
            dedupe_key=dedupe_key,
            persist_payload=persist_payload,
        )

        if not filepath:
            error_msg = (
                "❌ 下载歌曲失败，可能原因：\n"
                "- 该歌曲可能需要VIP权限\n"
                "- 歌曲可能有版权限制\n"
                "- 网络连接问题\n"
                "请稍后重试或尝试其他歌曲。"
            )
            await callback_query.message.edit_text(error_msg)
            return

        caption = (
            f"🎵 {selected_song['name']}\n"
            f"👤 {format_singers(selected_song['singer'])}\n"
            f"💿 {selected_song['album']['name']}"
        )
        intro = _extract_intro(selected_song.get("_detail"))
        if intro:
            max_len = 220
            if len(intro) > max_len:
                intro = intro[:max_len].rstrip() + "..."
            caption = f"{caption}\n📝 简介: {intro}"

        await callback_query.message.edit_text(
            f"正在发送音频文件： 🎵 {selected_song['name']} - "
            f"{format_singers(selected_song['singer'])} 💿{selected_song['album']['name']}"
        )

        try:
            with open(str(filepath), "rb") as audio_file:
                await context.bot.send_audio(
                    chat_id=callback_query.message.chat_id,
                    audio=audio_file,
                    title=selected_song["name"],
                    performer=format_singers(selected_song["singer"]),
                    duration=selected_song.get("interval", 0),
                    caption=caption,
                )
        except Exception as send_error:
            error_msg = f"❌ 发送音频文件时出错：\n{str(send_error)}\n请稍后重试。"
            await callback_query.message.edit_text(error_msg)
            return

        await callback_query.message.edit_text(
            f"✅ 歌曲已发送: {selected_song['name']} - {format_singers(selected_song['singer'])}"
        )

    except Exception as e:
        error_details = traceback.format_exc()
        logger.error(f"处理歌曲时出错: {error_details}")

        error_msg = f"❌ 处理歌曲时出错: {str(e)}\n请稍后重试或联系管理员。"
        await callback_query.message.edit_text(error_msg)


def register(app):
    app.add_handler(CallbackQueryHandler(handle_song_selection, pattern=r"^song:(\d+)$"))
