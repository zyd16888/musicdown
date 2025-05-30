from telegram import Update
from telegram.ext import ContextTypes, CommandHandler


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"👋 你好 {update.message.from_user.first_name}！\n\n"
        "我是QQ音乐机器人，可以帮你搜索和下载QQ音乐上的歌曲。\n"
        "使用 /search 命令加歌曲名来搜索歌曲，例如：\n"
        "/search 周杰伦 稻香\n\n"
        "使用 /help 查看更多命令。"
    )


def register(app):
    app.add_handler(CommandHandler("start", start))
