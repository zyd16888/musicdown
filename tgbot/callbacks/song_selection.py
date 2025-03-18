import os
import sys
from pathlib import Path

from pyrogram import Client, filters
from pyrogram.types import CallbackQuery

from api.qm import QQMusicAPI
from downloader.downloader import DownloadManager
from utils.config import config
from utils.formatters import format_singers, get_file_path

# 确保可以导入项目根目录的模块
sys.path.append(str(Path(__file__).parent.parent.parent))

# 初始化QQ音乐API和下载管理器
qq_music_api = QQMusicAPI()
download_manager = DownloadManager()


def register(app: Client):
    @app.on_callback_query(filters.regex(r"^song:(\d+)$"))
    async def handle_song_selection(client, callback_query: CallbackQuery):
        user_id = callback_query.from_user.id
        song_index = int(callback_query.data.split(":")[1])

        if user_id not in config.user_sessions or "search_results" not in config.user_sessions[user_id]:
            await callback_query.answer("会话已过期，请重新搜索")
            return

        songs = config.user_sessions[user_id]["search_results"]
        if song_index >= len(songs):
            await callback_query.answer("无效的选择，请重新搜索")
            return

        selected_song = songs[song_index]

        # 显示下载中消息
        await callback_query.edit_message_text(
            f"⏳ 正在下载歌曲: {selected_song['name']} - {format_singers(selected_song['singer'])}..."
        )

        try:
            # 获取歌曲下载链接
            song_url_result = await qq_music_api.get_song_url(selected_song['mid'], filetype='m4a')

            if song_url_result['code'] == -1 or not song_url_result.get('url'):
                await callback_query.edit_message_text("❌ 无法获取歌曲下载链接，可能是版权限制。")
                return

            # 准备下载
            song_url = song_url_result['url']
            filepath = await get_file_path(selected_song, song_url)

            # 下载歌曲
            download_success = await download_manager.download_with_progress(song_url, filepath)

            if not download_success:
                await callback_query.edit_message_text("❌ 下载歌曲失败，请稍后重试。")
                return

            # 获取专辑封面
            album_mid = selected_song['album']['mid']
            cover_path = None
            try:
                cover_path = await download_manager.download_album_cover(album_mid)
            except:
                pass  # 如果封面下载失败，继续而不使用封面

            # 发送歌曲文件
            await callback_query.message.reply_audio(
                audio=str(filepath),
                title=selected_song['name'],
                performer=format_singers(selected_song['singer']),
                duration=selected_song.get('interval', 0),
                thumb=str(cover_path) if cover_path else None,
                caption=f"🎵 {selected_song['name']}\n👤 {format_singers(selected_song['singer'])}\n💿 {selected_song['album']['name']}"
            )

            # 更新消息
            await callback_query.edit_message_text(
                f"✅ 歌曲已发送: {selected_song['name']} - {format_singers(selected_song['singer'])}"
            )

            # 清理下载文件
            try:
                os.remove(filepath)
                if cover_path and os.path.exists(cover_path):
                    os.remove(cover_path)
            except:
                pass

        except Exception as e:
            await callback_query.edit_message_text(f"❌ 处理歌曲时出错: {str(e)}")


