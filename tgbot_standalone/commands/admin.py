import io

from telegram import InputFile, Update
from telegram.ext import CommandHandler, ContextTypes

from ..api.qqmusic import QQMusicAPI
from ..utils.config import config
from ..utils.permissions import is_admin
from ..utils.logger import logger
from ..utils.chat_guard import ensure_private_chat

_login_task = None


async def login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await ensure_private_chat(update, context):
        return

    user_id = update.message.from_user.id
    if not is_admin(user_id):
        await update.message.reply_text("❌ 无权限执行该命令")
        return

    global _login_task
    if _login_task and not _login_task.done():
        await update.message.reply_text("⏳ 当前已有登录流程在进行中，请稍后再试。")
        return

    login_type = config.QR_LOGIN_TYPE
    if context.args:
        candidate = context.args[0].strip().upper()
        if candidate in {"QQ", "WX"}:
            login_type = candidate
        else:
            await update.message.reply_text("用法：/login [QQ|WX]")
            return

    status_message = await update.message.reply_text("正在生成二维码...")
    api = QQMusicAPI()

    async def send_qr(data: bytes):
        if not data:
            await status_message.edit_text("❌ 二维码生成失败")
            return
        qr_file = io.BytesIO(data)
        qr_file.name = "qqmusic_qr.png"
        await context.bot.send_photo(
            chat_id=update.effective_chat.id,
            photo=InputFile(qr_file),
            caption="请使用手机扫码登录QQ音乐",
        )

    async def update_status(text: str):
        try:
            await status_message.edit_text(text)
        except Exception as exc:
            logger.warning(f"更新登录状态失败: {exc}")

    def login_callback(event_type, data):
        if event_type == "qr_generated":
            context.application.create_task(send_qr(data))
        elif event_type in {"waiting_scan", "waiting_confirm"}:
            context.application.create_task(update_status(str(data)))
        elif event_type == "login_success":
            context.application.create_task(update_status("✅ 登录成功，凭证已保存"))
        elif event_type in {"timeout", "refused", "error"}:
            context.application.create_task(update_status(f"❌ {data}"))

    async def run_login():
        success, _, error_msg = await api.login_with_qr(login_type, login_callback)
        if not success and error_msg:
            await update_status(f"❌ {error_msg}")

    _login_task = context.application.create_task(run_login())


async def setlimits(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await ensure_private_chat(update, context):
        return

    user_id = update.message.from_user.id
    if not is_admin(user_id):
        await update.message.reply_text("❌ 无权限执行该命令")
        return

    if len(context.args) != 2:
        await update.message.reply_text("用法：/setlimits <歌单额度> <单曲额度>")
        return

    try:
        playlist_limit = int(context.args[0])
        song_limit = int(context.args[1])
    except ValueError:
        await update.message.reply_text("额度必须是整数")
        return

    if playlist_limit < 0 or song_limit < 0:
        await update.message.reply_text("额度必须为非负整数")
        return

    config.set_limits(playlist_limit, song_limit)
    await update.message.reply_text(
        f"✅ 已更新额度：歌单 {config.PLAYLIST_LIMIT_PER_DAY} / 单曲 {config.SONG_LIMIT_PER_DAY}"
    )


async def setquality(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await ensure_private_chat(update, context):
        return

    user_id = update.message.from_user.id
    if not is_admin(user_id):
        await update.message.reply_text("❌ 无权限执行该命令")
        return

    if len(context.args) != 1:
        await update.message.reply_text("用法：/setquality <m4a|128|320|flac|ATMOS_51|ATMOS_2|MASTER>")
        return

    quality = context.args[0].strip()
    valid = {"m4a", "128", "320", "flac", "ATMOS_51", "ATMOS_2", "MASTER"}
    if quality not in valid:
        await update.message.reply_text("❌ 无效音质，请使用: m4a/128/320/flac/ATMOS_51/ATMOS_2/MASTER")
        return

    config.set_quality(quality)
    await update.message.reply_text(f"✅ 已更新音质为: {config.DEFAULT_QUALITY}")


async def setplaylistquality(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await ensure_private_chat(update, context):
        return

    user_id = update.message.from_user.id
    if not is_admin(user_id):
        await update.message.reply_text("❌ 无权限执行该命令")
        return

    if not context.args:
        await update.message.reply_text(
            "用法：/setplaylistquality <音质列表>\n例：/setplaylistquality 128,320,flac"
        )
        return

    raw = " ".join(context.args).strip()
    if "," in raw:
        items = [item.strip() for item in raw.split(",") if item.strip()]
    else:
        items = [item.strip() for item in context.args if item.strip()]

    valid = {"m4a", "128", "320", "flac", "ATMOS_51", "ATMOS_2", "MASTER"}
    invalid = [item for item in items if item not in valid]
    if invalid or not items:
        await update.message.reply_text(
            "❌ 音质列表不合法，请使用: m4a/128/320/flac/ATMOS_51/ATMOS_2/MASTER"
        )
        return

    config.set_playlist_qualities(items)
    await update.message.reply_text(
        f"✅ 已更新歌单音质为: {', '.join(config.PLAYLIST_QUALITIES)}"
    )


async def setdir(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await ensure_private_chat(update, context):
        return

    user_id = update.message.from_user.id
    if not is_admin(user_id):
        await update.message.reply_text("❌ 无权限执行该命令")
        return

    if not context.args:
        await update.message.reply_text("用法：/setdir <保存目录>")
        return

    download_dir = " ".join(context.args).strip()
    if not download_dir:
        await update.message.reply_text("❌ 保存目录不能为空")
        return

    config.set_download_dir(download_dir)
    await update.message.reply_text(f"✅ 已更新保存目录为: {config.DOWNLOADS_DIR}")


async def setlogintype(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await ensure_private_chat(update, context):
        return

    user_id = update.message.from_user.id
    if not is_admin(user_id):
        await update.message.reply_text("❌ 无权限执行该命令")
        return

    if len(context.args) != 1:
        await update.message.reply_text("用法：/setlogintype <QQ|WX>")
        return

    login_type = context.args[0].strip().upper()
    if login_type not in {"QQ", "WX"}:
        await update.message.reply_text("❌ 登录类型只支持 QQ 或 WX")
        return

    config.config_file.set("login.qrType", login_type)
    config.reload_config()
    await update.message.reply_text(f"✅ 已更新登录二维码类型为: {config.QR_LOGIN_TYPE}")


def register(app):
    app.add_handler(CommandHandler("login", login))
    app.add_handler(CommandHandler("setlimits", setlimits))
    app.add_handler(CommandHandler("setquality", setquality))
    app.add_handler(CommandHandler("setplaylistquality", setplaylistquality))
    app.add_handler(CommandHandler("setdir", setdir))
    app.add_handler(CommandHandler("setlogintype", setlogintype))
