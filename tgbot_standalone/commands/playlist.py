from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from ..services.playlist import resolve_playlist_id, fetch_playlist_songs, download_playlist_songs
from ..services.quota import quota_manager
from ..utils.config import config
from ..utils.permissions import is_admin
from ..utils.chat_guard import ensure_private_chat
from ..utils.message_builders import build_song_list_preview


async def playlist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await ensure_private_chat(update, context):
        return

    user_id = update.message.from_user.id
    if not context.args:
        await update.message.reply_text("请输入歌单链接或ID，例如：/playlist https://y.qq.com/n/ryqq/playlist/123456")
        return

    status_message = await update.message.reply_text("🔗 正在解析歌单链接...")
    playlist_id = await resolve_playlist_id(context.args[0])
    if not playlist_id:
        await status_message.edit_text("❌ 无法解析歌单链接，请检查后重试。")
        return

    try:
        songs = await fetch_playlist_songs(playlist_id)
    except Exception as e:
        await status_message.edit_text(f"❌ 获取歌单失败: {str(e)}")
        return

    if not songs:
        await status_message.edit_text("❌ 歌单中未获取到可下载的歌曲。")
        return

    if not is_admin(user_id):
        ok, _, limit = await quota_manager.consume(user_id, "playlist", amount=1)
        if not ok:
            await status_message.edit_text(
                f"❌ 今日歌单投稿额度已用完（上限 {limit} 次）。"
            )
            return

    await update.message.reply_text(build_song_list_preview(songs))
    await status_message.edit_text("✅ 歌单解析成功，开始下载歌曲...")

    last_update = {"index": 0}

    def progress_cb(index: int, total: int, success: int, failed: int, quality: str):
        if index == 1 or index == total or index - last_update["index"] >= 5:
            last_update["index"] = index
            context.application.create_task(
                status_message.edit_text(
                    f"⏳ 下载中 {index}/{total} | 成功 {success} 失败 {failed} | 音质 {quality}"
                )
            )

    total, success, failed = await download_playlist_songs(
        playlist_id,
        songs=songs,
        progress_cb=progress_cb,
    )

    qualities_text = ", ".join(config.PLAYLIST_QUALITIES)
    await status_message.edit_text(
        f"✅ 歌单下载完成：成功 {success} 首，失败 {failed} 首。\n"
        f"音质: {qualities_text}\n"
        f"文件已保存到: {config.DOWNLOADS_DIR}"
    )


def register(app):
    app.add_handler(CommandHandler("playlist", playlist))
