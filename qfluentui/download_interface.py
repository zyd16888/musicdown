from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QHeaderView, QTableWidgetItem
from qfluentwidgets import TableWidget, ProgressBar, SubtitleLabel, BodyLabel

class DownloadInterface(QFrame):
    """ Download interface """

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName('DownloadInterface')

        self.v_layout = QVBoxLayout(self)
        
        self.title = SubtitleLabel("下载任务", self)
        
        self.download_table = TableWidget(self)
        
        self.progress_layout = QHBoxLayout()
        self.progress_label = BodyLabel("总体进度:", self)
        self.progress_bar = ProgressBar(self)

        self.__init_widgets()
        # 进度缓存
        self._row_progress_percent = {}   # row -> value (0-100)
        self._row_bytes = {}              # row -> (downloaded, total)

    def __init_widgets(self):
        self.v_layout.setContentsMargins(36, 20, 36, 20)
        self.v_layout.setSpacing(15)

        # Table
        # 调整为 5 列：歌曲名 | 歌手 | 状态 | 进度 | 保存路径
        self.download_table.setColumnCount(5)
        self.download_table.setHorizontalHeaderLabels(["歌曲名", "歌手", "状态", "进度", "保存路径"])
        self.download_table.setEditTriggers(TableWidget.EditTrigger.NoEditTriggers)
        
        # Set column width
        h = self.download_table.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        h.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        h.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        h.resizeSection(3, 160)  # 进度条列固定宽度，避免拥挤

        # Progress bar
        self.progress_layout.addWidget(self.progress_label)
        self.progress_layout.addWidget(self.progress_bar)

        # Add widgets to layout
        self.v_layout.addWidget(self.title)
        self.v_layout.addWidget(self.download_table)
        self.v_layout.addLayout(self.progress_layout)

    # --- Public API ---
    def add_download_task_row(self, title: str, artist: str) -> int:
        """新增一行下载任务，返回行号。"""
        row = self.download_table.rowCount()
        self.download_table.insertRow(row)

        self.download_table.setItem(row, 0, QTableWidgetItem(title))
        self.download_table.setItem(row, 1, QTableWidgetItem(artist))

        # 状态列文字
        self.set_row_status_text(row, "队列中")

        # 进度列放入进度条
        pb = ProgressBar(self.download_table)
        pb.setRange(0, 100)
        pb.setValue(0)
        self.download_table.setCellWidget(row, 3, pb)

        # 保存路径先占位
        self.download_table.setItem(row, 4, QTableWidgetItem("-"))

        self._row_progress_percent[row] = 0
        self._row_bytes[row] = (0, 0)
        self._update_overall_progress()
        return row

    def set_row_progress(self, row: int, value: int):
        widget = self.download_table.cellWidget(row, 3)
        if isinstance(widget, ProgressBar):
            widget.setValue(max(0, min(100, int(value))))
        self._row_progress_percent[row] = max(0, min(100, int(value)))
        self._update_overall_progress()

    def set_row_status_text(self, row: int, text: str):
        # 状态列（第2列）只显示文字，与进度列分离，避免重叠
        item = QTableWidgetItem(text)
        item.setTextAlignment(Qt.AlignCenter)
        self.download_table.setItem(row, 2, item)
        # 完成时将百分比设为 100（不改变进度条列的控件，仅更新总体进度）
        if text.startswith("完成"):
            self._row_progress_percent[row] = 100
        self._update_overall_progress()

    def set_row_path(self, row: int, path_str: str):
        self.download_table.setItem(row, 4, QTableWidgetItem(path_str))

    def set_row_progress_bytes(self, row: int, downloaded: int, total: int):
        # 仅当百分比变化达到 1% 再刷新，避免频繁重绘
        percent = int(downloaded * 100 / total) if total > 0 else 0
        prev = self._row_progress_percent.get(row, -1)
        self._row_bytes[row] = (downloaded, total)
        if percent != prev and (abs(percent - prev) >= 1):
            self.set_row_progress(row, percent)

    def _update_overall_progress(self):
        # 优先使用按字节加权的总体进度
        rows = [r for r, (_, total) in self._row_bytes.items() if total > 0]
        if rows:
            downloaded_sum = sum(self._row_bytes[r][0] for r in rows)
            total_sum = sum(self._row_bytes[r][1] for r in rows)
            overall = int(downloaded_sum * 100 / total_sum) if total_sum > 0 else 0
            self.progress_bar.setValue(overall)
            return

        # 回退：平均百分比
        if not self._row_progress_percent:
            self.progress_bar.setValue(0)
            return
        avg = sum(self._row_progress_percent.values()) / max(1, len(self._row_progress_percent))
        self.progress_bar.setValue(int(avg))
