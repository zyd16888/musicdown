from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout
from qfluentwidgets import (
    ScrollArea, CardWidget, SubtitleLabel, BodyLabel, LineEdit, PushButton, ComboBox
)

class SettingInterface(ScrollArea):
    """ Setting interface """

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName('SettingInterface')
        self.scrollWidget = QWidget()
        self.scrollWidget.setObjectName('scrollWidget')
        self.v_layout = QVBoxLayout(self.scrollWidget)

        self.setting_label = SubtitleLabel("设置", self)

        # --- Download Card ---
        self.download_card = CardWidget(self)
        self.download_layout = QVBoxLayout(self.download_card)
        self.download_title = BodyLabel("下载路径", self.download_card)
        self.download_control_layout = QHBoxLayout()
        self.download_path_edit = LineEdit(self)
        self.download_browse_button = PushButton("浏览", self)

        # --- Quality Card ---
        self.quality_card = CardWidget(self)
        self.quality_layout = QHBoxLayout(self.quality_card)
        self.quality_title = BodyLabel("下载音质", self.quality_card)
        self.quality_combo = ComboBox(self)

        self.__init_widgets()

        # Make the background transparent
        self.setStyleSheet("QScrollArea, #scrollWidget { background-color: transparent; }")

    def __init_widgets(self):
        self.setWidget(self.scrollWidget)
        self.setWidgetResizable(True)
        self.v_layout.setContentsMargins(36, 20, 36, 20)
        self.v_layout.setSpacing(15)

        self.v_layout.addWidget(self.setting_label)

        # --- Setup Download Card ---
        self.download_path_edit.setReadOnly(True)
        self.download_path_edit.setPlaceholderText("当前未设置")
        self.download_control_layout.addWidget(self.download_path_edit, 1)
        self.download_control_layout.addWidget(self.download_browse_button)
        self.download_layout.addWidget(self.download_title)
        self.download_layout.addLayout(self.download_control_layout)
        self.v_layout.addWidget(self.download_card)

        # --- Setup Quality Card ---
        self.quality_combo.addItems([
            "M4A", "MP3 128kbps", "MP3 320kbps", "FLAC", 
            "臻品音质2.0", "臻品全景声2.0", "臻品母带2.0"
        ])
        self.quality_layout.addWidget(self.quality_title)
        self.quality_layout.addStretch(1)
        self.quality_layout.addWidget(self.quality_combo)
        self.v_layout.addWidget(self.quality_card)

        self.v_layout.addStretch(1)