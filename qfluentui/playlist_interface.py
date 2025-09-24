from PySide6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QHeaderView
from qfluentwidgets import (SearchLineEdit, PrimaryPushButton, TableWidget, PushButton, SubtitleLabel)

class PlaylistInterface(QFrame):
    """ Playlist interface """

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName('PlaylistInterface')

        self.v_layout = QVBoxLayout(self)
        
        self.title = SubtitleLabel("歌单链接下载", self)

        # --- Link Input ---
        self.link_input_layout = QHBoxLayout()
        self.link_input = SearchLineEdit(self)
        self.get_playlist_button = PrimaryPushButton("获取歌单", self)

        # --- Song Table ---
        self.playlist_table = TableWidget(self)

        # --- Action Buttons ---
        self.action_button_layout = QHBoxLayout()
        self.select_all_button = PushButton("全选", self)
        self.batch_download_button = PrimaryPushButton("批量下载选中歌曲", self)

        self.__init_widgets()

    def __init_widgets(self):
        self.v_layout.setContentsMargins(36, 20, 36, 20)
        self.v_layout.setSpacing(15)

        # Link input
        self.link_input.setPlaceholderText("输入QQ音乐歌单链接...")
        self.link_input_layout.addWidget(self.link_input, 1)
        self.link_input_layout.addWidget(self.get_playlist_button)

        # Table（与搜索页面保持一致：不单独展示可用音质列）
        self.playlist_table.setColumnCount(6)
        self.playlist_table.setHorizontalHeaderLabels(["", "歌曲名", "歌手", "专辑", "时长", "操作"])
        self.playlist_table.setEditTriggers(TableWidget.EditTrigger.NoEditTriggers)
        
        # Set column width
        self.playlist_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.playlist_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.playlist_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.playlist_table.horizontalHeader().resizeSection(0, 40)  # Checkbox
        self.playlist_table.horizontalHeader().resizeSection(4, 100)  # Duration
        self.playlist_table.horizontalHeader().resizeSection(5, 120)  # Action

        # Action buttons
        self.action_button_layout.addWidget(self.select_all_button)
        self.action_button_layout.addWidget(self.batch_download_button)
        self.action_button_layout.addStretch(1)

        # Add widgets to layout
        self.v_layout.addWidget(self.title)
        self.v_layout.addLayout(self.link_input_layout)
        self.v_layout.addWidget(self.playlist_table)
        self.v_layout.addLayout(self.action_button_layout)
