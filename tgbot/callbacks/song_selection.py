from telegram.ext import ContextTypes, CallbackQueryHandler
from telegram import Update
import os
import sys
import tempfile
import traceback
from pathlib import Path

# 确保可以导入项目根目录的模块
current_dir = Path(__file__).parent
project_root = current_dir.parent.parent
sys.path.insert(0, str(project_root))


from api.qm import QQMusicAPI
from downloader.music_downloader import MusicDownloader
from utils.config import config
from utils.formatters import format_singers

# 初始化QQ音乐API和下载管理器
qq_music_api = QQMusicAPI()
music_downloader = MusicDownloader()


async def handle_song_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    callback_query = update.callback_query
    user_id = callback_query.from_user.id
    song_index = int(callback_query.data.split(":")[1])

    await callback_query.answer()  # 必须应答回调查询

    if user_id not in config.user_sessions or "search_results" not in config.user_sessions[user_id]:
        await callback_query.message.edit_text("会话已过期，请重新搜索")
        return

    songs = config.user_sessions[user_id]["search_results"]
    if song_index >= len(songs):
        await callback_query.message.edit_text("无效的选择，请重新搜索")
        return

    selected_song = songs[song_index]

    # 显示下载中消息
    await callback_query.message.edit_text(
        f"⏳ 正在下载歌曲: {selected_song['name']} - {format_singers(selected_song['singer'])}..."
    )

    try:
        # 创建临时目录用于下载
        temp_dir = Path(tempfile.mkdtemp(prefix="qqmusic_"))

        # 使用 MusicDownloader 下载并处理歌曲
        try:
            filepath = await music_downloader.download_song(
                song_info=selected_song,
                download_dir=temp_dir,
                filetype='flac'
            )

            if not filepath:
                error_msg = "❌ 下载歌曲失败，可能原因：\n"
                error_msg += "- 该歌曲可能需要VIP权限\n"
                error_msg += "- 歌曲可能有版权限制\n"
                error_msg += "- 网络连接问题\n"
                error_msg += "请稍后重试或尝试其他歌曲。"

                await callback_query.message.edit_text(error_msg)
                # 清理临时目录
                try:
                    import shutil
                    shutil.rmtree(temp_dir, ignore_errors=True)
                except:
                    pass
                return
        except Exception as download_error:
            error_msg = f"❌ 下载歌曲时出错：\n{str(download_error)}\n请稍后重试或尝试其他歌曲。"
            await callback_query.message.edit_text(error_msg)
            # 清理临时目录
            try:
                import shutil
                shutil.rmtree(temp_dir, ignore_errors=True)
            except:
                pass
            return

        # 获取专辑封面
        album_mid = selected_song['album']['mid']
        cover_path = None
        try:
            cover_path = await music_downloader.download_manager.download_album_cover(album_mid, temp_dir)
        except Exception as cover_error:
            print(f"封面下载失败: {str(cover_error)}")
            pass  # 如果封面下载失败，继续而不使用封面

        # 准备发送的音频信息
        caption = f"🎵 {selected_song['name']}\n👤 {format_singers(selected_song['singer'])}\n💿 {selected_song['album']['name']}"

        await callback_query.message.edit_text(f"正在发送音频文件： 💿 {selected_song['album']['name']}")

        # 发送歌曲文件
        try:
            with open(str(filepath), 'rb') as audio_file:
                if cover_path and os.path.exists(str(cover_path)):
                    with open(str(cover_path), 'rb') as thumb_file:
                        await context.bot.send_audio(
                            chat_id=callback_query.message.chat_id,
                            audio=audio_file,
                            title=selected_song['name'],
                            performer=format_singers(selected_song['singer']),
                            duration=selected_song.get('interval', 0),
                            thumbnail=thumb_file,
                            caption=caption
                        )
                else:
                    await context.bot.send_audio(
                        chat_id=callback_query.message.chat_id,
                        audio=audio_file,
                        title=selected_song['name'],
                        performer=format_singers(selected_song['singer']),
                        duration=selected_song.get('interval', 0),
                        caption=caption
                    )
        except Exception as send_error:
            error_msg = f"❌ 发送音频文件时出错：\n{str(send_error)}\n请稍后重试。"
            await callback_query.message.edit_text(error_msg)
            # 清理临时目录
            try:
                import shutil
                shutil.rmtree(temp_dir, ignore_errors=True)
            except:
                pass
            return

        # 更新消息
        await callback_query.message.edit_text(
            f"✅ 歌曲已发送: {selected_song['name']} - {format_singers(selected_song['singer'])}"
        )

        # 清理临时目录
        try:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
        except Exception as e:
            print(f"清理临时目录失败: {str(e)}")

    except Exception as e:
        # 获取详细的错误信息
        error_details = traceback.format_exc()
        print(f"处理歌曲时出错: {error_details}")

        # 向用户显示友好的错误信息，包含错误原因
        error_msg = f"❌ 处理歌曲时出错: {str(e)}\n请稍后重试或联系管理员。"
        await callback_query.message.edit_text(error_msg)

        # 确保出错时也清理临时目录
        try:
            if 'temp_dir' in locals():
                import shutil
                shutil.rmtree(temp_dir, ignore_errors=True)
        except:
            pass


def register(app):
    app.add_handler(CallbackQueryHandler(
        handle_song_selection, pattern=r"^song:(\d+)$"))


