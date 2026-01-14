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
from api.adapter import MusicAdapter
from qfluentui.worker import AsyncWorker
from PySide6.QtCore import QThread

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
        # 使用较小字号并禁用换行，保证标题单行美观
        self.titleLabel = SubtitleLabel("使用手机 QQ/微信 扫码登录", self)
        self.titleLabel.setWordWrap(False)
        self.titleLabel.setAlignment(Qt.AlignCenter)
        # 统一控制字号，避免默认 TitleLabel 字号过大导致换行
        self.titleLabel.setStyleSheet("font-size: 14px;")
        # 会员状态标签（普通用户/绿钻/豪华绿钻）
        self.vipLabel = BodyLabel("", self)
        self.vipLabel.setAlignment(Qt.AlignCenter)
        self.vipLabel.setStyleSheet("color: #888; font-size: 12px;")

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
        self.vBoxLayout.addWidget(self.vipLabel, 0, Qt.AlignmentFlag.AlignCenter)
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
        # 推断会员状态并展示
        try:
            label = self._infer_membership_label(credential)
            if label:
                self.vipLabel.setText(f"会员：{label}")
        except Exception:
            pass
        # 尝试从接口拉取更权威的用户信息，更新标签
        self._fetch_membership_async()
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

    # ---- helpers ----
    def _infer_membership_label(self, credential: Credential) -> str:
        """根据 credential.extra_fields 推断会员等级（尽量稳健）。"""
        data = getattr(credential, 'extra_fields', {}) or {}
        return self._detect_vip_from_dict(data)

    # ---- detection utils ----
    def _detect_vip_from_dict(self, data: dict) -> str:
        """在未知字段名差异时，通过扁平化 + 模糊匹配判断 VIP/SVIP。

        规则：
        - 先判定 SVIP：键名包含 'svip' 或 'supervip'，或在典型集合中；且值为真/数值>0/字符串数值>0/字符串'true'
        - 再判定 VIP：键名包含 'vip'（但不包含 'svip'），或在典型集合中；且值同上
        - 其他：普通用户
        """
        flat = {}
        def _flatten(d: dict, p: str = ""):
            for k, v in (d or {}).items():
                key = (p + "." + str(k)) if p else str(k)
                if isinstance(v, dict):
                    _flatten(v, key)
                else:
                    flat[key.lower()] = v
        _flatten(data)

        def _truthy(v):
            if isinstance(v, bool):
                return v
            if isinstance(v, (int, float)):
                return v > 0
            if isinstance(v, str):
                vs = v.strip().lower()
                if vs.isdigit():
                    return int(vs) > 0
                return vs in ("true", "yes", "vip", "svip")
            return False

        # 典型键集合（全部转小写）
        svip_keys = {"issvip", "is_svip", "svip", "supervip", "sviplevel", "viptype2"}
        vip_keys = {"isvip", "is_vip", "vip", "vipflag", "viplevel", "paymonth", "viptype"}
        blacklist_substr = ("openid", "appid")

        # 先检测 SVIP
        for k, v in flat.items():
            if any(b in k for b in blacklist_substr):
                continue
            if ("svip" in k or "supervip" in k or k in svip_keys) and _truthy(v):
                return "豪华绿钻"

        # 再检测 VIP（排除包含 svip 的键）
        for k, v in flat.items():
            if any(b in k for b in blacklist_substr):
                continue
            if ("vip" in k and "svip" not in k) or (k in vip_keys):
                if _truthy(v):
                    return "绿钻"

        return "普通用户"

    def _fetch_membership_async(self):
        thread = QThread()
        worker = AsyncWorker()
        worker.moveToThread(thread)
        class _Task:
            def __init__(self, c):
                self.coro = c
        async def _coro():
            try:
                adapter = MusicAdapter()
                return await adapter.get_login_user_info()
            except Exception:
                return {}
        def _on_finished(_task, data: dict):
            try:
                if isinstance(data, dict):
                    label = self._detect_vip_from_dict(data)
                    self.vipLabel.setText(f'会员：{label}')
                    # 若仍无法判定，辅助输出可疑键到日志，便于调整映射
                    if label == '普通用户':
                        try:
                            from utils.logger import logger
                            keys = []
                            def _collect(d, p=""):
                                for k, v in (d or {}).items():
                                    key = (p + "." + str(k)) if p else str(k)
                                    if isinstance(v, dict):
                                        _collect(v, key)
                                    else:
                                        kl = key.lower()
                                        if ('vip' in kl) or ('svip' in kl):
                                            keys.append(f"{key}={v}")
                            _collect(data)
                            if keys:
                                logger.info("LoginUserInfo VIP-related keys: " + ", ".join(keys)[:500])
                            else:
                                logger.info("LoginUserInfo keys: " + ", ".join(list(data.keys()))[:500])
                        except Exception:
                            pass
            finally:
                thread.quit()
                worker.deleteLater()
        def _on_failed(_task, _e):
            thread.quit()
            worker.deleteLater()
        worker.finished.connect(_on_finished)
        worker.failed.connect(_on_failed)
        thread.started.connect(lambda: worker.run(_Task(_coro())))
        thread.finished.connect(thread.deleteLater)
        thread.start()


