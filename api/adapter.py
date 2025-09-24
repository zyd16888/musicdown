from dataclasses import dataclass, field
from typing import List, Optional, Dict
import asyncio
import re
from urllib.parse import urlparse, parse_qs

# ======================================================================================
#  Data Models
# ======================================================================================

@dataclass
class Artist:
    """A standardized representation of an artist."""
    name: str
    mid: str


@dataclass
class Album:
    """A standardized representation of an album."""
    name: str
    mid: str


@dataclass
class Song:
    """A cleaned and standardized representation of a song."""
    mid: str
    docid: str
    title: str
    interval: int
    artists: List[Artist] = field(default_factory=list)
    album: Optional[Album] = None
    # 可用音质（canonical codes: MASTER/ATMOS_51/ATMOS_2/FLAC/MP3_320/MP3_128/ACC_192/ACC_96/ACC_48/ACC_24）
    # 来自 qqmusic_api 搜索结果 file 字段，按高->低去重排序
    available_qualities: List[str] = field(default_factory=list)

    @property
    def duration(self) -> str:
        """Formatted duration string MM:SS."""
        minutes, seconds = divmod(self.interval, 60)
        return f"{minutes:02d}:{seconds:02d}"

    @property
    def artist_names(self) -> str:
        """Comma-separated string of artist names."""
        return ", ".join(artist.name for artist in self.artists)

@dataclass
class AlbumSearchResult:
    """A standardized representation of an album search result."""
    mid: str
    name: str
    artists: List[Artist] = field(default_factory=list)
    publish_date: str = ""

    @property
    def artist_names(self) -> str:
        return ", ".join(artist.name for artist in self.artists)

@dataclass
class PlaylistSearchResult:
    """A standardized representation of a playlist search result."""
    id: int
    name: str
    creator_name: str = ""
    song_count: int = 0

    # ======================================================================================
    #  Library Imports
    # ======================================================================================

from qqmusic_api import search, album as api_album, songlist as api_songlist
from utils.network import network

# except ImportError:
#     from enum import Enum
#     class SearchType(Enum):
#         SONG = 0
#         ALBUM = 2
#         SONGLIST = 3

#     class DummySearch:
#         SearchType = SearchType
#         async def search_by_type(*args, **kwargs):
#             print("Warning: qqmusic-api-python not installed. Returning empty search results.")
#             return []
#     search = DummySearch()
#     class api_album:
#         async def get_song(*args, **kwargs):
#             return []
#     class api_songlist:
#         async def get_songlist(*args, **kwargs):
#             return []

# ======================================================================================
#  Adapter Class
# ======================================================================================

class MusicAdapter:
    """
    An adapter for the qqmusic-api-python library that returns clean,
    standardized data models instead of raw library objects.
    """

    def _parse_song_list(self, raw_song_dicts: List[dict]) -> List[Song]:
        """Helper method to parse a list of raw song dicts into Song objects."""
        songs = []
        if not isinstance(raw_song_dicts, list):
            return []

        for raw_song in raw_song_dicts:
            if not isinstance(raw_song, dict):
                continue

            album_info = raw_song.get('album', {})
            if not isinstance(album_info, dict):
                album_info = {}

            singer_info = raw_song.get('singer', [])
            if not isinstance(singer_info, list):
                singer_info = []

            artists = [
                Artist(name=a.get('name', ''), mid=a.get('mid', ''))
                for a in singer_info if isinstance(a, dict)
            ]

            # 解析文件字段中的各音质大小，推断可用音质
            file_info = raw_song.get('file', {})
            if not isinstance(file_info, dict):
                file_info = {}
            qualities: List[str] = []
            # 新字段 size_new 按索引表示部分档位（参见 qqmusic_api.song.SongFileType 注释）
            size_new = file_info.get('size_new')
            if isinstance(size_new, (list, tuple)):
                try:
                    if int(size_new[0]) > 0:
                        qualities.append('MASTER')
                except Exception:
                    pass
                try:
                    if int(size_new[1]) > 0:
                        qualities.append('ATMOS_2')
                except Exception:
                    pass
                try:
                    if int(size_new[2]) > 0:
                        qualities.append('ATMOS_51')
                except Exception:
                    pass
                try:
                    if int(size_new[3]) > 0:
                        qualities.append('OGG_320')
                except Exception:
                    pass
                try:
                    if len(size_new) > 5 and int(size_new[5]) > 0:
                        qualities.append('OGG_640')
                except Exception:
                    pass
            # 兼容旧字段（部分接口仍返回）
            try:
                if int(file_info.get('size_hires', 0)) > 0 and 'MASTER' not in qualities:
                    qualities.append('MASTER')
            except Exception:
                pass
            try:
                if int(file_info.get('size_dolby', 0)) > 0 and 'ATMOS_2' not in qualities:
                    qualities.append('ATMOS_2')
            except Exception:
                pass
            try:
                if int(file_info.get('size_flac', 0)) > 0:
                    qualities.append('FLAC')
            except Exception:
                pass
            try:
                if int(file_info.get('size_320mp3', 0)) > 0:
                    qualities.append('MP3_320')
            except Exception:
                pass
            try:
                if int(file_info.get('size_128mp3', 0)) > 0:
                    qualities.append('MP3_128')
            except Exception:
                pass
            # OGG 其他档位
            for k, code in (
                ('size_192ogg', 'OGG_192'),
                ('size_96ogg', 'OGG_96'),
            ):
                try:
                    if int(file_info.get(k, 0)) > 0:
                        qualities.append(code)
                except Exception:
                    pass

            # 按可用 AAC 档位细分（m4a 容器）
            for k, code in (
                ('size_192aac', 'ACC_192'),
                ('size_96aac', 'ACC_96'),
                ('size_48aac', 'ACC_48'),
                # ('size_24aac', 'ACC_24'),  # 当前 SongFileType 未包含 ACC_24
            ):
                try:
                    if int(file_info.get(k, 0)) > 0:
                        qualities.append(code)
                except Exception:
                    pass
            # 去重保持顺序
            seen = set()
            qualities_unique: List[str] = []
            for q in qualities:
                if q not in seen:
                    seen.add(q)
                    qualities_unique.append(q)

            songs.append(Song(
                mid=raw_song.get('mid', ''),
                docid=raw_song.get('docid', ''),
                title=raw_song.get('title', ''),
                interval=raw_song.get('interval', 0),
                artists=artists,
                album=Album(name=album_info.get('name', ''), mid=album_info.get('mid', '')),
                available_qualities=qualities_unique,
            ))
        return songs

    async def search_song(
        self, keyword: str, page: int = 1, limit: int = 20
    ) -> List[Song]:
        raw_song_dicts: List[dict] = await search.search_by_type(
            keyword=keyword, search_type=search.SearchType.SONG, page=page, num=limit
        )
        return self._parse_song_list(raw_song_dicts)

    async def search_album(self, keyword: str, page: int = 1, limit: int = 20) -> List[AlbumSearchResult]:
        raw_album_dicts: List[dict] = await search.search_by_type(
            keyword=keyword, search_type=search.SearchType.ALBUM, page=page, num=limit
        )
        albums = []
        for raw_album in raw_album_dicts:
            if not isinstance(raw_album, dict):
                continue

            # Prioritize 'singer_list' for more reliable data
            singer_info = raw_album.get("singer_list", [])
            if not isinstance(singer_info, list):
                singer_info = []

            artists = [
                Artist(name=a.get('name', ''), mid=a.get('mid', ''))
                for a in singer_info if isinstance(a, dict)
            ]

            albums.append(
                AlbumSearchResult(
                    mid=raw_album.get(
                        "albummid", ""
                    ),  # FIX: Use the correct key 'albummid'
                    name=raw_album.get("name", ""),
                    publish_date=raw_album.get("publish_date", ""),
                    artists=artists,
                )
            )
        return albums

    async def search_playlist(self, keyword: str, page: int = 1, limit: int = 20) -> List[PlaylistSearchResult]:
        raw_playlist_dicts: List[dict] = await search.search_by_type(
            keyword=keyword, search_type=search.SearchType.SONGLIST, page=page, num=limit
        )
        playlists = []
        for raw_playlist in raw_playlist_dicts:
            if not isinstance(raw_playlist, dict):
                continue

            dissid_str = raw_playlist.get('dissid', '0')

            playlists.append(PlaylistSearchResult(
                id=int(dissid_str) if dissid_str.isdigit() else 0,
                name=raw_playlist.get('dissname', ''),
                song_count=raw_playlist.get('songnum', 0),
                creator_name=raw_playlist.get('nickname', '')
            ))
        return playlists

    async def get_album_songs(self, album_mid: str) -> List[Song]:
        """Gets all songs from an album and returns a list of clean Song objects."""
        raw_songs: List[dict] = await api_album.get_song(album_mid, page=1, num=200)
        return self._parse_song_list(raw_songs)

    async def get_playlist_songs(self, playlist_id: int) -> List[Song]:
        """Gets all songs from a playlist and returns a list of clean Song objects."""
        raw_songs: List[dict] = await api_songlist.get_songlist(playlist_id)
        return self._parse_song_list(raw_songs)

    # ============================
    #  Share Link Utilities
    # ============================
    async def resolve_playlist_id_from_share(self, url: str) -> Optional[int]:
        """Resolve QQ Music playlist disstid from a share URL.

        Supports:
        - https://c*.y.qq.com/base/fcgi-bin/u?__=... (short link → 302)
        - https://y.qq.com/n/ryqq/playlist/<id>
        - https://y.qq.com/playlist.html?id=<id>
        Returns: int disstid or None
        """
        final_url = url
        try:
            client = await network._ensure_async_client()
            resp = await client.get(url, follow_redirects=True)
            final_url = str(resp.url)
        except Exception:
            # fallback: keep original url
            pass

        try:
            pr = urlparse(final_url)
            qs = parse_qs(pr.query)
            # query id
            if 'id' in qs and qs['id']:
                v = qs['id'][0]
                return int(v) if v.isdigit() else None
            # path pattern /playlist/<digits> or /n/ryqq/playlist/<digits>
            m = re.search(r"/(?:n/ryqq/)?playlist/(\d+)", pr.path)
            if m:
                return int(m.group(1))
        except Exception:
            return None
        return None

    async def get_playlist_songs_by_share_link(self, share_url: str) -> List[Song]:
        """High-level helper: resolve share URL then fetch all songs as Song list."""
        disstid = await self.resolve_playlist_id_from_share(share_url)
        if not disstid:
            return []
        return await self.get_playlist_songs(disstid)
