import sys
from pathlib import Path

from pyrogram import Client, filters
from pyrogram.types import CallbackQuery

from api.qm import QQMusicAPI
from tgbot.utils.message_builders import build_search_results_message
from utils.config import config
from utils.menum import SearchType

# 确保可以导入项目根目录的模块
sys.path.append(str(Path(__file__).parent.parent.parent))

# 初始化QQ音乐API
qq_music_api = QQMusicAPI()


def register(app: Client):
    @app.on_callback_query(filters.regex(r"^page:(next|prev)$"))
    async def handle_pagination(client, callback_query: CallbackQuery):
        user_id = callback_query.from_user.id
        action = callback_query.data.split(":")[1]

        if user_id not in config.user_sessions:
            await callback_query.answer("会话已过期，请重新搜索")
            return

        current_page = config.user_sessions[user_id]["current_page"]
        query = config.user_sessions[user_id].get("last_query", "")

        if action == "next":
            next_page = current_page + 1
            try:
                # 获取下一页搜索结果
                search_result = await qq_music_api.search(query, SearchType.SONG, page=next_page, limit=10)

                if search_result['code'] == -1 or not search_result.get('songs'):
                    await callback_query.answer("没有更多结果了")
                    return

                # 更新用户会话
                config.user_sessions[user_id]["search_results"] = search_result['songs']
                config.user_sessions[user_id]["current_page"] = next_page

                # 更新消息
                text, keyboard = build_search_results_message(
                    search_result['songs'])
                await callback_query.edit_message_text("🔍 搜索结果:", reply_markup=keyboard)

            except Exception as e:
                await callback_query.answer(f"加载下一页失败: {str(e)}")

        elif action == "prev":
            if current_page <= 1:
                await callback_query.answer("已经是第一页")
                return

            prev_page = current_page - 1
            try:
                # 获取上一页搜索结果
                search_result = await qq_music_api.search(query, SearchType.SONG, page=prev_page, limit=10)

                # 更新用户会话
                config.user_sessions[user_id]["search_results"] = search_result['songs']
                config.user_sessions[user_id]["current_page"] = prev_page

                # 更新消息
                text, keyboard = build_search_results_message(
                    search_result['songs'])
                await callback_query.edit_message_text(text, reply_markup=keyboard)

            except Exception as e:
                await callback_query.answer(f"加载上一页失败: {str(e)}")
