from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from ..utils.chat_guard import ensure_private_chat


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await ensure_private_chat(update, context):
        return
    is_admin = update.effective_user and update.effective_user.id in set(context.bot_data.get("admin_ids", []))

    help_text = (
        "🎵 音乐机器人使用指南\n\n"
        "基本命令:\n"
        "/search 歌曲名 - 搜索歌曲并点选下载\n"
        "/playlist 歌单链接或ID - 提交歌单并下载到服务器\n"
        "/psearch 歌单关键词 - 搜索歌单并点选下载\n"
        "/help - 显示帮助信息\n\n"
    )

    if is_admin:
        help_text += (
            "管理员命令:\n"
            "/login [QQ|WX] - 获取二维码并登录QQ音乐\n"
            "/setlimits <歌单额度> <单曲额度> - 设置普通用户每日额度\n"
            "/setquality <音质> - 设置单曲回传音质\n"
            "/setplaylistquality <音质列表> - 设置歌单落盘音质\n"
            "/setdir <保存目录> - 设置下载保存目录\n"
            "/setlogintype <QQ|WX> - 设置默认二维码类型\n\n"
        )

    help_text += (
        "说明:\n"
        "- 单曲下载会回传文件并消耗单曲额度\n"
        "- 歌单投稿只下载到服务器，不回传文件\n"
        "- 每日额度在 0 点重置"
    )
    await update.message.reply_text(help_text)


def register(app):
    app.add_handler(CommandHandler("help", help_command))
