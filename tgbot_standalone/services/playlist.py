import re
from typing import Dict, List, Optional, Tuple
from urllib.parse import parse_qs, urlparse

from ..api.qqmusic import QQMusicAPI
import asyncio

from ..services.download_queue import playlist_download_queue, download_song_job
from ..utils.config import config
from ..utils.network import network
from ..utils.logger import logger


async def resolve_playlist_id(value: str) -> Optional[int]:
    value = (value or "").strip()
    if not value:
        return None
    if value.isdigit():
        return int(value)

    final_url = value
    try:
        client = await network._ensure_async_client()
        resp = await client.get(value, follow_redirects=True)
        final_url = str(resp.url)
    except Exception:
        final_url = value

    try:
        parsed = urlparse(final_url)
        qs = parse_qs(parsed.query)
        if "id" in qs and qs["id"]:
            candidate = qs["id"][0]
            return int(candidate) if candidate.isdigit() else None

        match = re.search(r"/(?:n/ryqq/)?playlist/(\d+)", parsed.path)
        if match:
            return int(match.group(1))
    except Exception:
        return None

    return None


def _normalize_song_item(item: Dict) -> Optional[Dict]:
    if not isinstance(item, dict):
        return None
    if "songInfo" in item and isinstance(item["songInfo"], dict):
        return item["songInfo"]
    return item


async def fetch_playlist_songs(playlist_id: int) -> List[Dict]:
    qq_api = QQMusicAPI()
    result = await qq_api.playlist_detail(playlist_id)
    songs = result.get("songs") or result.get("songList") or []
    song_items = []
    for item in songs:
        song_info = _normalize_song_item(item)
        if song_info:
            song_items.append(song_info)
    return song_items


async def download_playlist_songs(
    playlist_id: int,
    songs: Optional[List[Dict]] = None,
    progress_cb=None,
) -> Tuple[int, int, int]:
    if songs is None:
        songs = await fetch_playlist_songs(playlist_id)
    qualities = config.PLAYLIST_QUALITIES or [config.DEFAULT_QUALITY]
    total = len(songs) * len(qualities)
    if total == 0:
        return 0, 0, 0

    success = 0
    failed = 0
    completed = 0
    pending = set()
    future_meta = {}
    max_pending = max(config.PLAYLIST_CONCURRENT * 2, 1)

    for quality in qualities:
        download_dir = config.DOWNLOADS_DIR / quality
        download_dir.mkdir(parents=True, exist_ok=True)
        for song_info in songs:
            dedupe_key = None
            if song_info.get("mid"):
                dedupe_key = f"{song_info['mid']}:{quality}"

            persist_payload = {
                "song_info": song_info,
                "download_dir": str(download_dir),
                "filetype": quality,
                "cookie": None,
                "fetch_detail": True,
            }

            future = await playlist_download_queue.enqueue(
                download_song_job,
                song_info,
                download_dir,
                quality,
                None,
                True,
                dedupe_key=dedupe_key,
                persist_payload=persist_payload,
            )
            pending.add(future)
            future_meta[future] = quality

            if len(pending) >= max_pending:
                done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
                for finished in done:
                    quality_done = future_meta.pop(finished, "")
                    try:
                        result = finished.result()
                        if result:
                            success += 1
                        else:
                            failed += 1
                    except Exception as exc:
                        logger.warning(f"下载歌单歌曲失败: {exc}")
                        failed += 1
                    completed += 1
                    if callable(progress_cb):
                        try:
                            progress_cb(completed, total, success, failed, quality_done)
                        except Exception:
                            pass

    while pending:
        done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
        for finished in done:
            quality_done = future_meta.pop(finished, "")
            try:
                result = finished.result()
                if result:
                    success += 1
                else:
                    failed += 1
            except Exception as exc:
                logger.warning(f"下载歌单歌曲失败: {exc}")
                failed += 1
            completed += 1
            if callable(progress_cb):
                try:
                    progress_cb(completed, total, success, failed, quality_done)
                except Exception:
                    pass

    return total, success, failed
