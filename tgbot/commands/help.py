from pyrogram import Client, filters
from pyrogram.types import Message


def register(app: Client):
    @app.on_message(filters.command("help") & filters.private)
    async def help_command(client, message: Message):
        help_text = (
            "🎵 **QQ音乐机器人使用指南** 🎵\n\n"
            "**基本命令：**\n"
            "/search 歌曲名 - 搜索歌曲\n"
            "/album 专辑ID - 获取专辑歌曲\n"
            "/playlist 歌单ID - 获取歌单歌曲\n"
            "/help - 显示帮助信息\n\n"
            "**使用方法：**\n"
            "1. 发送 /search 命令加歌曲名搜索歌曲\n"
            "2. 从搜索结果中选择歌曲\n"
            "3. 机器人将下载并发送歌曲文件"
        )
        await message.reply(help_text)
