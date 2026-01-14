import importlib
from pathlib import Path

from telegram import (
    BotCommand,
    BotCommandScopeAllGroupChats,
    BotCommandScopeAllPrivateChats,
    BotCommandScopeChat,
    BotCommandScopeDefault,
)
from telegram.ext import ApplicationBuilder

from .utils.config import config
from .utils.logger import logger
from .services.download_queue import playlist_download_queue, single_download_queue


class QQMusicBot:
    def __init__(self):
        self.app = (
            ApplicationBuilder()
            .token(config.BOT_TOKEN)
            .base_url(config.API_BASE_URL)
            .post_init(self._post_init)
            .build()
        )
        self._register_handlers()

    def _register_handlers(self):
        commands_dir = Path(__file__).parent / "commands"
        for file in commands_dir.glob("*.py"):
            if file.name == "__init__.py":
                continue
            module_name = f"tgbot_standalone.commands.{file.stem}"
            module = importlib.import_module(module_name)
            if hasattr(module, "register"):
                module.register(self.app)

        callbacks_dir = Path(__file__).parent / "callbacks"
        for file in callbacks_dir.glob("*.py"):
            if file.name == "__init__.py":
                continue
            module_name = f"tgbot_standalone.callbacks.{file.stem}"
            module = importlib.import_module(module_name)
            if hasattr(module, "register"):
                module.register(self.app)

    def run(self):
        logger.info("音乐机器人启动中...")
        self.app.run_polling()

    async def _post_init(self, app):
        await single_download_queue.start(config.SINGLE_CONCURRENT)
        await playlist_download_queue.start(config.PLAYLIST_CONCURRENT)
        await self._set_bot_commands(app)
        app.bot_data["admin_ids"] = config.ADMIN_IDS
        print("音乐机器人已启动", flush=True)

    async def _set_bot_commands(self, app):
        default_commands = [
            BotCommand("search", "搜索歌曲并点选下载"),
        ]
        private_commands = [
            BotCommand("start", "开始使用机器人"),
            BotCommand("help", "查看帮助"),
            BotCommand("search", "搜索歌曲并点选下载"),
            BotCommand("playlist", "提交歌单链接并落盘下载"),
            BotCommand("psearch", "搜索歌单并点选下载"),
        ]
        admin_commands = [
            BotCommand("login", "获取二维码并登录QQ音乐"),
            BotCommand("setlimits", "设置普通用户每日额度"),
            BotCommand("setquality", "设置单曲回传音质"),
            BotCommand("setplaylistquality", "设置歌单落盘音质"),
            BotCommand("setdir", "设置下载保存目录"),
            BotCommand("setlogintype", "设置默认二维码类型"),
        ]

        try:
            await app.bot.set_my_commands(
                default_commands, scope=BotCommandScopeDefault()
            )
        except Exception as exc:
            logger.warning(f"设置默认命令失败: {exc}")

        try:
            await app.bot.set_my_commands(
                default_commands, scope=BotCommandScopeAllGroupChats()
            )
        except Exception as exc:
            logger.warning(f"设置群聊命令失败: {exc}")

        try:
            await app.bot.set_my_commands(
                private_commands, scope=BotCommandScopeAllPrivateChats()
            )
        except Exception as exc:
            logger.warning(f"设置私聊命令失败: {exc}")

        for admin_id in config.ADMIN_IDS:
            try:
                await app.bot.set_my_commands(
                    private_commands + admin_commands,
                    scope=BotCommandScopeChat(chat_id=admin_id),
                )
            except Exception as exc:
                logger.warning(f"设置管理员命令失败: {exc}")


if __name__ == "__main__":
    bot = QQMusicBot()
    bot.run()
