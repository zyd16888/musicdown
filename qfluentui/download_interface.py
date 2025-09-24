import time
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QHeaderView, QTableWidgetItem, QWidget
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
        self._progress_widgets = {}       # row -> (ProgressBar, BodyLabel)
        self._speed_labels = {}           # row -> BodyLabel
        self._row_last_sample = {}        # row -> (last_bytes, last_time)

    def __init_widgets(self):
        self.v_layout.setContentsMargins(36, 20, 36, 20)
        self.v_layout.setSpacing(15)

        # Table
        # 调整为 6 列：歌曲名 | 歌手 | 状态 | 进度 | 速度 | 保存路径
        self.download_table.setColumnCount(6)
        self.download_table.setHorizontalHeaderLabels(["歌曲名", "歌手", "状态", "进度", "速度", "保存路径"])
        self.download_table.setEditTriggers(TableWidget.EditTrigger.NoEditTriggers)
        
        # Set column width
        h = self.download_table.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        h.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        h.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        h.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        h.resizeSection(3, 220)  # 进度列包含进度条 + 百分比
        h.resizeSection(4, 140)  # 速度列固定更宽，避免遮挡

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

        # 进度列：进度条 + 百分比
        cell = QWidget(self.download_table)
        layout = QHBoxLayout(cell)
        layout.setContentsMargins(6, 0, 6, 0)
        layout.setSpacing(6)
        pb = ProgressBar(cell)
        pb.setRange(0, 100)
        pb.setValue(0)
        percent_label = BodyLabel("0%", cell)
        percent_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        layout.addWidget(pb, 1)
        layout.addWidget(percent_label)
        self.download_table.setCellWidget(row, 3, cell)
        self._progress_widgets[row] = (pb, percent_label)

        # 速度列先占位
        speed_lbl = BodyLabel("-", self.download_table)
        speed_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        speed_lbl.setStyleSheet("padding: 0 6px;")
        self.download_table.setCellWidget(row, 4, speed_lbl)
        self._speed_labels[row] = speed_lbl

        # 保存路径先占位
        self.download_table.setItem(row, 5, QTableWidgetItem("-"))

        self._row_progress_percent[row] = 0
        self._row_bytes[row] = (0, 0)
        self._update_overall_progress()
        return row

    def set_row_progress(self, row: int, value: int):
        percent = max(0, min(100, int(value)))
        # 更新控件
        pb, lbl = self._progress_widgets.get(row, (None, None))
        if pb is None or lbl is None:
            # 兼容旧行：尝试从 cell 中取出
            cell = self.download_table.cellWidget(row, 3)
            if isinstance(cell, QWidget) and cell.layout() and cell.layout().count() >= 2:
                pb = cell.layout().itemAt(0).widget()
                lbl = cell.layout().itemAt(1).widget()
                if isinstance(pb, ProgressBar) and isinstance(lbl, BodyLabel):
                    self._progress_widgets[row] = (pb, lbl)
        if isinstance(pb, ProgressBar):
            pb.setValue(percent)
        if isinstance(lbl, BodyLabel):
            lbl.setText(f"{percent}%")
        # 记录
        self._row_progress_percent[row] = percent
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
        self.download_table.setItem(row, 5, QTableWidgetItem(path_str))

    def set_row_progress_bytes(self, row: int, downloaded: int, total: int):
        # 百分比更新（≥1% 变化）
        percent = int(downloaded * 100 / total) if total > 0 else 0
        prev = self._row_progress_percent.get(row, -1)
        self._row_bytes[row] = (downloaded, total)
        if percent != prev and (abs(percent - prev) >= 1):
            self.set_row_progress(row, percent)

        # 速度更新（基于采样计算瞬时速度）
        now = time.time()
        last = self._row_last_sample.get(row)
        if last is None:
            self._row_last_sample[row] = (downloaded, now)
        else:
            last_bytes, last_time = last
            dt = max(1e-6, now - last_time)
            if dt >= 0.3:  # 至少 300ms 采样一次
                speed_bps = max(0, downloaded - last_bytes) / dt
                self._update_speed_label(row, speed_bps)
                self._row_last_sample[row] = (downloaded, now)

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

    def _update_speed_label(self, row: int, bps: float):
        lbl = self._speed_labels.get(row)
        if not isinstance(lbl, BodyLabel):
            return
        # 简单的人性化大小显示
        units = ["B/s", "KB/s", "MB/s", "GB/s"]
        val = bps
        idx = 0
        while val >= 1024 and idx < len(units) - 1:
            val /= 1024.0
            idx += 1
        lbl.setText(f"{val:.1f} {units[idx]}")
