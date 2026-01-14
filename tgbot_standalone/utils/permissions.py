from .config import config


def is_admin(user_id: int) -> bool:
    return int(user_id) in set(config.ADMIN_IDS)
