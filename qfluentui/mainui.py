import sys
from typing import List

# Add project root to Python path
import os
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from PySide6.QtCore import QThread, Qt, QEvent, QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QTableWidgetItem, QWidget, QVBoxLayout
from qfluentwidgets import (
    FluentIcon as FIF,
    MSFluentWindow,
    NavigationItemPosition,
    InfoBar,
    PushButton,
    BodyLabel,
)

# Local imports
from api.adapter import MusicAdapter, Song, AlbumSearchResult, PlaylistSearchResult
from qfluentui.download_interface import DownloadInterface
from qfluentui.log_interface import LogInterface
from qfluentui.playlist_interface import PlaylistInterface
from qfluentui.search_interface import SearchInterface
from qfluentui.setting_interface import SettingInterface
from qfluentui.worker import AsyncWorker
from qfluentui.login import LoginPanel


class Window(MSFluentWindow):
    """ 主界面 """

    def __init__(self):
        super().__init__()

        # State
        self.search_page = 1
        self.current_search_query = ""
        self.current_search_type = "单曲"
        self.loading_bar = None

        # API Adapter
        self.adapter = MusicAdapter()
        self.active_threads = []

        # --- Interfaces ---
        self.searchInterface = SearchInterface(self)
        self.playlistInterface = PlaylistInterface(self)
        self.downloadInterface = DownloadInterface(self)
        self.logInterface = LogInterface(self)
        self.settingInterface = SettingInterface(self)

        self.initNavigation()
        self.initWindow()
        self.connect_signals()
        # 尝试在启动时加载并验证登录状态（若已保存）
        try:
            from api.qqmusic import QQMusicAPI
            self.__qqapi_auto__ = QQMusicAPI()
            self._validate_login_on_startup()
        except Exception:
            self.__qqapi_auto__ = None

    def initNavigation(self):
        self.addSubInterface(self.searchInterface, FIF.SEARCH, '搜索')
        self.addSubInterface(self.playlistInterface, FIF.MUSIC_FOLDER, '歌单')
        self.addSubInterface(self.downloadInterface, FIF.DOWNLOAD, '下载')
        self.addSubInterface(self.logInterface, FIF.DOCUMENT, '日志', position=NavigationItemPosition.BOTTOM)
        self.addSubInterface(self.settingInterface, FIF.SETTING, '设置', position=NavigationItemPosition.BOTTOM)

    def initWindow(self):
        self.resize(960, 580)
        self.setWindowIcon(QIcon("D:/project/python/musicdown/ui/icon.ico"))
        self.setWindowTitle('Music Downloader')

    def connect_signals(self):
        self.searchInterface.search_button.clicked.connect(lambda: self.start_search(is_new_search=True))
        self.searchInterface.search_input.returnPressed.connect(lambda: self.start_search(is_new_search=True))
        self.searchInterface.prev_page_button.clicked.connect(self.go_to_previous_page)
        self.searchInterface.next_page_button.clicked.connect(self.go_to_next_page)

    def go_to_previous_page(self):
        if self.search_page > 1:
            self.search_page -= 1
            self.start_search(is_new_search=False)

    def go_to_next_page(self):
        self.search_page += 1
        self.start_search(is_new_search=False)

    # 重写导航初始化：在“设置”上方增加“登录”入口
    def initNavigation(self):
        # 顶部功能
        self.addSubInterface(self.searchInterface, FIF.SEARCH, "搜索")
        self.addSubInterface(self.playlistInterface, FIF.MUSIC_FOLDER, "歌单")
        self.addSubInterface(self.downloadInterface, FIF.DOWNLOAD, "下载")

        # 底部功能：日志、登录、设置（登录位于设置上方）
        self.addSubInterface(
            self.logInterface,
            FIF.DOCUMENT,
            "日志",
            position=NavigationItemPosition.BOTTOM,
        )

        self.loginInterface = QWidget(self)
        self.addSubInterface(
            self.loginInterface,
            FIF.DOCUMENT,
            "登录",
            position=NavigationItemPosition.BOTTOM,
        )
        self.loginInterface.installEventFilter(self)

        self.addSubInterface(
            self.settingInterface,
            FIF.SETTING,
            "设置",
            position=NavigationItemPosition.BOTTOM,
        )

    # --- 登录界面（内嵌展示，无弹窗） ---
    def eventFilter(self, obj, event):
        # 目前不需要特殊事件，直接保持默认行为
        return super().eventFilter(obj, event)

    def on_login_success(self, credential):
        try:
            from api.qqmusic import QQMusicAPI
            QQMusicAPI().save_credential(credential)
        except Exception:
            pass

        InfoBar.success(
            "登录成功",
            f"用户ID: {getattr(credential, 'musicid', '-')}",
            duration=3000,
            parent=self,
        )
        # 在页面内更新登录状态显示：隐藏扫码面板，展示状态标签
        if hasattr(self, 'loginPanel'):
            try:
                self.loginPanel.hide()
            except Exception:
                pass
        if hasattr(self, 'loginStatusLabel'):
            uid = getattr(credential, 'musicid', '-')
            self.loginStatusLabel.setText(f"已登录：用户ID {uid}")
            self.loginStatusLabel.show()

    # 覆盖导航，新增“登录”按钮（置于“设置”上方）
    def initNavigation(self):
        # 顶部功能
        self.addSubInterface(self.searchInterface, FIF.SEARCH, '搜索')
        self.addSubInterface(self.playlistInterface, FIF.MUSIC_FOLDER, '歌单')
        self.addSubInterface(self.downloadInterface, FIF.DOWNLOAD, '下载')

        # 底部功能
        self.addSubInterface(self.logInterface, FIF.DOCUMENT, '日志', position=NavigationItemPosition.BOTTOM)

        # 登录入口：直接在页面内嵌登录面板
        self.loginInterface = QWidget(self)
        self.loginInterface.setObjectName('loginInterface')
        self.addSubInterface(self.loginInterface, FIF.PEOPLE, '登录', position=NavigationItemPosition.BOTTOM)
        # 内嵌布局：居中显示扫码与状态
        self.loginLayout = QVBoxLayout(self.loginInterface)
        self.loginLayout.setAlignment(Qt.AlignCenter)
        self.loginPanel = LoginPanel(self.loginInterface)
        self.loginPanel.login_succeeded.connect(self.on_login_success)
        self.loginStatusLabel = BodyLabel('', self.loginInterface)
        self.loginStatusLabel.hide()
        self.loginLayout.addWidget(self.loginPanel)
        self.loginLayout.addWidget(self.loginStatusLabel, 0, Qt.AlignCenter)

        self.addSubInterface(self.settingInterface, FIF.SETTING, '设置', position=NavigationItemPosition.BOTTOM)

    def start_search(self, is_new_search: bool = True):
        if is_new_search:
            self.search_page = 1
            self.current_search_query = self.searchInterface.search_input.text().strip()
            self.current_search_type = self.searchInterface.search_type_combo.currentText()

        if not self.current_search_query:
            return

        self.searchInterface.search_button.setEnabled(False)
        self.searchInterface.search_button.setText("搜索中...")
        self.searchInterface.result_table.clearContents()
        self.searchInterface.result_table.setRowCount(0)
        self.searchInterface.show_bottom_controls(False)

        limit = self.searchInterface.limit_spinbox.value()

        if self.current_search_type == "单曲":
            coro = self.adapter.search_song(keyword=self.current_search_query, limit=limit, page=self.search_page)
            self.run_async_task(coro, self.on_song_search_finished)
        elif self.current_search_type == "专辑":
            coro = self.adapter.search_album(keyword=self.current_search_query, limit=limit, page=self.search_page)
            self.run_async_task(coro, self.on_album_search_finished)
        elif self.current_search_type == "歌单":
            coro = self.adapter.search_playlist(keyword=self.current_search_query, limit=limit, page=self.search_page)
            self.run_async_task(coro, self.on_playlist_search_finished)

    def on_song_search_finished(self, songs: List[Song]):
        self.searchInterface.search_button.setEnabled(True)
        self.searchInterface.search_button.setText("搜索")
        self.searchInterface.setup_for_song_results()

        if self._handle_empty_results(songs):
            return

        self._populate_song_table(songs)
        self._update_pagination(len(songs))
        InfoBar.success("搜索成功", f"找到了 {len(songs)} 首歌曲", duration=3000, parent=self)

    def on_album_search_finished(self, albums: List[AlbumSearchResult]):
        self.searchInterface.search_button.setEnabled(True)
        self.searchInterface.search_button.setText("搜索")
        self.searchInterface.setup_for_album_results()

        table = self.searchInterface.result_table
        table.clearContents()
        if self._handle_empty_results(albums):
            return

        table.setRowCount(len(albums))
        for i, album in enumerate(albums):
            table.setItem(i, 0, QTableWidgetItem(album.name))
            table.setItem(i, 1, QTableWidgetItem(album.artist_names))
            table.setItem(i, 2, QTableWidgetItem(album.publish_date))
            view_button = PushButton("查看歌曲", table)
            view_button.clicked.connect(lambda _, a=album: self.view_album_songs(a.mid))
            table.setCellWidget(i, 3, view_button)

        self._update_pagination(len(albums), is_song_search=False)
        InfoBar.success("搜索成功", f"找到了 {len(albums)} 张专辑", duration=3000, parent=self)

    def on_playlist_search_finished(self, playlists: List[PlaylistSearchResult]):
        self.searchInterface.search_button.setEnabled(True)
        self.searchInterface.search_button.setText("搜索")
        self.searchInterface.setup_for_playlist_results()

        table = self.searchInterface.result_table
        table.clearContents()
        if self._handle_empty_results(playlists):
            return

        table.setRowCount(len(playlists))
        for i, playlist in enumerate(playlists):
            table.setItem(i, 0, QTableWidgetItem(playlist.name))
            table.setItem(i, 1, QTableWidgetItem(playlist.creator_name))
            table.setItem(i, 2, QTableWidgetItem(str(playlist.song_count)))
            view_button = PushButton("查看歌曲", table)
            view_button.clicked.connect(
                lambda _, p=playlist: self.view_playlist_songs(p.id)
            )
            table.setCellWidget(i, 3, view_button)

        self._update_pagination(len(playlists), is_song_search=False)
        InfoBar.success("搜索成功", f"找到了 {len(playlists)} 个歌单", duration=3000, parent=self)

    def view_album_songs(self, album_mid: str):
        self.loading_bar = InfoBar.info(
            "正在加载",
            f"正在获取专辑歌曲...",
            duration=-1,
            isClosable=False,
            parent=self,
        )
        coro = self.adapter.get_album_songs(album_mid)
        self.run_async_task(coro, self.on_song_list_finished)

    def view_playlist_songs(self, playlist_id: int):
        self.loading_bar = InfoBar.info(
            "正在加载",
            f"正在获取歌单歌曲...",
            duration=-1,
            isClosable=False,
            parent=self,
        )
        coro = self.adapter.get_playlist_songs(playlist_id)
        self.run_async_task(coro, self.on_song_list_finished)

    def on_song_list_finished(self, songs: List[Song]):
        if self.loading_bar:
            self.loading_bar.close()
            self.loading_bar = None

        self.searchInterface.setup_for_song_results()
        table = self.searchInterface.result_table
        table.clearContents()

        if not songs:
            InfoBar.warning("无歌曲", "未能获取到歌曲列表", duration=3000, parent=self)
            self.searchInterface.show_bottom_controls(False)
            return

        self._populate_song_table(songs)
        self.searchInterface.show_bottom_controls(True, is_song_search=True)
        self.searchInterface.prev_page_button.hide()
        self.searchInterface.next_page_button.hide()
        self.searchInterface.page_label.hide()
        InfoBar.success(
            "加载成功", f"共获取到 {len(songs)} 首歌曲", duration=3000, parent=self
        )

    def _populate_song_table(self, songs: List[Song]):
        table = self.searchInterface.result_table
        table.setRowCount(len(songs))
        for i, song in enumerate(songs):
            checkbox_item = QTableWidgetItem()
            checkbox_item.setFlags(
                Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled
            )
            checkbox_item.setCheckState(Qt.CheckState.Unchecked)
            table.setItem(i, 0, checkbox_item)
            table.setItem(i, 1, QTableWidgetItem(song.title))
            table.setItem(i, 2, QTableWidgetItem(song.artist_names))
            table.setItem(i, 3, QTableWidgetItem(song.album.name if song.album else ""))
            table.setItem(i, 4, QTableWidgetItem(song.duration))
            download_button = PushButton("下载", table)
            table.setCellWidget(i, 5, download_button)

    def _handle_empty_results(self, results: list) -> bool:
        if not results:
            if self.search_page == 1:
                InfoBar.info("无结果", "未找到任何内容", duration=3000, parent=self)
            else:
                InfoBar.info("没有更多了", "已经是最后一页", duration=3000, parent=self)
                self.search_page -= 1
            is_song_search = self.current_search_type == "单曲"
            self.searchInterface.show_bottom_controls(self.search_page > 1, is_song_search)
            self.searchInterface.update_page_display(self.search_page, has_next=False, has_prev=self.search_page > 1)
            return True
        return False

    def _update_pagination(self, result_count: int, is_song_search: bool = True):
        limit = self.searchInterface.limit_spinbox.value()
        has_next = result_count == limit
        has_prev = self.search_page > 1
        self.searchInterface.show_bottom_controls(True, is_song_search)
        self.searchInterface.update_page_display(self.search_page, has_next=has_next, has_prev=has_prev)

    def handle_error(self, e: Exception):
        if self.loading_bar:
            self.loading_bar.close()
            self.loading_bar = None

        print(f"An error occurred: {e}")
        InfoBar.error("发生错误", str(e), duration=5000, parent=self)
        if not self.searchInterface.search_button.isEnabled():
            self.searchInterface.search_button.setEnabled(True)
            self.searchInterface.search_button.setText("搜索")

    def _validate_login_on_startup(self):
        # 异步验证已保存的登录凭据
        try:
            from api.qqmusic import QQMusicAPI
            api = QQMusicAPI()
        except Exception:
            return
        async def _coro():
            return await api.is_logged_in()
        def _on_finished(ok: bool):
            if ok:
                InfoBar.success('已登录', '已加载本地登录状态', duration=2000, parent=self)
        # 传入协程函数，避免创建未被 await 的协程对象
        self.run_async_task(_coro, _on_finished)

    def run_async_task(self, coro_or_func, on_finished_slot):
        """在线程中运行协程，兼容传入协程对象或返回协程的函数。
        注意：所有 UI 更新在主线程进行，避免跨线程 setParent 导致卡死。
        """
        thread = QThread()
        worker = AsyncWorker()
        thread.worker = worker
        worker.moveToThread(thread)

        class _Task:
            def __init__(self, c, cb):
                self.coro = c
                self.cb = cb

        # 记录 task->thread 的映射，便于完成后清理
        if not hasattr(self, "_async_threads"):
            self._async_threads = {}

        def _start_worker():
            try:
                coro_obj = coro_or_func() if callable(coro_or_func) else coro_or_func
                task = _Task(coro_obj, on_finished_slot)
                self._async_threads[id(task)] = thread
                worker.start.emit(task)
            except Exception as e:
                # 报错统一回主线程处理
                QTimer.singleShot(0, lambda: self.handle_error(e))
                thread.quit()

        worker.finished.connect(self._on_async_finished)
        worker.failed.connect(self._on_async_failed)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        self.active_threads.append(thread)
        thread.finished.connect(lambda: self.active_threads.remove(thread))
        thread.started.connect(_start_worker)
        thread.start()

    def _cleanup_async_task(self, task):
        try:
            task_id = id(task)
            t = getattr(self, "_async_threads", {}).pop(task_id, None)
            if t is not None:
                t.quit()
                t.wait()
        except Exception:
            pass

    def _on_async_finished(self, task, result):
        # 此方法在主线程执行（接收者为 Window 对象）
        try:
            cb = getattr(task, "cb", None)
            if callable(cb):
                cb(result)
        except Exception as e:
            self.handle_error(e)
        finally:
            self._cleanup_async_task(task)

    def _on_async_failed(self, task, exc: Exception):
        try:
            self.handle_error(exc)
        finally:
            self._cleanup_async_task(task)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    w = Window()
    w.show()
    app.exec()

