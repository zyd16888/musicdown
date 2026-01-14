from typing import List, Optional

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QAction
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel
from qfluentwidgets import ToolButton, FluentIcon as FIF, InfoBar


class TrackItem:
    def __init__(self, title: str, source: str, value: str):
        self.title = title
        self.source = source  # 'file' or 'url'
        self.value = value


class PlayerBar(QWidget):
    """Floating mini player bar.

    - Prev / Play-Pause / Next buttons
    - Title text
    - Simple queue management (FIFO)
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('PlayerBar')
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet('#PlayerBar { background: rgba(245,245,245,0.9); border-top: 1px solid rgba(0,0,0,0.08); }')
        self.setFixedHeight(64)

        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(12, 8, 12, 8)
        self.layout.setSpacing(8)

        self.prevBtn = ToolButton(FIF.PAGE_RIGHT, self)
        self.playBtn = ToolButton(FIF.PLAY_SOLID, self)
        self.nextBtn = ToolButton(FIF.PAGE_LEFT, self)
        self.titleLabel = QLabel('未播放', self)
        self.titleLabel.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)

        self.layout.addWidget(self.prevBtn)
        self.layout.addWidget(self.playBtn)
        self.layout.addWidget(self.nextBtn)
        self.layout.addSpacing(6)
        self.layout.addWidget(self.titleLabel, 1)

        self.player = QMediaPlayer(self)
        self.audio = QAudioOutput(self)
        self.player.setAudioOutput(self.audio)
        self.audio.setVolume(0.8)

        self.queue: List[TrackItem] = []
        self.current_index: int = -1
        self.is_paused: bool = False

        self.prevBtn.clicked.connect(self.play_previous)
        self.playBtn.clicked.connect(self.toggle_play)
        self.nextBtn.clicked.connect(self.play_next)
        self.player.mediaStatusChanged.connect(self._on_media_status_changed)

    # ------------- Public API -------------
    def enqueue_file(self, title: str, file_path: str, auto_play: bool = False):
        self.queue.append(TrackItem(title, 'file', file_path))
        if auto_play and self.current_index == -1:
            self.current_index = len(self.queue) - 1
            self._play_current()

    def enqueue_url(self, title: str, url: str, auto_play: bool = False):
        self.queue.append(TrackItem(title, 'url', url))
        if auto_play and self.current_index == -1:
            self.current_index = len(self.queue) - 1
            self._play_current()

    def clear_queue(self):
        self.queue.clear()
        self.current_index = -1
        self.player.stop()
        self.titleLabel.setText('未播放')
        self.playBtn.setIcon(FIF.PLAY)

    # ------------- Controls -------------
    def toggle_play(self):
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
            self.playBtn.setIcon(FIF.PLAY)
            self.is_paused = True
        else:
            if self.current_index == -1 and self.queue:
                self.current_index = 0
                self._play_current()
            else:
                self.player.play()
            self.playBtn.setIcon(FIF.PAUSE)
            self.is_paused = False

    def play_next(self):
        if not self.queue:
            return
        self.current_index = (self.current_index + 1) % len(self.queue)
        self._play_current()

    def play_previous(self):
        if not self.queue:
            return
        self.current_index = (self.current_index - 1) % len(self.queue)
        self._play_current()

    # ------------- Internals -------------
    def _play_current(self):
        if self.current_index < 0 or self.current_index >= len(self.queue):
            return
        item = self.queue[self.current_index]
        self.titleLabel.setText(item.title)
        try:
            if item.source == 'file':
                self.player.setSource(QUrl.fromLocalFile(item.value))
            else:
                self.player.setSource(QUrl(item.value))
            self.player.play()
            self.playBtn.setIcon(FIF.PAUSE)
        except Exception:
            InfoBar.error('播放失败', item.title, duration=2000, parent=self)

    def _on_media_status_changed(self, status):
        # 自动下一首
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            if self.queue:
                self.play_next()

