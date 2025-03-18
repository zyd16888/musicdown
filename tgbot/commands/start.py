from pyrogram import Client, filters
from pyrogram.types import Message


def register(app: Client):
    @app.on_message(filters.command("start") & filters.private)
    async def start_command(client, message: Message):
        await message.reply(
            f"👋 你好 {message.from_user.first_name}！\n\n"
            "我是QQ音乐机器人，可以帮你搜索和下载QQ音乐上的歌曲。\n"
            "使用 /search 命令加歌曲名来搜索歌曲，例如：\n"
            "/search 周杰伦 稻香\n\n"
            "使用 /help 查看更多命令。"
        )
