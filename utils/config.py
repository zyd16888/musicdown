# config_manager.py
import os
import json
from dataclasses import field, dataclass
from pathlib import Path

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
            with open(self.config_file, "r", encoding='utf-8') as f:
                self.config = json.load(f)
        else:
            self.config = {}
            self.save_config()

    def save_config(self):
        with open(self.config_file, "w", encoding='utf-8') as f:
            json.dump(self.config, f, indent=4, ensure_ascii=False)

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
    config_file = ConfigManager.get_instance("config.json")
    DOWNLOADS_DIR: Path = field(default=Path('downloads'))
    DEFAULT_QUALITY: int = 11
    BLOCK_SIZE: int = 8192
    PROGRESS_UPDATE_INTERVAL: float = 0.5
    QQMUSIC_COOKIE: str = field(init=False)
    API_ID: str = field(init=False)
    API_HASH: str = field(init=False)
    BOT_TOKEN: str = field(init=False)
    # 用户会话状态存储
    user_sessions = {}

    def __post_init__(self):
        self.QQMUSIC_COOKIE = self.config_file.get("qqmusic.cookie", "")
        self.API_ID = self.config_file.get("tgbot.appId", "")
        self.API_HASH = self.config_file.get("tgbot.apiHash", "")
        self.BOT_TOKEN = self.config_file.get("tgbot.botToken", "")


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
