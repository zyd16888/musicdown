import asyncio
from PySide6.QtCore import QObject, Signal, Slot

class AsyncWorker(QObject):
    """ A reusable worker for running asyncio coroutines. """
    finished = Signal(object, object) # task, result
    failed = Signal(object, Exception)   # task, exception
    start = Signal(object)               # task

    def __init__(self, parent=None):
        super().__init__(parent)
        self.start.connect(self.run)
        self._is_busy = False

    @Slot(object)
    def run(self, task):
        if self._is_busy:
            return

        self._is_busy = True
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(task.coro)
            self.finished.emit(task, result)
        except Exception as e:
            self.failed.emit(task, e)
        finally:
            self._is_busy = False
