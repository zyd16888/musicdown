import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List


class ConfigManager:
    _instances = {}

    @classmethod
    def get_instance(cls, config_file: Path) -> "ConfigManager":
        key = str(config_file)
        if key not in cls._instances:
            cls._instances[key] = cls(config_file)
        return cls._instances[key]

    def __init__(self, config_file: Path):
        self.config_file = Path(config_file)
        self.config = {}
        self.load_config()

    def load_config(self):
        if self.config_file.exists():
            with open(self.config_file, "r", encoding="utf-8") as f:
                self.config = json.load(f)
        else:
            self.config = {}
            self.save_config()

    def reload_config(self):
        self.load_config()
        return self.config

    def save_config(self):
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)

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
    root_dir: Path = field(default_factory=lambda: Path(__file__).resolve().parent.parent)
    config_file: ConfigManager = field(init=False)
    data_dir: Path = field(init=False)
    users_file: Path = field(init=False)
    quota_db_file: Path = field(init=False)
    download_index_db_file: Path = field(init=False)
    queue_db_file: Path = field(init=False)
    credential_file: Path = field(init=False)

    DOWNLOADS_DIR: Path = field(init=False)
    MAX_CONCURRENT: int = field(init=False)
    DOWNGRADE_RETRY: bool = field(init=False)
    DEFAULT_QUALITY: str = field(init=False)
    BLOCK_SIZE: int = 8192
    PROGRESS_UPDATE_INTERVAL: float = 0.5
    SINGLE_CONCURRENT: int = field(init=False)
    PLAYLIST_CONCURRENT: int = field(init=False)

    BOT_TOKEN: str = field(init=False)
    API_BASE_URL: str = field(init=False)
    ADMIN_IDS: List[int] = field(init=False)
    PLAYLIST_LIMIT_PER_DAY: int = field(init=False)
    SONG_LIMIT_PER_DAY: int = field(init=False)
    QR_LOGIN_TYPE: str = field(init=False)
    PLAYLIST_QUALITIES: List[str] = field(init=False)

    user_sessions = {}

    def __post_init__(self):
        self.config_file = ConfigManager.get_instance(self.root_dir / "config.json")
        self.data_dir = self.root_dir / "data"
        self.users_file = self.data_dir / "users.json"
        self.quota_db_file = self.data_dir / "quota.db"
        self.download_index_db_file = self.data_dir / "download_index.db"
        self.queue_db_file = self.data_dir / "download_queue.db"
        self.credential_file = self.root_dir / "credential.json"
        self.reload_config()

    def reload_config(self):
        self.config_file.reload_config()
        downloads_dir = self.config_file.get("downloads.dir", "downloads")
        self.DOWNLOADS_DIR = self._resolve_path(downloads_dir)
        self.MAX_CONCURRENT = int(self.config_file.get("downloads.concurrent", 3))
        self.SINGLE_CONCURRENT = int(
            self.config_file.get("downloads.concurrentSingle", self.MAX_CONCURRENT)
        )
        self.PLAYLIST_CONCURRENT = int(
            self.config_file.get("downloads.concurrentPlaylist", 1)
        )
        self.DOWNGRADE_RETRY = bool(self.config_file.get("downloads.downgradeRetry", True))
        self.DEFAULT_QUALITY = self.config_file.get("quality", "flac")

        self.BOT_TOKEN = self.config_file.get("tgbot.botToken", "")
        self.API_BASE_URL = self.config_file.get("tgbot.apiBaseUrl", "https://api.telegram.org/bot")

        self.ADMIN_IDS = [int(x) for x in (self.config_file.get("admins", []) or [])]
        self.PLAYLIST_LIMIT_PER_DAY = int(self.config_file.get("limits.playlistPerDay", 3))
        self.SONG_LIMIT_PER_DAY = int(self.config_file.get("limits.songPerDay", 10))
        self.QR_LOGIN_TYPE = str(self.config_file.get("login.qrType", "QQ"))
        self.PLAYLIST_QUALITIES = self._normalize_qualities(
            self.config_file.get("playlistQualities", [self.DEFAULT_QUALITY])
        )

    def _resolve_path(self, value: str) -> Path:
        path = Path(value)
        if not path.is_absolute():
            path = self.root_dir / path
        return path

    def set_limits(self, playlist_limit: int, song_limit: int):
        self.config_file.set("limits.playlistPerDay", int(playlist_limit))
        self.config_file.set("limits.songPerDay", int(song_limit))
        self.reload_config()

    def set_quality(self, quality: str):
        self.config_file.set("quality", quality)
        self.reload_config()

    def set_download_dir(self, download_dir: str):
        self.config_file.set("downloads.dir", download_dir)
        self.reload_config()

    def set_playlist_qualities(self, qualities: List[str]):
        self.config_file.set("playlistQualities", qualities)
        self.reload_config()

    @staticmethod
    def _normalize_qualities(value) -> List[str]:
        if isinstance(value, str):
            items = [value]
        elif isinstance(value, list):
            items = value
        else:
            items = []
        cleaned = [str(item).strip() for item in items if str(item).strip()]
        return cleaned or ["flac"]


config = Config()
