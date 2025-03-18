# config_manager.py
from dataclasses import field, dataclass
from pathlib import Path
import tomli
import tomli_w
import os

class ConfigManager:
    _instances = {}

    @classmethod
    def get_instance(cls, config_file: str) -> "ConfigManager":
        if config_file not in cls._instances:
            cls._instances[config_file] = cls(config_file)
        return cls._instances[config_file]

    def __init__(self, config_file: str):
        self.config_file = config_file
        self.config = {}
        self.load_config()

    def load_config(self):
        if os.path.exists(self.config_file):
            with open(self.config_file, "rb") as f:
                self.config = tomli.load(f)
        else:
            self.config = {}
            self.save_config()

    def save_config(self):
        with open(self.config_file, "wb") as f:
            tomli_w.dump(self.config, f)

    def get(self, key_path: str, default=None):
        keys = key_path.split(".")
        current = self.config
        for key in keys:
            try:
                current = current[key]
            except (KeyError, TypeError):
                return default
        return current

    def set(self, key_path: str, value):
        keys = key_path.split(".")
        current = self.config
        for key in keys[:-1]:
            if key not in current or not isinstance(current[key], dict):
                current[key] = {}
            current = current[key]
        current[keys[-1]] = value
        self.save_config()


@dataclass
class Config:
    config_file = ConfigManager.get_instance("config.toml")
    DOWNLOADS_DIR: Path = field(default=Path('downloads'))
    DEFAULT_QUALITY: int = 11
    BLOCK_SIZE: int = 8192
    PROGRESS_UPDATE_INTERVAL: float = 0.5
    QQMUSIC_COOKIE: str = config_file.get("qqmusic.cookie")
    API_ID: str = config_file.get("tgbot.appId")
    API_HASH: str = config_file.get("tgbot.apiHash")
    BOT_TOKEN: str = config_file.get("tgbot.botToken")
    # 用户会话状态存储
    user_sessions = {}


config = Config()


# robot_module.py
# from config import ConfigManager
# robot_config = ConfigManager.get_instance("robot_config.toml")
# shared_config = ConfigManager.get_instance("shared_config.toml")
# speed = robot_config.get("speed")
# log_level = shared_config.get("log_level")

# # desktop_module.py
# from config import ConfigManager
# desktop_config = ConfigManager.get_instance("desktop_config.toml")
# shared_config = ConfigManager.get_instance("shared_config.toml")
# theme = desktop_config.get("theme")
