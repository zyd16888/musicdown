from dataclasses import dataclass, field
from typing import List, Optional
import asyncio

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

            songs.append(Song(
                mid=raw_song.get('mid', ''),
                docid=raw_song.get('docid', ''),
                title=raw_song.get('title', ''),
                interval=raw_song.get('interval', 0),
                artists=artists,
                album=Album(name=album_info.get('name', ''), mid=album_info.get('mid', ''))
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
