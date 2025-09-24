import asyncio
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget
from qfluentwidgets import (
    TitleLabel,
    SubtitleLabel,
    BodyLabel,
    ProgressRing,
    FlyoutViewBase,
    PillPushButton,
    Flyout,
    FluentIcon,
)

from qqmusic_api.login import get_qrcode, check_qrcode, QRLoginType, QRCodeLoginEvents
from qqmusic_api.utils.credential import Credential
from api.qqmusic import QQMusicAPI

# 持有正在运行的线程，避免窗口销毁时线程对象被提前析构
RUNNING_THREADS = set()


class LoginWorker(QThread):
    """Worker thread to handle the QR code login process."""

    qr_ready = Signal(bytes)
    status_updated = Signal(str)
    login_success = Signal(Credential)
    login_failed = Signal(str)

    def __init__(self, login_type=QRLoginType.QQ, parent=None):
        super().__init__(parent)
        self.login_type = login_type
        self._is_running = True

    def stop(self):
        """Politely ask the thread to stop."""
        self._is_running = False

    def run(self):
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.login_flow())
        except Exception as e:
            if self._is_running:
                self.login_failed.emit(str(e))

    async def login_flow(self):
        login_type_name = "QQ" if self.login_type == QRLoginType.QQ else "微信"
        self.status_updated.emit(f"正在生成{login_type_name}二维码...")
        try:
            qr = await get_qrcode(self.login_type)
            if not self._is_running:
                return
            self.qr_ready.emit(qr.data)
        except Exception as e:
            if self._is_running:
                self.login_failed.emit(f"生成二维码失败: {e}")
            return

        max_attempts = 60  # ~2 minutes polling
        for _ in range(max_attempts):
            if not self._is_running:
                return

            try:
                event, credential = await check_qrcode(qr)
            except Exception as e:
                if self._is_running:
                    self.login_failed.emit(f"检查状态失败: {e}")
                return

            if not self._is_running:
                return

            if event == QRCodeLoginEvents.DONE:
                self.status_updated.emit("登录成功！")
                self.login_success.emit(credential)
                return
            elif event == QRCodeLoginEvents.TIMEOUT:
                self.login_failed.emit("二维码已过期，请重新登录")
                return
            elif event == QRCodeLoginEvents.REFUSE:
                self.login_failed.emit("用户拒绝登录")
                return
            elif event == QRCodeLoginEvents.SCAN:
                self.status_updated.emit(f"请使用手机{login_type_name}扫描二维码")
            elif event == QRCodeLoginEvents.CONF:
                self.status_updated.emit("已扫码，请在手机上确认登录")

            await asyncio.sleep(2)

        if self._is_running:
            self.login_failed.emit("登录超时，请重试")


class LoginPanel(FlyoutViewBase):
    """登录面板（在 Flyout 中展示）。"""

    login_succeeded = Signal(Credential)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.vBoxLayout = QVBoxLayout(self)
        self.titleLabel = TitleLabel("使用手机 QQ/微信 扫码登录", self)
        self.titleLabel.setWordWrap(True)

        # --- QR Code Area ---
        self.qrWidget = QWidget(self)
        self.qrStackedWidget = QStackedWidget(self.qrWidget)
        self.qrCodeLabel = BodyLabel(self)
        self.progressRing = ProgressRing(self)

        self.statusLabel = SubtitleLabel("正在生成二维码...", self)

        # 登录方式选择按钮
        self.buttonLayout = QHBoxLayout()
        self.qqButton = PillPushButton(FluentIcon.ACCEPT.icon(), "QQ登录", self)
        self.wxButton = PillPushButton(FluentIcon.WIFI.icon(), "微信登录", self)
        self.qqButton.setCheckable(True)
        self.wxButton.setCheckable(True)
        self.qqButton.setChecked(True)

        self.buttonLayout.addWidget(self.qqButton)
        self.buttonLayout.addWidget(self.wxButton)
        self.buttonLayout.setSpacing(10)

        self.worker = None
        self.current_login_type = QRLoginType.QQ
        self.__init_widgets()
        self.__connect_signals()
        try:
            self.destroyed.connect(self._on_destroyed)
        except Exception:
            pass
        self.start_login()  # 初始化后自动开始登录

    def __init_widgets(self):
        self.setFixedSize(340, 480)
        self.vBoxLayout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.vBoxLayout.setContentsMargins(24, 24, 24, 24)

        # QR Code Area
        self.qrWidget.setFixedSize(240, 240)
        qr_layout = QVBoxLayout(self.qrWidget)
        qr_layout.setContentsMargins(0, 0, 0, 0)
        qr_layout.addWidget(self.qrStackedWidget)

        self.qrStackedWidget.addWidget(self.progressRing)
        self.qrStackedWidget.addWidget(self.qrCodeLabel)

        self.qrCodeLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.qrCodeLabel.setStyleSheet(
            "background-color: white; border: 1px solid #e0e0e0; border-radius: 10px;"
        )
        self.progressRing.setFixedSize(70, 70)

        # Main Layout
        self.vBoxLayout.addWidget(self.titleLabel, 0, Qt.AlignmentFlag.AlignCenter)
        self.vBoxLayout.addSpacing(16)
        self.vBoxLayout.addWidget(self.qrWidget, 0, Qt.AlignmentFlag.AlignCenter)
        self.vBoxLayout.addSpacing(16)
        self.vBoxLayout.addLayout(self.buttonLayout)
        self.vBoxLayout.addSpacing(16)
        self.vBoxLayout.addWidget(self.statusLabel, 0, Qt.AlignmentFlag.AlignCenter)

    def __connect_signals(self):
        self.qqButton.clicked.connect(lambda: self.on_login_type_changed(QRLoginType.QQ))
        self.wxButton.clicked.connect(lambda: self.on_login_type_changed(QRLoginType.WX))

    def on_login_type_changed(self, login_type):
        # If the button is already active, do nothing
        if login_type == self.current_login_type:
            if login_type == QRLoginType.QQ:
                self.qqButton.setChecked(True)
            else:
                self.wxButton.setChecked(True)
            return

        # Stop current process
        if self.worker and self.worker.isRunning():
            # 仅请求停止，不阻塞等待，避免 UI 卡顿
            self.worker.stop()

        # Update login type and button states
        self.current_login_type = login_type
        if login_type == QRLoginType.QQ:
            self.qqButton.setChecked(True)
            self.wxButton.setChecked(False)
            self.titleLabel.setText("使用手机 QQ 扫码登录")
        else:
            self.qqButton.setChecked(False)
            self.wxButton.setChecked(True)
            self.titleLabel.setText("使用手机 微信 扫码登录")

        # Reset status
        self.qrCodeLabel.clear()
        self.statusLabel.setText("正在生成二维码...")
        self.qrStackedWidget.setCurrentWidget(self.progressRing)

        # Start new login flow
        self.start_login()

    def start_login(self):
        self.qrStackedWidget.setCurrentWidget(self.progressRing)
        # 不把线程设为 Panel 的子对象，避免 Flyout 关闭时随父对象被销毁
        self.worker = LoginWorker(self.current_login_type, None)
        self.worker.qr_ready.connect(self.show_qr_code)
        self.worker.status_updated.connect(self.update_status)
        self.worker.login_success.connect(self.on_login_success)
        self.worker.login_failed.connect(self.on_login_failure)
        # 注册全局引用，线程结束后清理
        RUNNING_THREADS.add(self.worker)
        w = self.worker
        def _cleanup():
            RUNNING_THREADS.discard(w)
        w.finished.connect(_cleanup)
        self.worker.start()

    def show_qr_code(self, qr_data: bytes):
        pixmap = QPixmap()
        pixmap.loadFromData(qr_data)
        self.qrCodeLabel.setPixmap(
            pixmap.scaled(
                220,
                220,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )
        self.qrStackedWidget.setCurrentWidget(self.qrCodeLabel)

    def update_status(self, text: str):
        self.statusLabel.setText(text)

    def on_login_success(self, credential: Credential):
        # persist credential immediately
        try:
            api = QQMusicAPI()
            api.save_credential(credential)
        except Exception:
            pass
        # emit success so outer code can update UI
        self.login_succeeded.emit(credential)
        # close only the flyout that contains this view to avoid closing main window
        self._close_parent_flyout()

    def on_login_failure(self, reason: str):
        self.statusLabel.setText(f"登录失败: {reason}")
        self.qrCodeLabel.setText("加载失败")
        self.qrStackedWidget.setCurrentWidget(self.qrCodeLabel)

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            # 仅请求停止，不阻塞等待，避免 UI 卡顿
            self.worker.stop()
        super().closeEvent(event)

    def hideEvent(self, event):
        # Flyout 点击外部时会触发隐藏，这里也请求停止线程
        if self.worker and self.worker.isRunning():
            self.worker.stop()
        super().hideEvent(event)

    def _on_destroyed(self, _obj=None):
        # 保底：对象销毁前尝试请求停止
        if self.worker and self.worker.isRunning():
            self.worker.stop()

    def _close_parent_flyout(self):
        """Find and close parent Flyout only (avoid closing the main window)."""
        p = self.parentWidget()
        while p is not None:
            if isinstance(p, Flyout):
                p.close()
                return
            p = p.parentWidget()


