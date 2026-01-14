from telegram import Update
from telegram.ext import CallbackQueryHandler, ContextTypes

from ..services.playlist import fetch_playlist_songs, download_playlist_songs
from ..services.quota import quota_manager
from ..utils.config import config
from ..utils.permissions import is_admin
from ..utils.chat_guard import ensure_private_chat
from ..utils.logger import logger
from ..utils.message_builders import build_song_list_preview


def _extract_playlist_id(item):
    if not isinstance(item, dict):
        return None
    for key in ("dissid", "id", "listid", "dirid", "tid"):
        value = item.get(key)
        if value is None:
            continue
        if isinstance(value, int):
            return value
        value_str = str(value)
        if value_str.isdigit():
            return int(value_str)
    return None


async def handle_playlist_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    callback_query = update.callback_query
    await callback_query.answer()

    if not await ensure_private_chat(update, context):
        return

    user_id = callback_query.from_user.id
    try:
        index = int(callback_query.data.split(":")[1])
    except Exception:
        await callback_query.message.edit_text("无效的选择，请重新搜索")
        return

    session = config.user_sessions.get(user_id, {})
    playlists = session.get("playlist_search_results") or []
    if not playlists:
        await callback_query.message.edit_text("会话已过期，请重新搜索")
        return

    if index < 0 or index >= len(playlists):
        await callback_query.message.edit_text("无效的选择，请重新搜索")
        return

    selected = playlists[index]
    playlist_id = _extract_playlist_id(selected)
    if not playlist_id:
        await callback_query.message.edit_text("❌ 无法解析歌单ID，请重新搜索")
        return

    await callback_query.message.edit_text("🔗 正在获取歌单信息...")

    try:
        songs = await fetch_playlist_songs(playlist_id)
    except Exception as e:
        await callback_query.message.edit_text(f"❌ 获取歌单失败: {str(e)}")
        return

    if not songs:
        await callback_query.message.edit_text("❌ 歌单中未获取到可下载的歌曲。")
        return

    if not is_admin(user_id):
        ok, _, limit = await quota_manager.consume(user_id, "playlist", amount=1)
        if not ok:
            await callback_query.message.edit_text(
                f"❌ 今日歌单投稿额度已用完（上限 {limit} 次）。"
            )
            return

    await context.bot.send_message(
        chat_id=callback_query.message.chat_id,
        text=build_song_list_preview(songs),
    )
    await callback_query.message.edit_text("✅ 歌单解析成功，开始下载歌曲...")

    last_update = {"index": 0}

    def progress_cb(index: int, total: int, success: int, failed: int, quality: str):
        if index == 1 or index == total or index - last_update["index"] >= 5:
            last_update["index"] = index
            context.application.create_task(
                callback_query.message.edit_text(
                    f"⏳ 下载中 {index}/{total} | 成功 {success} 失败 {failed} | 音质 {quality}"
                )
            )

    total, success, failed = await download_playlist_songs(
        playlist_id,
        songs=songs,
        progress_cb=progress_cb,
    )

    if total == 0:
        await callback_query.message.edit_text("❌ 歌单中未获取到可下载的歌曲。")
        return

    qualities_text = ", ".join(config.PLAYLIST_QUALITIES)
    await callback_query.message.edit_text(
        f"✅ 歌单下载完成：成功 {success} 首，失败 {failed} 首。\n"
        f"音质: {qualities_text}\n"
        f"文件已保存到: {config.DOWNLOADS_DIR}"
    )


def register(app):
    app.add_handler(CallbackQueryHandler(handle_playlist_selection, pattern=r"^plist:(\d+)$"))
