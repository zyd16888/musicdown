import sys
from PyQt6.QtWidgets import QApplication
from ui.mainui import QQMusicDownloaderGUI

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = QQMusicDownloaderGUI()
    window.show()
    sys.exit(app.exec())
