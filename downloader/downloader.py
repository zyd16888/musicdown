import time
from pathlib import Path

import humanize

from utils.config import config
from utils.decorator import ensure_downloads_dir
from utils.logger import logger
from utils.network import network


class DownloadManager:
    """下载管理器"""

    def __init__(self):
        self.log = logger.log_progress

    @ensure_downloads_dir
    async def download_with_progress(self, url: str, filepath: Path) -> bool:
        """带进度和速度显示的下载函数"""
        try:
            client = await network._ensure_async_client()
            async with client.stream('GET', url) as response:
                if response.status_code != 200:
                    self.log(f"下载失败: HTTP状态码 {response.status_code}")
                    return False

                total_size = int(response.headers.get('content-length', 0))
                downloaded = 0
                start_time = time.time()
                last_update_time = start_time

                with open(filepath, 'wb') as f:
                    async for chunk in response.aiter_bytes(chunk_size=config.BLOCK_SIZE):
                        downloaded += len(chunk)
                        f.write(chunk)

                        current_time = time.time()
                        if current_time - last_update_time >= config.PROGRESS_UPDATE_INTERVAL:
                            self._update_progress(
                                downloaded, total_size, start_time, current_time)
                            last_update_time = current_time

                self.log("文件下载完成！")
                return True

        except Exception as e:
            self.log(f"下载出错: {str(e)}")
            return False

    def _update_progress(self, downloaded: int, total_size: int, start_time: float, current_time: float):
        """更新下载进度"""
        duration = current_time - start_time
        if duration > 0:
            speed = downloaded / duration
            progress = (downloaded / total_size * 100) if total_size else 0
            self.log(
                f"下载进度: {progress:.1f}% | 速度: {humanize.naturalsize(speed)}/s")

    async def download_album_cover(self, album_mid: str) -> Path:
        """下载专辑封面并返回本地文件路径"""
        cover_url = f"https://y.qq.com/music/photo_new/T002R800x800M000{album_mid}.jpg?max_age=2592000"
        cover_path = config.DOWNLOADS_DIR / f"cover_{album_mid}.jpg"

        try:
            # 使用下载管理器下载封面
            await self.download_with_progress(cover_url, cover_path)
            return cover_path
        except Exception:
            return None
