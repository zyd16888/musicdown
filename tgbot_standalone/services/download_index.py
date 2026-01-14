import asyncio
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

from ..utils.config import config


class DownloadIndex:
    def __init__(self):
        self._db_path = config.download_index_db_file
        self._lock = asyncio.Lock()
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        config.data_dir.mkdir(parents=True, exist_ok=True)
        return sqlite3.connect(self._db_path)

    def _init_db(self) -> None:
        conn = self._connect()
        try:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS download_index ("
                "song_mid TEXT NOT NULL, "
                "quality TEXT NOT NULL, "
                "path TEXT NOT NULL, "
                "updated_at TEXT NOT NULL, "
                "PRIMARY KEY (song_mid, quality)"
                ")"
            )
            conn.commit()
        finally:
            conn.close()

    async def get_path(self, song_mid: str, quality: str) -> Optional[Path]:
        async with self._lock:
            conn = self._connect()
            try:
                cursor = conn.execute(
                    "SELECT path FROM download_index WHERE song_mid = ? AND quality = ?",
                    (song_mid, quality),
                )
                row = cursor.fetchone()
                if not row:
                    return None

                path = Path(row[0])
                if path.exists():
                    return path

                conn.execute(
                    "DELETE FROM download_index WHERE song_mid = ? AND quality = ?",
                    (song_mid, quality),
                )
                conn.commit()
                return None
            finally:
                conn.close()

    async def set_path(self, song_mid: str, quality: str, path: Path) -> None:
        async with self._lock:
            conn = self._connect()
            try:
                conn.execute(
                    "INSERT INTO download_index(song_mid, quality, path, updated_at) "
                    "VALUES(?, ?, ?, ?) "
                    "ON CONFLICT(song_mid, quality) DO UPDATE SET path=excluded.path, updated_at=excluded.updated_at",
                    (song_mid, quality, str(path), datetime.now().isoformat()),
                )
                conn.commit()
            finally:
                conn.close()


download_index = DownloadIndex()
