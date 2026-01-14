from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from ..services.quota import quota_manager
from ..utils.permissions import is_admin
from ..utils.chat_guard import ensure_private_chat


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await ensure_private_chat(update, context):
        return

    user_id = update.message.from_user.id
    if is_admin(user_id):
        quota_text = "管理员账户不限额"
    else:
        remaining = await quota_manager.get_remaining(user_id)
        quota_text = (
            f"今日剩余额度 - 歌单投稿: {remaining['playlist']} | 单曲下载: {remaining['song']}"
        )

    await update.message.reply_text(
        "👋 你好！\n\n"
        "我是音乐机器人，可以搜索歌曲并下载，也支持提交歌单链接批量下载。\n"
        "\n"
        f"{quota_text}\n\n"
        "使用 /help 查看全部命令。"
    )


def register(app):
    app.add_handler(CommandHandler("start", start))
