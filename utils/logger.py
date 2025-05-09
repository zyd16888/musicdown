import io
import logging
import os
import sys
import time
from logging import CRITICAL, DEBUG, ERROR, INFO, NOTSET, WARNING
from datetime import datetime



log_file = os.path.join("logs/", f'{time.strftime("%Y.%m.%d", time.localtime())}.log')
if not os.path.exists(os.path.dirname(log_file)):
    os.makedirs(os.path.dirname(log_file))

class Logger:
    def __init__(self) -> None:
        self.name = 'LDDC'
        self.__logger = logging.getLogger(self.name)
        self.level = self.str2log_level("DEBUG")
        self.last_progress = None  # 添加进度跟踪变量
        self.ui_handlers = []  # 存储UI处理器

        formatter = logging.Formatter('[%(levelname)s]%(asctime)s- %(module)s(%(lineno)d) - %(funcName)s:%(message)s')
        # 创建一个处理器,用于将日志写入文件
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        self.__logger.addHandler(file_handler)

        if __debug__ and (os.getenv("DEBUGPY_RUNNING") == "true" or sys.gettrace() is not None):
            # 调试时创建一个处理器,用于将日志输出到标准输出
            console_handler = logging.StreamHandler(sys.stdout)
            if isinstance(sys.stdout, io.TextIOWrapper):
                sys.stdout.reconfigure(encoding='utf-8')
            console_handler.setFormatter(formatter)
            self.__logger.addHandler(console_handler)

        self.set_level(self.level)

        self.debug = self.__logger.debug
        self.info = self.__logger.info
        self.warning = self.__logger.warning
        self.error = self.__logger.error
        self.critical = self.__logger.critical
        self.log = self.__logger.log
        self.exception = self.__logger.exception

    def set_level(self, level: int | str) -> None:
        if isinstance(level, str):
            level = self.str2log_level(level)
        self.level = level
        self.__logger.setLevel(level)
        for handler in self.__logger.handlers:
            handler.setLevel(level)

    def str2log_level(self, level: str) -> int:
        match level:
            case "NOTSET":
                return NOTSET
            case "DEBUG":
                return DEBUG
            case "INFO":
                return INFO
            case "WARNING":
                return WARNING
            case "ERROR":
                return ERROR
            case "CRITICAL":
                return CRITICAL
            case _:
                msg = f"Invalid log level: {level}"
                raise ValueError(msg)

    def log_progress(self, message: str, level: str = "INFO") -> None:
        """处理进度显示的日志消息
        
        Args:
            message: 日志消息内容
            level: 日志级别，可选值为 "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_method = getattr(self, level.lower(), self.info)

        # 使用对应级别的日志方法记录到文件和UI
        log_method(message)

        # 只在控制台环境下处理进度显示
        if not self.ui_handlers:  # 如果没有UI处理器，说明是控制台环境
            if "进度:" in message:
                # 使用 \r 来覆盖当前行显示进度
                print(f"\r[{timestamp}] [{level}] {message}", end='', flush=True)
                self.last_progress = message
            else:
                # 如果上一条是进度消息，先打印换行
                if self.last_progress:
                    print()
                    self.last_progress = None
                # 其他消息正常打印并换行
                print(f"[{timestamp}] [{level}] {message}")

    def add_handler(self, handler):
        """添加新的日志处理器"""
        handler.setLevel(self.level)
        formatter = logging.Formatter(
            '[%(levelname)s] %(asctime)s - %(message)s')
        handler.setFormatter(formatter)
        self.__logger.addHandler(handler)
        # 保存UI处理器引用
        self.ui_handlers.append(handler)


logger = Logger()