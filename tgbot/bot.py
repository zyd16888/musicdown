from utils.config import config
from pyrogram import Client
from pathlib import Path
import importlib
import os
import sys

# 确保可以导入项目根目录的模块
sys.path.append(str(Path(__file__).parent.parent))


class QQMusicBot:
    def __init__(self):
        self.app = Client("qq_music_bot",
                          api_id=config.API_ID,
                          api_hash=config.API_HASH,
                          bot_token=config.BOT_TOKEN)

        # 注册所有命令和回调
        self._register_handlers()

    def _register_handlers(self):
        # 注册命令
        commands_dir = Path(__file__).parent / "commands"
        for file in commands_dir.glob("*.py"):
            if file.name != "__init__.py":
                module_name = f"tgbot.commands.{file.stem}"
                module = importlib.import_module(module_name)
                if hasattr(module, "register"):
                    module.register(self.app)

        # 注册回调
        callbacks_dir = Path(__file__).parent / "callbacks"
        for file in callbacks_dir.glob("*.py"):
            if file.name != "__init__.py":
                module_name = f"tgbot.callbacks.{file.stem}"
                module = importlib.import_module(module_name)
                if hasattr(module, "register"):
                    module.register(self.app)

    def run(self):
        print("QQ音乐Telegram机器人启动中...")
        self.app.run()
