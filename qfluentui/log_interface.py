import logging
import os
from datetime import datetime
from PySide6.QtCore import QObject, Signal, Slot
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout
from qfluentwidgets import TextEdit, SubtitleLabel, ToolButton
from qfluentwidgets import FluentIcon as FIF
from utils.logger import logger as app_logger

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
        self.__init_logging()

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

        # 交互
        self.clear_button.clicked.connect(self.log_text_edit.clear)

    # --- logging 接入 ---
    def __init_logging(self):
        """将全局 logger 输出接入到日志面板，线程安全地追加文本。"""
        # 建立线程安全信号，将日志从 logging.Handler 分发到 UI 线程
        class _Emitter(QObject):
            message = Signal(str)

        self._emitter = _Emitter(self)
        self._emitter.message.connect(self._append_text)

        # 自定义 Handler：格式化后发射信号
        class QtLogHandler(logging.Handler):
            def __init__(self, emit_signal):
                super().__init__()
                self._emit_signal = emit_signal

            def emit(self, record: logging.LogRecord):
                try:
                    msg = self.format(record)
                except Exception:
                    msg = record.getMessage()
                # 通过 Qt 信号转到主线程
                self._emit_signal(msg)

        self._qt_handler = QtLogHandler(lambda s: self._emitter.message.emit(s))
        # 使用简洁格式，避免重复的模块/行号信息
        formatter = logging.Formatter('[%(levelname)s] %(asctime)s - %(message)s')
        self._qt_handler.setFormatter(formatter)

        # 接入到全局 logger
        try:
            app_logger.add_handler(self._qt_handler)
        except Exception:
            pass

        # 初始载入当日日志文件（如存在），便于进入页面即可看到历史
        try:
            log_dir = os.path.join('logs')
            date_str = datetime.now().strftime('%Y.%m.%d')
            log_path = os.path.join(log_dir, f'{date_str}.log')
            if os.path.exists(log_path):
                with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    if content:
                        self.log_text_edit.setPlainText(content)
                        self._scroll_to_end()
        except Exception:
            pass

    @Slot(str)
    def _append_text(self, text: str):
        self.log_text_edit.append(text)
        self._scroll_to_end()

    def _scroll_to_end(self):
        # 使用 QTextCursor.End 常量通过编辑器 API 滚动到底部
        try:
            self.log_text_edit.moveCursor(QTextCursor.End)
        except Exception:
            # 兼容兜底：保留旧逻辑但改用类常量
            cursor = self.log_text_edit.textCursor()
            try:
                cursor.movePosition(QTextCursor.End)
                self.log_text_edit.setTextCursor(cursor)
            except Exception:
                pass
        self.log_text_edit.ensureCursorVisible()
