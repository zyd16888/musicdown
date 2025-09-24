import asyncio
import os
import re
from pathlib import Path
from typing import Optional

import aiohttp
from mutagen import File
from mutagen.asf import ASF
from mutagen.flac import FLAC, Picture
from mutagen.id3 import APIC, USLT
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4, MP4Cover
from mutagen.oggopus import OggOpus
from mutagen.oggvorbis import OggVorbis

from api.adapter import MusicAdapter, Song


class DownloadManager:
    """Manages the download and processing of a single song."""

    def __init__(self, song: Song, quality: str, download_dir: Path, adapter: MusicAdapter):
        self.song = song
        self.quality = quality
        self.download_dir = download_dir
        self.adapter = adapter

        self.temp_song_path: Optional[Path] = None
        self.temp_cover_path: Optional[Path] = None

    async def run(self) -> Optional[Path]:
        """Execute the full download and processing pipeline."""
        try:
            # 1. Get URL
            song_url = await self.adapter.get_song_url(self.song, self.quality)
            if not song_url:
                raise ValueError(f"无法获取 {self.song.title} 的下载链接，可能是VIP或地区限制")

            # 2. Download song file
            file_extension = self._get_file_extension(song_url)
            self.temp_song_path = self.download_dir / f"{self.song.mid}_temp{file_extension}"
            await self._download_file(song_url, self.temp_song_path)

            # 3. Download cover
            if self.song.album and self.song.album.mid:
                cover_url = f"https://y.qq.com/music/photo_new/T002R800x800M000{self.song.album.mid}.jpg"
                self.temp_cover_path = self.download_dir / f"{self.song.album.mid}_cover.jpg"
                await self._download_file(cover_url, self.temp_cover_path)

            # 4. Get lyrics
            lyrics, translated_lyrics = await self.adapter.get_lyrics(self.song)

            # 5. Embed metadata
            final_path = self._process_metadata(lyrics, translated_lyrics)
            return final_path

        finally:
            # 6. Cleanup
            self._cleanup_temp_files()

    async def _download_file(self, url: str, path: Path):
        """Downloads a file from a URL to a given path."""
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                response.raise_for_status()
                with open(path, 'wb') as f:
                    while True:
                        chunk = await response.content.read(8192)
                        if not chunk:
                            break
                        f.write(chunk)

    def _process_metadata(self, lyrics: str, translated_lyrics: str) -> Path:
        """Embeds cover, lyrics, and other metadata into the audio file."""
        audio = File(self.temp_song_path)
        if not audio:
            raise TypeError(f"不支持的音频格式: {self.temp_song_path.suffix}")

        # Add basic tags
        audio["title"] = self.song.title
        audio["artist"] = self.song.artist_names
        if self.song.album:
            audio["album"] = self.song.album.name

        # Embed lyrics
        if lyrics:
            if isinstance(audio.tags, USLT):
                 audio.tags.add(USLT(encoding=3, lang='chi', desc='Lyrics', text=lyrics))
            else:
                audio["lyrics"] = lyrics

        # Embed cover
        if self.temp_cover_path and self.temp_cover_path.exists():
            with open(self.temp_cover_path, 'rb') as f:
                cover_data = f.read()
            if isinstance(audio, MP4):
                audio["covr"] = [MP4Cover(cover_data, imageformat=MP4Cover.FORMAT_JPEG)]
            elif isinstance(audio, MP3):
                audio.tags.add(APIC(encoding=3, mime='image/jpeg', type=3, desc='Cover', data=cover_data))
            elif isinstance(audio, FLAC):
                pic = Picture()
                pic.type = 3
                pic.mime = 'image/jpeg'
                pic.desc = 'Cover'
                pic.data = cover_data
                audio.add_picture(pic)

        audio.save()

        # Rename file
        safe_title = self._sanitize_filename(self.song.title)
        safe_artist = self._sanitize_filename(self.song.artist_names)
        final_filename = f"{safe_title} - {safe_artist}{self.temp_song_path.suffix}"
        final_filepath = self.download_dir / final_filename

        # Handle existing files
        counter = 1
        while final_filepath.exists():
            final_filename = f"{safe_title} - {safe_artist} ({counter}){self.temp_song_path.suffix}"
            final_filepath = self.download_dir / final_filename
            counter += 1

        os.rename(self.temp_song_path, final_filepath)
        self.temp_song_path = None # Prevent cleanup from deleting the final file
        return final_filepath

    def _cleanup_temp_files(self):
        """Deletes temporary song and cover files."""
        if self.temp_song_path and self.temp_song_path.exists():
            os.remove(self.temp_song_path)
        if self.temp_cover_path and self.temp_cover_path.exists():
            os.remove(self.temp_cover_path)

    def _get_file_extension(self, url: str) -> str:
        match = re.search(r'\.(\w+)(\?|$)', url)
        if match:
            return f".{match.group(1)}"
        # Fallback based on quality
        if self.quality == "FLAC": return ".flac"
        if self.quality == "M4A": return ".m4a"
        return ".mp3"

    def _sanitize_filename(self, filename: str) -> str:
        return re.sub(r'[\\/:*?"<>|]', '_', filename)
