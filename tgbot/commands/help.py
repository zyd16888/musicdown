from telegram import Update
from telegram.ext import ContextTypes, CommandHandler


async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    await update.message.reply_text(help_text, parse_mode='Markdown')


def register(app):
    app.add_handler(CommandHandler("help", help))
