from enum import IntEnum, Enum


class SearchType(IntEnum):
    """搜索类型枚举"""
    SONG = 0
    ARTIST = 1
    ALBUM = 2
    SONGLIST = 3
    MV = 4
    LYRICS = 7


class RequestMethod(str, Enum):
    """请求方法枚举"""
    GET = "GET"
    POST = "POST"

class QrcType(Enum):
    """歌词类型枚举"""
    LOCAL = 0
    CLOUD = 1