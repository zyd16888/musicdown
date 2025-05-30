from utils.config import config, ConfigManager
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler
import sys
from pathlib import Path

# 确保可以导入项目根目录的模块
current_dir = Path(__file__).parent
project_root = current_dir.parent.parent
sys.path.insert(0, str(project_root))


async def settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理设置命令，显示设置选项"""
    user_id = update.message.from_user.id

    # 检查用户是否为管理员
    # 这里可以添加管理员检查逻辑，目前简单实现

    # 创建设置菜单
    keyboard = [
        [InlineKeyboardButton(
            "更新QQ音乐Cookie", callback_data="settings:cookie")],
        [InlineKeyboardButton("设置音乐音质", callback_data="settings:quality")],
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "⚙️ 机器人设置\n\n"
        "请选择要修改的设置项：",
        reply_markup=reply_markup
    )


def register(app):
    app.add_handler(CommandHandler("settings", settings))
