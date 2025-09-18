from PySide6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout
from qfluentwidgets import TextEdit, SubtitleLabel, ToolButton
from qfluentwidgets import FluentIcon as FIF

class LogInterface(QFrame):
    """ Log interface """

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName('LogInterface')

        self.v_layout = QVBoxLayout(self)
        
        self.title_layout = QHBoxLayout()
        self.title = SubtitleLabel("运行日志", self)
        self.clear_button = ToolButton(FIF.DELETE, self)

        self.log_text_edit = TextEdit(self)

        self.__init_widgets()

    def __init_widgets(self):
        self.v_layout.setContentsMargins(36, 20, 36, 20)
        self.v_layout.setSpacing(15)

        self.log_text_edit.setReadOnly(True)
        self.clear_button.setToolTip("清空日志")
        
        self.title_layout.addWidget(self.title)
        self.title_layout.addStretch(1)
        self.title_layout.addWidget(self.clear_button)

        self.v_layout.addLayout(self.title_layout)
        self.v_layout.addWidget(self.log_text_edit)
