from utils.config import config, ConfigManager
from telegram.ext import ContextTypes, CallbackQueryHandler, ConversationHandler, MessageHandler, filters, CommandHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
import sys
import json
from pathlib import Path

# 确保可以导入项目根目录的模块
current_dir = Path(__file__).parent
project_root = current_dir.parent.parent
sys.path.insert(0, str(project_root))


# 定义状态
WAITING_COOKIE = 1
WAITING_QUALITY = 2

# 音质选项
QUALITY_OPTIONS = {
    "m4a": "标准品质 M4A",
    "128": "标准品质 MP3 128k",
    "320": "高品质 MP3 320k",
    "flac": "无损品质 FLAC",
    "ATMOS_51": "臻品音质2.0",
    "ATMOS_2": "臻品全景声2.0",
    "MASTER": "臻品母带2.0"
}

# 对话状态存储
conversation_states = {}


async def handle_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理设置菜单的回调"""
    callback_query = update.callback_query
    user_id = callback_query.from_user.id
    action = callback_query.data.split(":")[1]

    await callback_query.answer()  # 必须应答回调查询

    if action == "cookie":
        await callback_query.message.edit_text(
            "🍪 更新QQ音乐Cookie\n\n"
            "请发送新的QQ音乐Cookie字符串。\n"
            "获取方法：登录QQ音乐网页版，从浏览器开发者工具中复制Cookie。\n\n"
            "发送 /cancel 取消操作。"
        )
        # 设置用户状态为等待输入Cookie
        conversation_states[user_id] = WAITING_COOKIE
        return WAITING_COOKIE

    elif action == "quality":
        # 创建音质选择菜单
        keyboard = []
        current_quality = config.DEFAULT_QUALITY

        for quality_key, quality_name in QUALITY_OPTIONS.items():
            # 在当前选中的音质前添加标记
            mark = "✅ " if quality_key == current_quality else ""
            keyboard.append([InlineKeyboardButton(
                f"{mark}{quality_name}", callback_data=f"quality:{quality_key}")])

        # 添加返回按钮
        keyboard.append([InlineKeyboardButton(
            "返回", callback_data="settings:back")])

        reply_markup = InlineKeyboardMarkup(keyboard)

        await callback_query.message.edit_text(
            "🎵 音乐音质设置\n\n"
            "请选择下载音乐的音质：\n"
            "注意：高音质选项可能需要VIP权限",
            reply_markup=reply_markup
        )
        return WAITING_QUALITY

    elif action == "back":
        # 返回主设置菜单
        keyboard = [
            [InlineKeyboardButton(
                "更新QQ音乐Cookie", callback_data="settings:cookie")],
            [InlineKeyboardButton("设置音乐音质", callback_data="settings:quality")],
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        await callback_query.message.edit_text(
            "⚙️ 机器人设置\n\n"
            "请选择要修改的设置项：",
            reply_markup=reply_markup
        )
        return ConversationHandler.END


async def handle_quality_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理音质选择的回调"""
    callback_query = update.callback_query
    quality = callback_query.data.split(":")[1]

    await callback_query.answer()  # 必须应答回调查询

    try:
        # 更新配置
        config_file_path = "config.json"
        with open(config_file_path, "r", encoding="utf-8") as f:
            config_data = json.load(f)

        config_data["quality"] = quality

        with open(config_file_path, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=2, ensure_ascii=False)

        # 重新加载配置到内存
        config.reload_config()

        # 创建更新后的音质选择菜单
        keyboard = []
        for quality_key, quality_name in QUALITY_OPTIONS.items():
            mark = "✅ " if quality_key == quality else ""
            keyboard.append([InlineKeyboardButton(
                f"{mark}{quality_name}", callback_data=f"quality:{quality_key}")])

        # 添加返回按钮
        keyboard.append([InlineKeyboardButton(
            "返回", callback_data="settings:back")])

        reply_markup = InlineKeyboardMarkup(keyboard)

        await callback_query.message.edit_text(
            f"✅ 音乐音质已更新为: {QUALITY_OPTIONS[quality]}\n\n"
            "请选择下载音乐的音质：",
            reply_markup=reply_markup
        )

    except Exception as e:
        await callback_query.message.edit_text(f"❌ 更新音质设置失败: {str(e)}")
        return ConversationHandler.END


async def handle_cookie_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理用户输入的Cookie"""
    user_id = update.message.from_user.id

    # 检查用户是否在等待输入Cookie状态
    if user_id not in conversation_states or conversation_states[user_id] != WAITING_COOKIE:
        return ConversationHandler.END

    new_cookie = update.message.text

    # 删除用户的消息以保护隐私
    try:
        await update.message.delete()
    except:
        pass

    try:
        # 更新配置
        config_file_path = "config.json"
        with open(config_file_path, "r", encoding="utf-8") as f:
            config_data = json.load(f)

        config_data["qqmusic"]["cookie"] = new_cookie

        with open(config_file_path, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=2, ensure_ascii=False)

        # 重新加载配置到内存
        config.reload_config()

        # 发送成功消息
        await context.bot.send_message(
            chat_id=user_id,
            text="✅ QQ音乐Cookie已成功更新！"
        )

    except Exception as e:
        await context.bot.send_message(
            chat_id=user_id,
            text=f"❌ 更新Cookie失败: {str(e)}"
        )

    # 清除用户状态
    if user_id in conversation_states:
        del conversation_states[user_id]

    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """取消当前操作"""
    user_id = update.message.from_user.id

    # 清除用户状态
    if user_id in conversation_states:
        del conversation_states[user_id]

    await update.message.reply_text("❌ 操作已取消")
    return ConversationHandler.END


def register(app):
    # 注册设置回调处理程序
    app.add_handler(CallbackQueryHandler(handle_settings,
                    pattern=r"^settings:(cookie|quality|back)$"))
    app.add_handler(CallbackQueryHandler(
        handle_quality_selection, pattern=r"^quality:"))

    # 注册消息处理程序来捕获Cookie输入
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND, handle_cookie_input))
    app.add_handler(CommandHandler("cancel", cancel))
