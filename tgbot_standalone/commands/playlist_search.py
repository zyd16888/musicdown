from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from ..api.qqmusic import QQMusicAPI
from ..utils.config import config
from ..utils.message_builders import build_playlist_results_message
from ..utils.chat_guard import ensure_private_chat

qq_music_api = QQMusicAPI()


async def playlist_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await ensure_private_chat(update, context):
        return

    if not context.args:
        await update.message.reply_text("请输入要搜索的歌单关键词，例如：/psearch 放松")
        return

    query = " ".join(context.args)
    user_id = update.message.from_user.id

    status_message = await update.message.reply_text("🔍 正在搜索歌单，请稍候...")

    try:
        result = await qq_music_api.search_playlist(query, limit=10, page=1)
        playlists = result.get("playlists") or []
        if result.get("code") == -1 or not playlists:
            await status_message.edit_text("❌ 未找到相关歌单，请尝试其他关键词。")
            return

        session = config.user_sessions.setdefault(user_id, {})
        session["playlist_search_results"] = playlists
        session["playlist_search_query"] = query
        session["playlist_search_page"] = 1

        _, keyboard = build_playlist_results_message(playlists)
        await status_message.edit_text("🔍 歌单搜索结果:", reply_markup=keyboard)

    except Exception as e:
        await status_message.edit_text(f"❌ 搜索出错: {str(e)}")


def register(app):
    app.add_handler(CommandHandler("psearch", playlist_search))
