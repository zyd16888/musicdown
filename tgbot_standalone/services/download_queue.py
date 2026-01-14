import asyncio
import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Awaitable, Callable, Optional

from ..utils.config import config
from ..utils.logger import logger


@dataclass
class DownloadJob:
    func: Callable[..., Awaitable[Any]]
    args: tuple
    kwargs: dict
    future: asyncio.Future
    job_id: Optional[int] = None


class DownloadQueue:
    def __init__(self, name: str, default_workers: int):
        self._queue: asyncio.Queue[Optional[DownloadJob]] = asyncio.Queue()
        self._workers: list[asyncio.Task] = []
        self._started = False
        self._default_workers = max(int(default_workers), 1)
        self._max_workers = self._default_workers
        self._name = name
        self._inflight: dict[str, asyncio.Future] = {}
        self._inflight_lock = asyncio.Lock()
        self._db_lock = asyncio.Lock()
        self._db_path = config.queue_db_file
        self._loaded = False
        self._init_db()

    async def start(self, max_workers: Optional[int] = None) -> None:
        if self._started:
            return
        if max_workers is None:
            max_workers = self._default_workers
        self._max_workers = max(int(max_workers), 1)
        self._started = True
        for index in range(self._max_workers):
            self._workers.append(asyncio.create_task(self._worker(index)))
        logger.info(f"{self._name} 下载队列已启动，worker={self._max_workers}")
        await self._load_pending_jobs()

    async def stop(self) -> None:
        if not self._started:
            return
        for _ in self._workers:
            await self._queue.put(None)
        await asyncio.gather(*self._workers, return_exceptions=True)
        self._workers.clear()
        self._started = False

    async def _ensure_started(self) -> None:
        if not self._started:
            await self.start(self._default_workers)

    async def enqueue(
        self,
        func: Callable[..., Awaitable[Any]],
        *args,
        dedupe_key: Optional[str] = None,
        persist_payload: Optional[dict] = None,
        **kwargs,
    ) -> asyncio.Future:
        await self._ensure_started()
        loop = asyncio.get_running_loop()
        future: asyncio.Future
        if dedupe_key:
            async with self._inflight_lock:
                existing = self._inflight.get(dedupe_key)
                if existing and not existing.done():
                    return existing
                future = loop.create_future()
                self._inflight[dedupe_key] = future

                def _cleanup(_):
                    self._inflight.pop(dedupe_key, None)

                future.add_done_callback(_cleanup)
        else:
            future = loop.create_future()
        job_id = None
        func_name = func.__name__
        if persist_payload is not None:
            job_id = await self._insert_job(
                func_name=func_name,
                payload=persist_payload,
                dedupe_key=dedupe_key,
            )

        await self._queue.put(
            DownloadJob(func=func, args=args, kwargs=kwargs, future=future, job_id=job_id)
        )
        return future

    async def submit(
        self,
        func: Callable[..., Awaitable[Any]],
        *args,
        dedupe_key: Optional[str] = None,
        persist_payload: Optional[dict] = None,
        **kwargs,
    ) -> Any:
        future = await self.enqueue(
            func,
            *args,
            dedupe_key=dedupe_key,
            persist_payload=persist_payload,
            **kwargs,
        )
        return await future

    async def _worker(self, index: int) -> None:
        while True:
            job = await self._queue.get()
            if job is None:
                self._queue.task_done()
                break
            try:
                if job.job_id is not None:
                    await self._mark_running(job.job_id)
                result = await job.func(*job.args, **job.kwargs)
                if not job.future.cancelled():
                    job.future.set_result(result)
                if job.job_id is not None:
                    await self._delete_job(job.job_id)
            except Exception as exc:
                if not job.future.cancelled():
                    job.future.set_exception(exc)
                if job.job_id is not None:
                    await self._delete_job(job.job_id)
            finally:
                self._queue.task_done()

    def _connect(self) -> sqlite3.Connection:
        config.data_dir.mkdir(parents=True, exist_ok=True)
        return sqlite3.connect(self._db_path)

    def _init_db(self) -> None:
        conn = self._connect()
        try:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS queue_jobs ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT, "
                "queue_name TEXT NOT NULL, "
                "func_name TEXT NOT NULL, "
                "payload TEXT NOT NULL, "
                "dedupe_key TEXT, "
                "status TEXT NOT NULL, "
                "created_at TEXT NOT NULL"
                ")"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_queue_jobs_status "
                "ON queue_jobs(queue_name, status, id)"
            )
            conn.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_queue_jobs_dedupe "
                "ON queue_jobs(queue_name, dedupe_key) WHERE dedupe_key IS NOT NULL"
            )
            conn.commit()
        finally:
            conn.close()

    async def _insert_job(self, func_name: str, payload: dict, dedupe_key: Optional[str]) -> Optional[int]:
        async with self._db_lock:
            conn = self._connect()
            try:
                payload_json = json.dumps(payload, ensure_ascii=False)
                if dedupe_key:
                    conn.execute(
                        "INSERT OR IGNORE INTO queue_jobs(queue_name, func_name, payload, dedupe_key, status, created_at) "
                        "VALUES(?, ?, ?, ?, 'pending', ?)",
                        (self._name, func_name, payload_json, dedupe_key, datetime.now().isoformat()),
                    )
                    cursor = conn.execute(
                        "SELECT id FROM queue_jobs WHERE queue_name = ? AND dedupe_key = ?",
                        (self._name, dedupe_key),
                    )
                    row = cursor.fetchone()
                    conn.commit()
                    return int(row[0]) if row else None

                cursor = conn.execute(
                    "INSERT INTO queue_jobs(queue_name, func_name, payload, dedupe_key, status, created_at) "
                    "VALUES(?, ?, ?, NULL, 'pending', ?)",
                    (self._name, func_name, payload_json, datetime.now().isoformat()),
                )
                conn.commit()
                return int(cursor.lastrowid)
            finally:
                conn.close()

    async def _mark_running(self, job_id: int) -> None:
        async with self._db_lock:
            conn = self._connect()
            try:
                conn.execute(
                    "UPDATE queue_jobs SET status = 'running' WHERE id = ?", (job_id,)
                )
                conn.commit()
            finally:
                conn.close()

    async def _delete_job(self, job_id: int) -> None:
        async with self._db_lock:
            conn = self._connect()
            try:
                conn.execute("DELETE FROM queue_jobs WHERE id = ?", (job_id,))
                conn.commit()
            finally:
                conn.close()

    async def _load_pending_jobs(self) -> None:
        if self._loaded:
            return
        self._loaded = True
        async with self._db_lock:
            conn = self._connect()
            try:
                cursor = conn.execute(
                    "SELECT id, func_name, payload, dedupe_key FROM queue_jobs "
                    "WHERE queue_name = ? AND status IN ('pending', 'running') ORDER BY id ASC",
                    (self._name,),
                )
                rows = cursor.fetchall()
            finally:
                conn.close()

        for job_id, func_name, payload_json, dedupe_key in rows:
            func = JOB_REGISTRY.get(func_name)
            if not func:
                continue
            try:
                payload = json.loads(payload_json)
            except Exception:
                continue

            payload = _normalize_payload(payload)
            future = asyncio.get_running_loop().create_future()
            if dedupe_key:
                async with self._inflight_lock:
                    self._inflight[dedupe_key] = future

                    def _cleanup(_):
                        self._inflight.pop(dedupe_key, None)

                    future.add_done_callback(_cleanup)

            await self._queue.put(
                DownloadJob(func=func, args=(), kwargs=payload, future=future, job_id=job_id)
            )


async def download_song_job(
    song_info,
    download_dir,
    filetype,
    cookie=None,
    fetch_detail: bool = False,
):
    from ..downloader.music_downloader import MusicDownloader

    downloader = MusicDownloader()
    return await downloader.download_song(
        song_info=song_info,
        download_dir=download_dir,
        filetype=filetype,
        cookie=cookie,
        fetch_detail=fetch_detail,
    )

def _normalize_payload(payload: dict) -> dict:
    if "download_dir" in payload and isinstance(payload["download_dir"], str):
        payload["download_dir"] = Path(payload["download_dir"])
    return payload


JOB_REGISTRY = {
    "download_song_job": download_song_job,
}


single_download_queue = DownloadQueue("single", config.SINGLE_CONCURRENT)
playlist_download_queue = DownloadQueue("playlist", config.PLAYLIST_CONCURRENT)
