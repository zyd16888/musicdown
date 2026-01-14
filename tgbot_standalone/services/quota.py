import asyncio
import json
import sqlite3
from datetime import datetime
from typing import Dict, Optional, Tuple

from ..utils.config import config
from ..utils.permissions import is_admin
from ..utils.logger import logger


class QuotaManager:
    def __init__(self):
        self._lock = asyncio.Lock()
        self._db_path = config.quota_db_file
        self._init_db()
        self._maybe_migrate_from_json()

    def _today_str(self) -> str:
        return datetime.now().strftime("%Y-%m-%d")

    def _connect(self) -> sqlite3.Connection:
        config.data_dir.mkdir(parents=True, exist_ok=True)
        return sqlite3.connect(self._db_path)

    def _init_db(self) -> None:
        conn = self._connect()
        try:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS quotas ("
                "user_id INTEGER PRIMARY KEY, "
                "playlist INTEGER NOT NULL, "
                "song INTEGER NOT NULL"
                ")"
            )
            conn.execute(
                "CREATE TABLE IF NOT EXISTS meta ("
                "key TEXT PRIMARY KEY, "
                "value TEXT NOT NULL"
                ")"
            )
            conn.commit()
        finally:
            conn.close()

    def _get_meta(self, conn: sqlite3.Connection, key: str) -> Optional[str]:
        cursor = conn.execute("SELECT value FROM meta WHERE key = ?", (key,))
        row = cursor.fetchone()
        return row[0] if row else None

    def _set_meta(self, conn: sqlite3.Connection, key: str, value: str) -> None:
        conn.execute(
            "INSERT INTO meta(key, value) VALUES(?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )

    def _reset_if_needed(self, conn: sqlite3.Connection) -> None:
        today = self._today_str()
        last_reset = self._get_meta(conn, "last_reset")
        if last_reset != today:
            conn.execute("DELETE FROM quotas")
            self._set_meta(conn, "last_reset", today)
            conn.commit()

    def _get_user_record(self, conn: sqlite3.Connection, user_id: int) -> Dict[str, int]:
        cursor = conn.execute(
            "SELECT playlist, song FROM quotas WHERE user_id = ?", (user_id,)
        )
        row = cursor.fetchone()
        if row:
            return {"playlist": int(row[0]), "song": int(row[1])}

        conn.execute(
            "INSERT INTO quotas(user_id, playlist, song) VALUES(?, 0, 0)",
            (user_id,),
        )
        conn.commit()
        return {"playlist": 0, "song": 0}

    def _set_user_record(self, conn: sqlite3.Connection, user_id: int, playlist: int, song: int) -> None:
        conn.execute(
            "INSERT INTO quotas(user_id, playlist, song) VALUES(?, ?, ?) "
            "ON CONFLICT(user_id) DO UPDATE SET playlist=excluded.playlist, song=excluded.song",
            (user_id, playlist, song),
        )
        conn.commit()

    def _limit_for(self, quota_type: str) -> int:
        if quota_type == "playlist":
            return config.PLAYLIST_LIMIT_PER_DAY
        if quota_type == "song":
            return config.SONG_LIMIT_PER_DAY
        return 0

    def _maybe_migrate_from_json(self) -> None:
        if not config.users_file.exists():
            return

        conn = self._connect()
        try:
            existing_meta = self._get_meta(conn, "last_reset")
            cursor = conn.execute("SELECT COUNT(1) FROM quotas")
            row = cursor.fetchone()
            if existing_meta or (row and row[0] > 0):
                return

            try:
                with open(config.users_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception as exc:
                logger.warning(f"额度数据迁移失败: {exc}")
                return

            if not isinstance(data, dict):
                return

            users = data.get("users", {})
            for user_id, record in users.items():
                try:
                    user_id_int = int(user_id)
                except Exception:
                    continue
                playlist = int(record.get("playlist", 0)) if isinstance(record, dict) else 0
                song = int(record.get("song", 0)) if isinstance(record, dict) else 0
                conn.execute(
                    "INSERT INTO quotas(user_id, playlist, song) VALUES(?, ?, ?) "
                    "ON CONFLICT(user_id) DO UPDATE SET playlist=excluded.playlist, song=excluded.song",
                    (user_id_int, playlist, song),
                )

            last_reset = data.get("last_reset") or self._today_str()
            self._set_meta(conn, "last_reset", str(last_reset))
            conn.commit()
        finally:
            conn.close()

    async def consume(self, user_id: int, quota_type: str, amount: int = 1) -> Tuple[bool, int, int]:
        if is_admin(user_id):
            return True, -1, -1

        async with self._lock:
            conn = self._connect()
            try:
                self._reset_if_needed(conn)
                record = self._get_user_record(conn, user_id)

                limit = self._limit_for(quota_type)
                used = int(record.get(quota_type, 0))
                if used + amount > limit:
                    return False, used, limit

                if quota_type == "playlist":
                    playlist = used + amount
                    song = record.get("song", 0)
                else:
                    playlist = record.get("playlist", 0)
                    song = used + amount

                self._set_user_record(conn, user_id, int(playlist), int(song))
                return True, int(record.get(quota_type, 0)) + amount, limit
            finally:
                conn.close()

    async def get_remaining(self, user_id: int) -> Dict[str, int]:
        if is_admin(user_id):
            return {"playlist": -1, "song": -1}

        async with self._lock:
            conn = self._connect()
            try:
                self._reset_if_needed(conn)
                record = self._get_user_record(conn, user_id)
            finally:
                conn.close()

        playlist_remaining = max(0, config.PLAYLIST_LIMIT_PER_DAY - int(record.get("playlist", 0)))
        song_remaining = max(0, config.SONG_LIMIT_PER_DAY - int(record.get("song", 0)))
        return {"playlist": playlist_remaining, "song": song_remaining}


quota_manager = QuotaManager()
