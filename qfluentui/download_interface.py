from PySide6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QHeaderView
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

    def __init_widgets(self):
        self.v_layout.setContentsMargins(36, 20, 36, 20)
        self.v_layout.setSpacing(15)

        # Table
        self.download_table.setColumnCount(4)
        self.download_table.setHorizontalHeaderLabels(["歌曲名", "歌手", "状态", "保存路径"])
        self.download_table.setEditTriggers(TableWidget.EditTrigger.NoEditTriggers)
        
        # Set column width
        self.download_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.download_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.download_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.download_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)

        # Progress bar
        self.progress_layout.addWidget(self.progress_label)
        self.progress_layout.addWidget(self.progress_bar)

        # Add widgets to layout
        self.v_layout.addWidget(self.title)
        self.v_layout.addWidget(self.download_table)
        self.v_layout.addLayout(self.progress_layout)
