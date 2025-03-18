import time
from pathlib import Path
import humanize

from utils.network import network
from utils.config import config
from utils.logger import logger


class DownloadManager:
    """下载管理器"""

    def __init__(self):
        self.log = logger.log_progress

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

                self.log("音频文件下载完成！")
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
