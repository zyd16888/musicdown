import httpx
import time
import random
from typing import Dict, List, Optional
from base64 import encode
from utils.enum import RequestMethod, SearchType
from utils.parser import MusicDataParser
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

class QQMusicAPI:
    """QQ音乐API封装类（异步版本）"""

    def __init__(self,  user_agent: str = None):
        """初始化API类

        Args:
            user_agent (str): 自定义User-Agent，可选
        """
        self.base_url = "https://u.y.qq.com/cgi-bin/musicu.fcg"
        self.lyric_url = "https://c.y.qq.com/lyric/fcgi-bin/fcg_query_lyric_new.fcg"

        self.file_config = {
            'm4a': {'s': 'C400', 'e': '.m4a', 'bitrate': 'M4A'},
            '128': {'s': 'M500', 'e': '.mp3', 'bitrate': '128kbps'},
            '320': {'s': 'M800', 'e': '.mp3', 'bitrate': '320kbps'},
            'flac': {'s': 'F000', 'e': '.flac', 'bitrate': 'FLAC'},
        }

        self.uin = str(random.randint(1000000000, 9999999999))
        self.default_headers = {
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Content-Type": "application/json",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "User-Agent": user_agent or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
        }
        self.mobile_headers = {
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Content-Type": "application/json",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "User-Agent": user_agent or "Mozilla/5.0 (iPhone; CPU iPhone OS 13_3_1 like Mac OS X; zh-CN) AppleWebKit/537.51.1 (KHTML, like Gecko) Mobile/17D50 UCBrowser/12.8.2.1268 Mobile AliApp(TUnionSDK/0.1.20.3)"
        }

        self.client = httpx.AsyncClient(
            limits=httpx.Limits(max_connections=100,
                                max_keepalive_connections=20),
            timeout=httpx.Timeout(10)
        )
        self.parser = MusicDataParser()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10), retry=retry_if_exception_type((httpx.RequestError, httpx.HTTPStatusError)))
    async def _make_request(self, url: str, method: str, payload: Dict = None, params: Dict = None, headers: Dict = None) -> Dict:
        """通用异步请求方法

        Args:
            url (str): 请求URL
            method (str): 请求方法 (POST/GET)
            payload (Dict): 请求体数据
            params (Dict): 查询参数
            headers (Dict): 自定义头部

        Returns:
            Dict: 响应JSON数据
        """
        try:
            custom_headers = {**self.default_headers, **(headers or {})}

            response = await self.client.request(
                method,
                url,
                json=payload if method == RequestMethod.POST else None,
                params=params if method == RequestMethod.GET else None,
                headers=custom_headers
            )
            response.raise_for_status()
            return response.json()
        except httpx.RequestError as e:
            raise Exception(f"请求失败: {str(e)}")

    async def search(self, query: str, search_type: SearchType = SearchType.SONG, page: int = 1, limit: int = 10) -> Dict:
        """异步搜索音乐

        Args:
            query (str): 搜索关键词
            search_type (SearchType): 搜索类型枚举，默认单曲
            page (int): 页码
            limit (int): 每页数量

        Returns:
            Dict: 解析后的搜索结果
        """
        payload = {
            "comm": {"uin": self.uin, "format": "json", "ct": 23, "cv": 0},
            "req_0": {
                "method": "DoSearchForQQMusicDesktop",
                "module": "music.search.SearchCgiService",
                "param": {
                    "remoteplace": "txt.mqq.all",
                    "num_per_page": limit,
                    "page_num": page,
                    "query": query,
                    "search_type": search_type
                }
            }
        }
        response = await self._make_request(self.base_url, RequestMethod.POST, payload)
        return self.parser.parse_search_result(response, search_type)

    async def get_album_songs(self, album_mid: str, begin: int = 0, num: int = -1) -> Dict:
        """异步获取专辑歌曲列表

        Args:
            album_mid (str): 专辑MID
            begin (int): 开始位置
            num (int): 获取数量 (-1表示全部)

        Returns:
            Dict: 解析后的专辑歌曲列表
        """
        payload = {
            "comm": {"uin": self.uin, "format": "json", "ct": 24, "cv": 4747474},
            "req_0": {
                "module": "music.musichallAlbum.AlbumSongList",
                "method": "GetAlbumSongList",
                "param": {"albumMid": album_mid, "begin": begin, "num": num, "order": 2}
            }
        }
        response = await self._make_request(self.base_url, RequestMethod.POST, payload)
        return self.parser.parse_album(response)

    async def get_playlist(self, disstid: int, song_begin: int = 0, song_num: int = -1) -> Dict:
        """异步获取歌单列表

        Args:
            disstid (str): 歌单ID
            song_begin (int): 开始位置
            song_num (int): 获取数量 (-1表示全部)

        Returns:
            Dict: 解析后的歌单信息
        """
        payload = {
            "comm": {"uin": self.uin, "format": "json"},
            "req_0": {
                "module": "music.srfDissInfo.aiDissInfo",
                "method": "uniform_get_Dissinfo",
                "param": {
                    "disstid": disstid, "song_begin": song_begin, "song_num": song_num, "tag": 1, "userinfo": 1}
            }
        }
        response = await self._make_request(self.base_url, RequestMethod.POST, payload)
        return self.parser.parse_playlist(response)

    async def get_word_by_word_lyrics(self, songmid: str = None, songID: int = None, album_name: str = None, singer_name: str = None, song_name: str = None) -> Dict:
        """异步获取逐字歌词（加密）

        Args:
            songmid (str): 歌曲MID
            songID (int): 歌曲ID
            album_name (str): 专辑名
            singer_name (str): 歌手名
            song_name (str): 歌名

        Returns:
            Dict: 解析后的歌词数据
        """
        if not songmid and not songID:
            raise ValueError("必须提供 songmid 或 songID 其中之一")
        # 建基础参数
        param = {
            "crypt": 1,
            "ct": 19,
            "cv": 1942,
            "qrc": 1,
            "roma": 1,
            "trans": 1
        }

        # 添加歌曲标识参数
        if songID:
            param["songID"] = songID
        else:
            param["songmid"] = songmid

        # 添加可选参数
        if album_name:
            param["albumName"] = encode(album_name)
        if singer_name:
            param["singerName"] = encode(singer_name)
        if song_name:
            param["songName"] = encode(song_name)

        payload = {
            "comm": {"uin": self.uin},
            "music.musichallSong.PlayLyricInfo.GetPlayLyricInfo": {
                "method": "GetPlayLyricInfo",
                "module": "music.musichallSong.PlayLyricInfo",
                "param": param
            }
        }
        response = await self._make_request(self.base_url, RequestMethod.POST, payload)
        return self.parser.parse_word_by_word_lyrics(response)

    async def get_lyrics(self, songmid: str) -> Dict:
        """异步获取普通歌词（未加密）

        Args:
            songmid (str): 歌曲MID

        Returns:
            Dict: 解析后的歌词数据
        """
        params = {
            "_": time.time(),
            "format": "json",
            "songmid": songmid,
            "loginUin": self.uin
        }
        headers = {"Referer": "https://y.qq.com/"}
        response = await self._make_request(self.lyric_url, RequestMethod.GET, params=params, headers=headers)
        return self.parser.parse_lyrics(response)

    async def get_song_url(self, songmid: str, filetype: str = '128', cookie: str = None) -> Dict:
        """异步获取歌曲URL

        Args:
            songmid (str): 歌曲MID
            filename (str): 文件名
            filetype (str): 文件类型 ('m4a'/'128'/'320'/'flac')
            cookie (str): Cookie

        Returns:
            Dict: 歌曲URL信息
        """
        file_info = self.file_config[filetype]
        file = f"{file_info['s']}{songmid}{songmid}{file_info['e']}"
        payload = {
            "req_1": {
                "module": "vkey.GetVkeyServer",
                "method": "CgiGetVkey",
                "param": {
                    "filename": [file],
                    "guid": "10000",
                    "songmid": [songmid],
                    "songtype": [0],
                    "uin": self.uin,
                    "loginflag": 1,
                    "platform": "20"
                }
            },
            "loginUin": self.uin,
            "comm": {"uin": self.uin, "format": "json", "ct": 24, "cv": 0}
        }
        headers = {"Cookie": cookie} if cookie else {}
        response = await self._make_request(self.base_url, "POST", payload, headers=headers)
        return self.parser.parse_song_url(response)

    async def get_singer_albums(self, singermid: str) -> Dict:
        """获取歌手的专辑信息

        Args:
            singermid (str): 歌手MID

        Returns:
            Dict: 歌手专辑信息
        """
        payload = {
            "req_0": {
                "module": "music.homepage.HomepageSrv",
                "method": "GetHomepageTabDetail",
                "param": {
                    "uin": self.uin,
                    "singerMid": singermid,
                    "tabId": "album",
                    "page": 1,
                    "pageSize": 10,
                    "order": 0
                }
            },
            "comm": {
                "g_tk": 1666686892,
                "uin": self.uin,
                "format": "json",
                "ct": 23
            }
        }
        return await self._make_request(self.base_url, RequestMethod.POST, payload)

    async def get_song_image_url(self, album_mid: str) -> str:
        """获取歌曲图片

        Args:
            songmid (str): 歌曲MID

        Returns:
            str: 歌曲图片url
        """
        url = f"https://y.qq.com/music/photo_new/T002R800x800M000{album_mid}.jpg?max_age=2592000"
        return url
    
    async def get_song_image_bytes(self, album_mid: str) -> bytes:

        url = f"https://y.qq.com/music/photo_new/T002R800x800M000{album_mid}.jpg?max_age=2592000"

        return self._make_request(url, RequestMethod.GET)
