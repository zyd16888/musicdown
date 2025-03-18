import sys
from pathlib import Path

from pyrogram import Client, filters
from pyrogram.types import Message

from api.qm import QQMusicAPI
from tgbot.utils.message_builders import build_search_results_message
from utils.config import config
from utils.menum import SearchType

# 确保可以导入项目根目录的模块
sys.path.append(str(Path(__file__).parent.parent.parent))

# 初始化QQ音乐API
qq_music_api = QQMusicAPI()


def register(app: Client):
    @app.on_message(filters.command("search") & filters.private)
    async def search_command(client, message: Message):
        # 获取搜索关键词
        if len(message.command) < 2:
            await message.reply("请输入要搜索的歌曲名，例如：/search 周杰伦 稻香")
            return

        query = " ".join(message.command[1:])
        user_id = message.from_user.id

        # 显示搜索中消息
        status_message = await message.reply("🔍 正在搜索歌曲，请稍候...")

        try:
            # 调用API搜索歌曲
            search_result = await qq_music_api.search(query, SearchType.SONG, page=1, limit=10)

            if search_result['code'] == -1 or not search_result.get('songs'):
                await status_message.edit("❌ 未找到相关歌曲，请尝试其他关键词。")
                return

            # 保存搜索结果到用户会话
            config.user_sessions[user_id] = {
                "search_results": search_result['songs'],
                "current_page": 1,
                "last_query": query
            }

            # 构建搜索结果消息和键盘
            text, keyboard = build_search_results_message(
                search_result['songs'])

            await status_message.edit(
                "🔍 搜索结果:",
                reply_markup=keyboard
            )

        except Exception as e:
            await status_message.edit(f"❌ 搜索出错: {str(e)}")
