import asyncio
from PySide6.QtCore import QObject, Signal, Slot

class AsyncWorker(QObject):
    """
    A worker that runs an asyncio coroutine in a separate thread.
    It is designed to be moved to a QThread.
    """
    finished = Signal(object)
    error = Signal(Exception)

    def __init__(self, coro, parent=None):
        super().__init__(parent)
        self.coro = coro

    @Slot()
    def run(self):
        """Runs the coroutine using asyncio.run()."""
        try:
            # asyncio.run() automatically manages the event loop
            result = asyncio.run(self.coro)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(e)