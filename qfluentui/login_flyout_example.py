from PySide6.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget
from qfluentwidgets import FluentIcon, Flyout, FlyoutAnimationType

from login import LoginPanel


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("登录示例")
        self.resize(800, 600)
        
        # 创建中央窗口部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建布局
        layout = QVBoxLayout(central_widget)
        
        # 创建登录按钮
        self.login_button = QPushButton("点击登录", self)
        self.login_button.clicked.connect(self.show_login_flyout)
        layout.addWidget(self.login_button)
    
    def show_login_flyout(self):
        # 创建登录面板
        login_panel = LoginPanel(self)
        
        # 连接登录成功信号
        login_panel.login_succeeded.connect(self.on_login_success)
        
        # 创建 Flyout
        flyout = Flyout.make(
            view=login_panel,
            target=self.login_button,
            parent=self
        )
        
        # 设置动画类型
        # flyout.setAnimationType(FlyoutAnimationType.PULL_UP)
        
        # 显示 Flyout
        flyout.show()
    
    def on_login_success(self, credential):
        print(f"登录成功！用户ID: {credential.musicid}")
        # 这里可以添加登录成功后的逻辑，比如更新UI状态等


if __name__ == "__main__":
    import sys
    
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())