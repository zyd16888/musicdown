import io
import logging
import os
import sys
import time
from logging import CRITICAL, DEBUG, ERROR, INFO, NOTSET, WARNING, LogRecord



log_file = os.path.join("logs/", f'{time.strftime("%Y.%m.%d", time.localtime())}.log')
if not os.path.exists(os.path.dirname(log_file)):
    os.makedirs(os.path.dirname(log_file))

class Logger:
    def __init__(self) -> None:
        self.name = 'LDDC'
        self.__logger = logging.getLogger(self.name)
        self.level = self.str2log_level("DEBUG")

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


logger = Logger()
