from functools import wraps
from .config import config


def ensure_downloads_dir(func):
    """确保下载目录存在的装饰器"""

    @wraps(func)
    def wrapper(*args, **kwargs):
        config.DOWNLOADS_DIR.mkdir(exist_ok=True)
        return func(*args, **kwargs)

    return wrapper
