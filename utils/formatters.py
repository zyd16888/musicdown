from typing import Dict, List


def format_singers(singers: List[Dict]) -> str:
    """格式化歌手列表为字符串"""
    return ", ".join([singer['name'] for singer in singers])


def format_interval(interval: int) -> str:
    minutes = interval // 60  # 计算分钟
    seconds = interval % 60   # 计算剩余秒数
    duration = f"{minutes}:{seconds:02d}"  # 格式化成 mm:ss
    return duration
