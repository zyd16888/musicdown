from telegram import Update
from telegram.ext import CallbackQueryHandler, ContextTypes

from ..api.qqmusic import QQMusicAPI
from ..utils.config import config
from ..utils.message_builders import build_search_results_message

qq_music_api = QQMusicAPI()


async def handle_pagination(update: Update, context: ContextTypes.DEFAULT_TYPE):
    callback_query = update.callback_query
    user_id = callback_query.from_user.id
    action = callback_query.data.split(":")[1]

    await callback_query.answer()

    if user_id not in config.user_sessions:
        await callback_query.message.edit_text("会话已过期，请重新搜索")
        return

    current_page = config.user_sessions[user_id]["current_page"]
    query = config.user_sessions[user_id].get("last_query", "")

    if action == "next":
        next_page = current_page + 1
        try:
            search_result = await qq_music_api.search(query, limit=10, page=next_page)
            if search_result["code"] == -1 or not search_result.get("songs"):
                await callback_query.answer("没有更多结果了")
                return

            config.user_sessions[user_id]["search_results"] = search_result["songs"]
            config.user_sessions[user_id]["current_page"] = next_page

            _, keyboard = build_search_results_message(search_result["songs"])
            await callback_query.message.edit_text("🔍 搜索结果:", reply_markup=keyboard)

        except Exception as e:
            await callback_query.answer(f"加载下一页失败: {str(e)}")

    elif action == "prev":
        if current_page <= 1:
            await callback_query.answer("已经是第一页")
            return

        prev_page = current_page - 1
        try:
            search_result = await qq_music_api.search(query, limit=10, page=prev_page)

            config.user_sessions[user_id]["search_results"] = search_result["songs"]
            config.user_sessions[user_id]["current_page"] = prev_page

            text, keyboard = build_search_results_message(search_result["songs"])
            await callback_query.message.edit_text(text, reply_markup=keyboard)

        except Exception as e:
            await callback_query.answer(f"加载上一页失败: {str(e)}")


def register(app):
    app.add_handler(CallbackQueryHandler(handle_pagination, pattern=r"^page:(next|prev)$"))
