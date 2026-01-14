from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from ..api.qqmusic import QQMusicAPI
from ..utils.config import config
from ..utils.message_builders import build_search_results_message

qq_music_api = QQMusicAPI()


async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("请输入要搜索的歌曲名，例如：/search 周杰伦 稻香")
        return

    query = " ".join(context.args)
    user_id = update.message.from_user.id

    status_message = await update.message.reply_text("🔍 正在搜索歌曲，请稍候...")

    try:
        search_result = await qq_music_api.search(query, limit=10, page=1)

        if search_result["code"] == -1 or not search_result.get("songs"):
            await status_message.edit_text("❌ 未找到相关歌曲，请尝试其他关键词。")
            return

        config.user_sessions[user_id] = {
            "search_results": search_result["songs"],
            "current_page": 1,
            "last_query": query,
        }

        _, keyboard = build_search_results_message(search_result["songs"])
        await status_message.edit_text("🔍 搜索结果:", reply_markup=keyboard)

    except Exception as e:
        await status_message.edit_text(f"❌ 搜索出错: {str(e)}")


def register(app):
    app.add_handler(CommandHandler("search", search))
