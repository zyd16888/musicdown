from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QFileDialog
from qfluentwidgets import (
    ScrollArea, CardWidget, SubtitleLabel, BodyLabel, LineEdit, PushButton, ComboBox, SpinBox, CheckBox
)
from utils.config import config

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

        # --- Concurrency Card ---
        self.concurrent_card = CardWidget(self)
        self.concurrent_layout = QHBoxLayout(self.concurrent_card)
        self.concurrent_title = BodyLabel("同时下载数量", self.concurrent_card)
        self.concurrent_spinbox = SpinBox(self)

        # --- Retry Card ---
        self.retry_card = CardWidget(self)
        self.retry_layout = QHBoxLayout(self.retry_card)
        self.retry_checkbox = CheckBox("下载失败时自动降低音质重试", self.retry_card)

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
        # 初始化为当前配置的下载目录
        try:
            self.download_path_edit.setText(str(config.DOWNLOADS_DIR))
        except Exception:
            self.download_path_edit.setPlaceholderText("当前未设置")
        self.download_control_layout.addWidget(self.download_path_edit, 1)
        self.download_control_layout.addWidget(self.download_browse_button)
        self.download_layout.addWidget(self.download_title)
        self.download_layout.addLayout(self.download_control_layout)
        self.v_layout.addWidget(self.download_card)

        # --- Setup Quality Card ---
        self.quality_combo.addItems([
            # 高阶音质
            "臻品母带2.0",         # MASTER
            "臻品音质2.0",         # ATMOS_51
            "臻品全景声2.0",       # ATMOS_2
            "FLAC",                # FLAC
            # OGG 档位
            "OGG 640kbps",         # OGG_640
            "OGG 320kbps",         # OGG_320
            "OGG 192kbps",         # OGG_192
            "OGG 96kbps",          # OGG_96
            # MP3 档位
            "MP3 320kbps",         # MP3_320
            "MP3 128kbps",         # MP3_128
            # M4A/AAC 档位
            "M4A（自动）",          # ACC_BEST（按 192>96>48 自动选择）
            "M4A 192kbps",         # ACC_192
            "M4A 96kbps",          # ACC_96
            "M4A 48kbps"           # ACC_48
        ])
        # 根据配置选择默认质量
        code2text = {
            # Canonical codes
            'MASTER': '臻品母带2.0',
            'ATMOS_51': '臻品音质2.0',
            'ATMOS_2': '臻品全景声2.0',
            'FLAC': 'FLAC',
            'OGG_640': 'OGG 640kbps',
            'OGG_320': 'OGG 320kbps',
            'OGG_192': 'OGG 192kbps',
            'OGG_96': 'OGG 96kbps',
            'MP3_320': 'MP3 320kbps',
            'MP3_128': 'MP3 128kbps',
            'ACC_BEST': 'M4A（自动）',
            'ACC_192': 'M4A 192kbps',
            'ACC_96': 'M4A 96kbps',
            'ACC_48': 'M4A 48kbps',
            # Legacy aliases
            'flac': 'FLAC',
            '320': 'MP3 320kbps',
            '128': 'MP3 128kbps',
            'm4a': 'M4A（自动）',
        }
        self.quality_combo.setCurrentText(code2text.get(getattr(config, 'DEFAULT_QUALITY', 'flac'), 'FLAC'))
        self.quality_layout.addWidget(self.quality_title)
        self.quality_layout.addStretch(1)
        self.quality_layout.addWidget(self.quality_combo)
        self.v_layout.addWidget(self.quality_card)

        # --- Setup Concurrency Card ---
        self.concurrent_spinbox.setRange(1, 10)
        try:
            self.concurrent_spinbox.setValue(int(getattr(config, 'MAX_CONCURRENT', 3)))
        except Exception:
            self.concurrent_spinbox.setValue(3)
        self.concurrent_layout.addWidget(self.concurrent_title)
        self.concurrent_layout.addStretch(1)
        self.concurrent_layout.addWidget(self.concurrent_spinbox)
        self.v_layout.addWidget(self.concurrent_card)

        # --- Setup Retry Card ---
        try:
            self.retry_checkbox.setChecked(bool(getattr(config, 'DOWNGRADE_RETRY', True)))
        except Exception:
            self.retry_checkbox.setChecked(True)
        self.retry_layout.addWidget(self.retry_checkbox)
        self.v_layout.addWidget(self.retry_card)

        self.v_layout.addStretch(1)

        # --- Connect signals ---
        self.download_browse_button.clicked.connect(self._on_browse_download_dir)
        self.concurrent_spinbox.valueChanged.connect(self._on_concurrency_changed)
        self.quality_combo.currentTextChanged.connect(self._on_quality_changed)
        self.retry_checkbox.stateChanged.connect(self._on_retry_changed)

    def _on_browse_download_dir(self):
        directory = QFileDialog.getExistingDirectory(self, "选择下载目录", str(config.DOWNLOADS_DIR))
        if directory:
            self.download_path_edit.setText(directory)
            # 保存到配置
            try:
                config.config_file.set("downloads.dir", directory)
                config.reload_config()
            except Exception:
                pass

    def _on_concurrency_changed(self, value: int):
        try:
            config.config_file.set("downloads.concurrent", int(value))
            config.reload_config()
        except Exception:
            pass

    def _on_retry_changed(self, _):
        try:
            val = bool(self.retry_checkbox.isChecked())
            config.config_file.set("downloads.downgradeRetry", val)
            config.reload_config()
        except Exception:
            pass

    def _on_quality_changed(self, text: str):
        # 将下拉文本映射为 canonical 质量码并保存到配置
        text2code = {
            '臻品母带2.0': 'MASTER',
            '臻品音质2.0': 'ATMOS_51',
            '臻品全景声2.0': 'ATMOS_2',
            'FLAC': 'FLAC',
            'OGG 640kbps': 'OGG_640',
            'OGG 320kbps': 'OGG_320',
            'OGG 192kbps': 'OGG_192',
            'OGG 96kbps': 'OGG_96',
            'MP3 320kbps': 'MP3_320',
            'MP3 128kbps': 'MP3_128',
            'M4A（自动）': 'ACC_BEST',
            'M4A 192kbps': 'ACC_192',
            'M4A 96kbps': 'ACC_96',
            'M4A 48kbps': 'ACC_48',
        }
        try:
            code = text2code.get(text, 'FLAC')
            config.config_file.set("quality", code)
            config.reload_config()
        except Exception:
            pass
