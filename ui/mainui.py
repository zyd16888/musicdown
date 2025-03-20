import asyncio
import sys
from pathlib import Path
from typing import Dict, List, Optional

from PyQt6.QtCore import Qt, QThread, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QIcon, QPixmap, QTextCursor
from PyQt6.QtWidgets import (QApplication, QComboBox, QFileDialog, QGridLayout,
                             QHBoxLayout, QHeaderView, QLabel, QLineEdit,
                             QMainWindow, QMessageBox, QProgressBar, QPushButton,
                             QRadioButton, QTabWidget, QTableWidget,
                             QTableWidgetItem, QVBoxLayout, QWidget, QTextEdit)

from api.qm import QQMusicAPI
from downloader.music_downloader import MusicDownloader
from utils.menum import SearchType
import logging


class WorkerThread(QThread):
    """工作线程，处理异步任务"""
    update_signal = pyqtSignal(dict)
    error_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int, int)  # 当前进度, 总进度

    def __init__(self, task_type, api=None, downloader=None, params=None):
        super().__init__()
        self.task_type = task_type
        self.api = api
        self.downloader = downloader
        self.params = params or {}

    async def run_task(self):
        try:
            if self.task_type == "search_song":
                result = await self.api.search(
                    self.params["query"],
                    SearchType.SONG,
                    self.params.get("page", 1),
                    self.params.get("limit", 20)
                )
                self.update_signal.emit(
                    {"type": "search_result", "data": result})

            elif self.task_type == "search_album":
                result = await self.api.search(
                    self.params["query"],
                    SearchType.ALBUM,
                    self.params.get("page", 1),
                    self.params.get("limit", 20)
                )
                self.update_signal.emit(
                    {"type": "search_result", "data": result})

            elif self.task_type == "get_album_songs":
                result = await self.api.get_album_songs(self.params["album_mid"])
                self.update_signal.emit(
                    {"type": "album_songs", "data": result})

            elif self.task_type == "search_playlist":
                result = await self.api.search(
                    self.params["query"],
                    SearchType.SONGLIST,
                    self.params.get("page", 1),
                    self.params.get("limit", 20)
                )
                self.update_signal.emit(
                    {"type": "search_result", "data": result})

            elif self.task_type == "get_playlist":
                result = await self.api.get_playlist(self.params["disstid"])
                self.update_signal.emit(
                    {"type": "playlist_songs", "data": result})

            elif self.task_type == "download_song":
                song_info = self.params["song_info"]
                filetype = self.params["filetype"]
                download_dir = self.params.get("download_dir")
                result = await self.downloader.download_song(song_info, download_dir, filetype)
                self.update_signal.emit({
                    "type": "download_complete",
                    "data": {
                        "success": result is not None,
                        "path": str(result) if result else None,
                        "song_name": song_info["name"],
                        "singer": song_info["singer"]
                    }
                })

            elif self.task_type == "download_multiple":
                songs = self.params["songs"]
                filetype = self.params["filetype"]
                download_dir = self.params.get("download_dir")
                total = len(songs)

                for i, song_info in enumerate(songs):
                    self.progress_signal.emit(i, total)
                    result = await self.downloader.download_song(song_info, download_dir, filetype)
                    self.update_signal.emit({
                        "type": "download_progress",
                        "data": {
                            "current": i + 1,
                            "total": total,
                            "success": result is not None,
                            "path": str(result) if result else None,
                            "song_name": song_info["name"],
                            "singer": song_info["singer"]
                        }
                    })

                self.update_signal.emit({"type": "download_all_complete"})

        except Exception as e:
            self.error_signal.emit(str(e))

    def run(self):
        print(f"Starting new thread for task: {self.task_type}")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self.run_task())
        except Exception as e:
            print(f"Error in thread: {e}")
            import traceback
            traceback.print_exc()
        finally:
            # 不要关闭事件循环，仅清理它
            loop.run_until_complete(loop.shutdown_asyncgens())
        print(f"Thread completed for task: {self.task_type}")


class QQMusicDownloaderGUI(QMainWindow):
    """QQ音乐下载器GUI"""

    def __init__(self):
        super().__init__()
        self.api = QQMusicAPI()
        self.downloader = MusicDownloader()

        # 存储搜索结果
        self.search_results = []
        self.album_songs = []
        self.playlist_songs = []

        # 设置下载路径
        self.download_path = str(Path.home() / "Downloads")

        # 存储当前活动的工作线程
        self.current_worker = None

        # 初始化日志显示区域
        self.log_text = None

        # 初始化UI，应该放在所有属性初始化之后
        self.initUI()

        # 注册日志处理器
        self.setup_logger()

    def initUI(self):
        """初始化UI"""
        self.setWindowTitle("QQ音乐下载器")
        self.setGeometry(100, 100, 1000, 700)

        # 主布局
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)

        # 搜索部分
        search_layout = QHBoxLayout()

        # 搜索类型选择
        self.search_type_combo = QComboBox()
        self.search_type_combo.addItems(["单曲搜索", "专辑搜索", "歌单搜索"])
        search_layout.addWidget(QLabel("搜索类型:"))
        search_layout.addWidget(self.search_type_combo)

        # 搜索框和按钮
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("输入关键词搜索...")
        self.search_input.returnPressed.connect(self.search)

        self.search_btn = QPushButton("搜索")
        self.search_btn.clicked.connect(self.search)

        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.search_btn)

        main_layout.addLayout(search_layout)

        # 选项卡组件
        self.tabs = QTabWidget()

        # 搜索结果标签页
        self.search_tab = QWidget()
        search_tab_layout = QVBoxLayout(self.search_tab)

        # 搜索结果表格
        self.result_table = QTableWidget()
        self.result_table.setColumnCount(6)
        self.result_table.setHorizontalHeaderLabels(
            ["", "歌曲名", "歌手", "专辑", "时长", "操作"])
        self.result_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents)
        self.result_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch)
        self.result_table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers)
        self.result_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows)

        search_tab_layout.addWidget(self.result_table)

        # 批量下载按钮
        batch_download_layout = QHBoxLayout()
        self.select_all_btn = QPushButton("全选")
        self.select_all_btn.clicked.connect(self.select_all_songs)

        self.batch_download_btn = QPushButton("批量下载选中歌曲")
        self.batch_download_btn.clicked.connect(self.batch_download)

        batch_download_layout.addWidget(self.select_all_btn)
        batch_download_layout.addWidget(self.batch_download_btn)
        batch_download_layout.addStretch()

        search_tab_layout.addLayout(batch_download_layout)

        # 下载设置标签页
        self.settings_tab = QWidget()
        settings_layout = QGridLayout(self.settings_tab)
        settings_layout.setAlignment(Qt.AlignmentFlag.AlignTop)  # 添加顶部对齐

        # 下载路径设置
        settings_layout.addWidget(
            QLabel("下载保存路径:"), 0, 0, Qt.AlignmentFlag.AlignTop)
        self.path_input = QLineEdit(self.download_path)
        self.path_input.setReadOnly(True)
        settings_layout.addWidget(
            self.path_input, 0, 1, Qt.AlignmentFlag.AlignTop)

        self.browse_btn = QPushButton("浏览...")
        self.browse_btn.clicked.connect(self.browse_path)
        settings_layout.addWidget(
            self.browse_btn, 0, 2, Qt.AlignmentFlag.AlignTop)

        # 音质选择
        settings_layout.addWidget(
            QLabel("下载音质:"), 1, 0, Qt.AlignmentFlag.AlignTop)
        quality_layout = QHBoxLayout()
        quality_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.quality_m4a = QRadioButton("M4A")
        self.quality_128 = QRadioButton("MP3 128kbps")
        self.quality_320 = QRadioButton("MP3 320kbps")
        self.quality_flac = QRadioButton("FLAC")

        self.quality_320.setChecked(True)  # 默认选择320kbps

        quality_layout.addWidget(self.quality_m4a)
        quality_layout.addWidget(self.quality_128)
        quality_layout.addWidget(self.quality_320)
        quality_layout.addWidget(self.quality_flac)
        quality_layout.addStretch()

        settings_layout.addLayout(quality_layout, 1, 1, 1, 2)

        # 下载记录标签
        self.download_tab = QWidget()
        download_layout = QVBoxLayout(self.download_tab)

        self.download_table = QTableWidget()
        self.download_table.setColumnCount(4)
        self.download_table.setHorizontalHeaderLabels(
            ["歌曲名", "歌手", "状态", "保存路径"])
        self.download_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents)
        self.download_table.horizontalHeader().setSectionResizeMode(
            3, QHeaderView.ResizeMode.Stretch)
        self.download_table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers)

        download_layout.addWidget(self.download_table)

        # 下载进度
        progress_layout = QHBoxLayout()
        progress_layout.addWidget(QLabel("总体进度:"))
        self.progress_bar = QProgressBar()
        progress_layout.addWidget(self.progress_bar)

        download_layout.addLayout(progress_layout)

        # 添加标签页到选项卡
        self.tabs.addTab(self.search_tab, "搜索结果")
        self.tabs.addTab(self.settings_tab, "下载设置")
        self.tabs.addTab(self.download_tab, "下载记录")

        # 添加新的日志选项卡
        self.log_tab = QWidget()
        log_layout = QVBoxLayout(self.log_tab)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        self.log_text.setStyleSheet("font-family: Courier, monospace;")

        log_layout.addWidget(self.log_text)

        # 清除日志按钮
        clear_log_btn = QPushButton("清除日志")
        clear_log_btn.clicked.connect(self.clear_log)
        log_layout.addWidget(clear_log_btn)

        self.tabs.addTab(self.log_tab, "下载日志")

        main_layout.addWidget(self.tabs)

        self.setCentralWidget(main_widget)

    def setup_logger(self):
        """设置日志处理器，将日志消息发送到UI"""
        class UILogHandler(logging.Handler):
            def __init__(self, ui_instance):
                super().__init__()
                self.ui = ui_instance

            def emit(self, record):
                msg = self.format(record)
                self.ui.update_log(msg)

        # 创建并添加UI日志处理器
        ui_handler = UILogHandler(self)
        formatter = logging.Formatter(
            '[%(levelname)s] %(asctime)s - %(message)s')
        ui_handler.setFormatter(formatter)

        # 添加到logger
        from utils.logger import logger
        logger.add_handler(ui_handler)

    def update_log(self, message):
        """更新日志显示区域"""
        if self.log_text:
            self.log_text.append(message)
            # 自动滚动到底部
            cursor = self.log_text.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            self.log_text.setTextCursor(cursor)

    def clear_log(self):
        """清除日志显示"""
        if self.log_text:
            self.log_text.clear()

    def get_selected_quality(self) -> str:
        """获取选择的音质"""
        if self.quality_m4a.isChecked():
            return "m4a"
        elif self.quality_128.isChecked():
            return "128"
        elif self.quality_320.isChecked():
            return "320"
        elif self.quality_flac.isChecked():
            return "flac"
        return "320"  # 默认

    @pyqtSlot()
    def search(self):
        """执行搜索"""
        query = self.search_input.text().strip()
        if not query:
            QMessageBox.warning(self, "提示", "请输入搜索关键词")
            return

        search_type_index = self.search_type_combo.currentIndex()
        self.result_table.setRowCount(0)  # 清空表格

        # 每次都创建新的工作线程
        if search_type_index == 0:  # 单曲搜索
            worker = WorkerThread(
                "search_song", api=self.api, params={"query": query})
        elif search_type_index == 1:  # 专辑搜索
            worker = WorkerThread(
                "search_album", api=self.api, params={"query": query})
        elif search_type_index == 2:  # 歌单搜索
            worker = WorkerThread(
                "search_playlist", api=self.api, params={"query": query})

        # 连接信号
        worker.update_signal.connect(self.handle_worker_update)
        worker.error_signal.connect(self.handle_worker_error)

        # 保存引用以防止垃圾回收
        self.current_worker = worker
        worker.start()

    @pyqtSlot(dict)
    def handle_worker_update(self, data):
        """处理工作线程的更新信号"""
        update_type = data["type"]

        # 特殊处理下载完成的情况，因为它没有data字段
        if update_type == "download_all_complete":
            self.progress_bar.setValue(100)
            QMessageBox.information(self, "下载完成", "所有选中的歌曲已下载完成！")
            return

        update_data = data["data"]

        if update_type == "search_result":
            self.display_search_results(update_data)

        elif update_type == "album_songs":
            self.album_songs = update_data["songList"]
            self.display_album_songs(update_data)

        elif update_type == "playlist_songs":
            self.playlist_songs = update_data["songs"]
            self.display_playlist_songs(update_data)

        elif update_type == "download_complete":
            self.update_download_record(update_data)

        elif update_type == "download_progress":
            self.update_download_progress(update_data)

    @pyqtSlot(str)
    def handle_worker_error(self, error_msg):
        """处理工作线程的错误信号"""
        QMessageBox.critical(self, "错误", f"发生错误: {error_msg}")

    @pyqtSlot(int, int)
    def handle_progress_update(self, current, total):
        """处理下载进度更新"""
        progress = int(current / total * 100) if total > 0 else 0
        self.progress_bar.setValue(progress)

    def display_search_results(self, result):
        """显示搜索结果"""
        if self.search_type_combo.currentIndex() == 0:  # 单曲
            self.search_results = result["songs"]
            self.result_table.setColumnCount(6)
            self.result_table.setHorizontalHeaderLabels(
                ["", "歌曲名", "歌手", "专辑", "时长", "操作"])

            self.result_table.setRowCount(len(self.search_results))
            for i, song in enumerate(self.search_results):
                # 复选框（用于批量选择）
                checkbox = QTableWidgetItem()
                checkbox.setFlags(
                    Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
                checkbox.setCheckState(Qt.CheckState.Unchecked)
                self.result_table.setItem(i, 0, checkbox)

                # 歌曲信息
                self.result_table.setItem(i, 1, QTableWidgetItem(song["name"]))
                self.result_table.setItem(i, 2, QTableWidgetItem(
                    ", ".join([s["name"] for s in song["singer"]])))
                self.result_table.setItem(
                    i, 3, QTableWidgetItem(song["album"]["name"]))

                # 时长
                duration = song.get("interval", 0)
                minutes, seconds = divmod(duration, 60)
                self.result_table.setItem(
                    i, 4, QTableWidgetItem(f"{minutes:02d}:{seconds:02d}"))

                # 下载按钮
                download_btn = QPushButton("下载")
                download_btn.clicked.connect(lambda checked, song_index=i: self.download_song(
                    self.search_results[song_index]))
                self.result_table.setCellWidget(i, 5, download_btn)

        elif self.search_type_combo.currentIndex() == 1:  # 专辑
            self.search_results = result["albums"]
            self.result_table.setColumnCount(4)
            self.result_table.setHorizontalHeaderLabels(
                ["专辑名", "歌手", "发行时间", "操作"])

            self.result_table.setRowCount(len(self.search_results))
            for i, album in enumerate(self.search_results):
                self.result_table.setItem(
                    i, 0, QTableWidgetItem(album["albumName"]))
                self.result_table.setItem(
                    i, 1, QTableWidgetItem(album["singerName"]))
                self.result_table.setItem(
                    i, 2, QTableWidgetItem(album.get("publicTime", "")))

                view_btn = QPushButton("查看歌曲")
                view_btn.clicked.connect(
                    lambda checked, album_mid=album["albumMID"]: self.get_album_songs(album_mid))
                self.result_table.setCellWidget(i, 3, view_btn)

        elif self.search_type_combo.currentIndex() == 2:  # 歌单
            self.search_results = result["playlists"]
            self.result_table.setColumnCount(4)
            self.result_table.setHorizontalHeaderLabels(
                ["歌单名", "创建者", "歌曲数量", "操作"])

            self.result_table.setRowCount(len(self.search_results))
            for i, playlist in enumerate(self.search_results):
                self.result_table.setItem(
                    i, 0, QTableWidgetItem(playlist["name"]))
                self.result_table.setItem(
                    i, 1, QTableWidgetItem(playlist["creator"]["name"]))
                self.result_table.setItem(
                    i, 2, QTableWidgetItem(str(playlist["songCount"])))

                view_btn = QPushButton("查看歌曲")
                view_btn.clicked.connect(
                    lambda checked, disstid=playlist["id"]: self.get_playlist(disstid))
                self.result_table.setCellWidget(i, 3, view_btn)

    def get_album_songs(self, album_mid):
        """获取专辑歌曲"""
        self.current_worker = WorkerThread("get_album_songs", api=self.api, params={
            "album_mid": album_mid})
        self.current_worker.update_signal.connect(self.handle_worker_update)
        self.current_worker.error_signal.connect(self.handle_worker_error)
        self.current_worker.start()

    def display_album_songs(self, album_data):
        """显示专辑歌曲"""
        self.result_table.setColumnCount(6)
        self.result_table.setHorizontalHeaderLabels(
            ["", "歌曲名", "歌手", "专辑", "时长", "操作"])

        # 修正: 从songList获取歌曲列表而非songs
        songs = album_data["songList"]
        self.result_table.setRowCount(len(songs))

        # 获取专辑名称 (从当前显示的专辑列表或album_data中)
        album_name = "未知专辑"
        for album in self.search_results:
            if album.get("albumMID") == album_data.get("albumMid"):
                album_name = album.get("albumName", "未知专辑")
                break

        # 添加下载专辑所有歌曲的按钮
        album_download_layout = QHBoxLayout()
        self.select_all_btn = QPushButton("全选")
        self.select_all_btn.clicked.connect(self.select_all_songs)

        # 添加批量下载选中歌曲按钮
        self.batch_download_btn = QPushButton("批量下载选中歌曲")
        self.batch_download_btn.clicked.connect(self.batch_download)

        self.download_album_btn = QPushButton("下载专辑所有歌曲")
        self.download_album_btn.clicked.connect(
            lambda: self.batch_download(songs))

        album_download_layout.addWidget(self.select_all_btn)
        album_download_layout.addWidget(self.batch_download_btn)
        album_download_layout.addWidget(self.download_album_btn)
        album_download_layout.addStretch()

        # 在显示歌曲列表前添加下载专辑按钮
        layout = self.search_tab.layout()
        if layout.count() > 1:
            # 移除原有的批量下载布局
            old_layout = layout.itemAt(1).layout()
            while old_layout.count():
                item = old_layout.takeAt(0)
                if item.widget():
                    item.widget().hide()

            # 删除旧布局
            layout.removeItem(old_layout)

        # 添加新布局
        layout.addLayout(album_download_layout)

        # 执行原有的歌曲列表填充代码
        for i, song in enumerate(songs):
            # 复选框
            checkbox = QTableWidgetItem()
            checkbox.setFlags(Qt.ItemFlag.ItemIsUserCheckable |
                              Qt.ItemFlag.ItemIsEnabled)
            checkbox.setCheckState(Qt.CheckState.Unchecked)
            self.result_table.setItem(i, 0, checkbox)

            # 歌曲信息
            self.result_table.setItem(i, 1, QTableWidgetItem(song["name"]))
            self.result_table.setItem(i, 2, QTableWidgetItem(
                ", ".join([s["name"] for s in song["singer"]])))
            self.result_table.setItem(i, 3, QTableWidgetItem(album_name))

            # 时长
            duration = song.get("interval", 0)
            minutes, seconds = divmod(duration, 60)
            self.result_table.setItem(
                i, 4, QTableWidgetItem(f"{minutes:02d}:{seconds:02d}"))

            # 下载按钮
            download_btn = QPushButton("下载")
            download_btn.clicked.connect(
                lambda checked, song_index=i: self.download_song(songs[song_index]))
            self.result_table.setCellWidget(i, 5, download_btn)

    def get_playlist(self, disstid):
        """获取歌单歌曲"""
        self.current_worker = WorkerThread(
            "get_playlist", api=self.api, params={"disstid": disstid})
        self.current_worker.update_signal.connect(self.handle_worker_update)
        self.current_worker.error_signal.connect(self.handle_worker_error)
        self.current_worker.start()

    def display_playlist_songs(self, playlist_data):
        """显示歌单歌曲"""
        self.result_table.setColumnCount(6)
        self.result_table.setHorizontalHeaderLabels(
            ["", "歌曲名", "歌手", "专辑", "时长", "操作"])

        songs = playlist_data["songs"]
        self.result_table.setRowCount(len(songs))

        for i, song in enumerate(songs):
            # 复选框
            checkbox = QTableWidgetItem()
            checkbox.setFlags(Qt.ItemFlag.ItemIsUserCheckable |
                              Qt.ItemFlag.ItemIsEnabled)
            checkbox.setCheckState(Qt.CheckState.Unchecked)
            self.result_table.setItem(i, 0, checkbox)

            # 歌曲信息
            self.result_table.setItem(i, 1, QTableWidgetItem(song["name"]))
            self.result_table.setItem(i, 2, QTableWidgetItem(
                ", ".join([s["name"] for s in song["singer"]])))
            self.result_table.setItem(
                i, 3, QTableWidgetItem(song["album"]["name"]))

            # 时长
            duration = song.get("interval", 0)
            minutes, seconds = divmod(duration, 60)
            self.result_table.setItem(
                i, 4, QTableWidgetItem(f"{minutes:02d}:{seconds:02d}"))

            # 下载按钮
            download_btn = QPushButton("下载")
            download_btn.clicked.connect(
                lambda checked, song_index=i: self.download_song(songs[song_index]))
            self.result_table.setCellWidget(i, 5, download_btn)

    def download_song(self, song_info):
        """下载单首歌曲"""
        filetype = self.get_selected_quality()

        # 使用用户设置的下载路径
        download_dir = Path(self.download_path)

        # 切换到下载记录标签页
        self.tabs.setCurrentIndex(2)

        # 添加下载记录
        row = self.download_table.rowCount()
        self.download_table.setRowCount(row + 1)

        self.download_table.setItem(
            row, 0, QTableWidgetItem(song_info["name"]))
        self.download_table.setItem(row, 1, QTableWidgetItem(
            ", ".join([s["name"] for s in song_info["singer"]])))
        self.download_table.setItem(row, 2, QTableWidgetItem("正在下载..."))
        self.download_table.setItem(row, 3, QTableWidgetItem(""))

        # 启动下载线程
        self.current_worker = WorkerThread(
            "download_song",
            downloader=self.downloader,
            params={
                "song_info": song_info,
                "filetype": filetype,
                "download_dir": download_dir
            }
        )
        self.current_worker.update_signal.connect(self.handle_worker_update)
        self.current_worker.error_signal.connect(self.handle_worker_error)
        self.current_worker.start()

    def select_all_songs(self):
        """全选/取消全选歌曲"""
        if self.result_table.rowCount() == 0:
            return

        # 检查当前是否已经全选
        all_checked = True
        for row in range(self.result_table.rowCount()):
            item = self.result_table.item(row, 0)
            if item and item.checkState() != Qt.CheckState.Checked:
                all_checked = False
                break

        # 设置新的状态
        new_state = Qt.CheckState.Unchecked if all_checked else Qt.CheckState.Checked

        # 更新所有复选框状态
        for row in range(self.result_table.rowCount()):
            item = self.result_table.item(row, 0)
            if item:
                item.setCheckState(new_state)

        # 刷新表格视图
        self.result_table.update()

    def batch_download(self):
        """批量下载选中的歌曲"""
        selected_songs = []

        # 获取表格中当前显示的歌曲
        current_songs = []
        search_type = self.search_type_combo.currentIndex()

        if search_type == 0:  # 单曲搜索
            current_songs = self.search_results
        elif search_type == 1 and self.album_songs:  # 专辑歌曲
            current_songs = self.album_songs
        elif search_type == 2 and self.playlist_songs:  # 歌单歌曲
            current_songs = self.playlist_songs

        # 收集选中的歌曲
        for row in range(self.result_table.rowCount()):
            item = self.result_table.item(row, 0)
            if item and item.checkState() == Qt.CheckState.Checked and row < len(current_songs):
                selected_songs.append(current_songs[row])

        if not selected_songs:
            QMessageBox.warning(self, "提示", "请选择要下载的歌曲")
            return

        # 切换到下载记录标签页
        self.tabs.setCurrentIndex(2)

        # 重置进度条
        self.progress_bar.setValue(0)

        # 添加下载记录
        start_row = self.download_table.rowCount()
        self.download_table.setRowCount(start_row + len(selected_songs))

        for i, song in enumerate(selected_songs):
            row = start_row + i
            self.download_table.setItem(row, 0, QTableWidgetItem(song["name"]))
            self.download_table.setItem(row, 1, QTableWidgetItem(
                ", ".join([s["name"] for s in song["singer"]])))
            self.download_table.setItem(row, 2, QTableWidgetItem("等待下载..."))
            self.download_table.setItem(row, 3, QTableWidgetItem(""))

        # 使用用户设置的下载路径
        download_dir = Path(self.download_path)

        # 启动批量下载线程
        filetype = self.get_selected_quality()
        self.current_worker = WorkerThread(
            "download_multiple",
            downloader=self.downloader,
            params={
                "songs": selected_songs,
                "filetype": filetype,
                "download_dir": download_dir
            }
        )
        self.current_worker.update_signal.connect(self.handle_worker_update)
        self.current_worker.error_signal.connect(self.handle_worker_error)
        self.current_worker.progress_signal.connect(
            self.handle_progress_update)
        self.current_worker.start()

    def update_download_record(self, data):
        """更新下载记录"""
        for row in range(self.download_table.rowCount()):
            song_name_item = self.download_table.item(row, 0)
            singer_item = self.download_table.item(row, 1)
            status_item = self.download_table.item(row, 2)

            if (song_name_item and song_name_item.text() == data["song_name"] and
                    singer_item and status_item and status_item.text() in ["正在下载...", "等待下载..."]):

                # 更新状态和路径
                if data["success"]:
                    self.download_table.setItem(
                        row, 2, QTableWidgetItem("下载成功"))
                    self.download_table.setItem(
                        row, 3, QTableWidgetItem(data["path"]))
                else:
                    self.download_table.setItem(
                        row, 2, QTableWidgetItem("下载失败"))

                break

    def update_download_progress(self, data):
        """更新批量下载进度"""
        # 更新进度条
        progress = int(data["current"] / data["total"] * 100)
        self.progress_bar.setValue(progress)

        # 更新下载记录
        for row in range(self.download_table.rowCount()):
            song_name_item = self.download_table.item(row, 0)
            singer_item = self.download_table.item(row, 1)
            status_item = self.download_table.item(row, 2)

            if (song_name_item and song_name_item.text() == data["song_name"] and
                    singer_item and status_item and status_item.text() == "等待下载..."):

                # 更新状态和路径
                if data["success"]:
                    self.download_table.setItem(
                        row, 2, QTableWidgetItem("下载成功"))
                    self.download_table.setItem(
                        row, 3, QTableWidgetItem(data["path"]))
                else:
                    self.download_table.setItem(
                        row, 2, QTableWidgetItem("下载失败"))

                break

    def browse_path(self):
        """浏览并选择下载保存路径"""
        dir_path = QFileDialog.getExistingDirectory(
            self, "选择下载保存位置", self.download_path)
        if dir_path:
            self.download_path = dir_path
            self.path_input.setText(dir_path)
