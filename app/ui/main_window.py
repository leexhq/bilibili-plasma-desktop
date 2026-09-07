"""KDE Plasma / Breeze Main Window Architecture
Integrates navigation stack, identity inheritance, passive archiving, and keyboard grid.
"""

from __future__ import annotations
from typing import Optional
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QStackedWidget, QStatusBar,
    QFrame, QComboBox, QApplication
)

from app.core.config import config_instance
from app.core.account_manager import account_manager
from app.core.state_machine import state_machine, PageContext
from app.ui.theme import apply_breeze_theme
from app.ui.keyboard import KeyboardNavigationManager
from app.ui.views.video_view import VideoView
from app.ui.views.up_space_view import UPSpaceView
from app.ui.views.archive_view import PassiveArchiveView
from app.ui.views.account_dialog import AccountManagerDialog
from app.ui.views.command_palette import CommandPaletteDialog
from app.ui.views.follow_dialog import FollowMessagePromptDialog

class BilibiliMainWindow(QMainWindow):
    """
    Main Application Window strictly compliant with KDE Breeze Desktop guidelines.
    Features:
    - Context identity inheritance across page views
    - Zero-overhead passive archiving indicator
    - Global Keyboard-First focus navigation
    - Real-time follow event listening and greeting prompt
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Bilibili - KDE Plasma / Breeze 桌面客户端 [架构实战]")
        self.resize(1400, 900)
        self.setMinimumSize(960, 600)

        self._setup_ui()
        self._setup_keyboard_navigation()
        self._setup_state_machine()
        
        # Load initial video
        self.video_view.load_video("BV1xx411c7mD")

    def _setup_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(8, 8, 8, 8)
        root_layout.setSpacing(6)

        # 1. Top KDE Plasma Toolbar
        toolbar = QFrame()
        toolbar.setStyleSheet("""
        QFrame {
            background-color: #2a2e32;
            border: 1px solid #474d54;
            border-radius: 6px;
            padding: 4px;
        }
        """)
        tb_layout = QHBoxLayout(toolbar)
        tb_layout.setContentsMargins(6, 4, 6, 4)
        tb_layout.setSpacing(10)

        # Navigation History Buttons
        self.btn_back = QPushButton("◀")
        self.btn_back.setToolTip("后退并恢复上一页面身份 (Alt+Left / Esc)")
        self.btn_back.clicked.connect(self._on_navigate_back)
        tb_layout.addWidget(self.btn_back)

        self.btn_forward = QPushButton("▶")
        self.btn_forward.setToolTip("前进 (Alt+Right)")
        self.btn_forward.clicked.connect(self._on_navigate_forward)
        tb_layout.addWidget(self.btn_forward)

        # App Brand & Breadcrumb
        self.breadcrumb_label = QLabel("<b>Bilibili Plasma</b> > 视频播放")
        self.breadcrumb_label.setStyleSheet("color: #eff0f1; font-size: 13px;")
        tb_layout.addWidget(self.breadcrumb_label)

        # Search Bar / Command Palette Launcher
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("🔍 按 / 或 Ctrl+K 呼出快速指令与搜索...")
        self.search_box.setFixedWidth(280)
        self.search_box.returnPressed.connect(self._on_search_entered)
        tb_layout.addWidget(self.search_box)

        tb_layout.addStretch()

        # Passive Archiving Live Pulse Badge
        self.archive_badge = QLabel("📦 被动归档: 活跃 (0开销)")
        self.archive_badge.setStyleSheet("""
        background-color: #1e3a5f;
        color: #78b9e6;
        border: 1px solid #3daee9;
        border-radius: 4px;
        padding: 4px 8px;
        font-size: 11px;
        font-weight: bold;
        """)
        tb_layout.addWidget(self.archive_badge)

        # Active Identity Selector Dropdown
        self.identity_selector = QComboBox()
        self.identity_selector.setToolTip("当前全局活跃身份 (页面跳转自动继承)")
        self._refresh_identity_selector()
        self.identity_selector.currentIndexChanged.connect(self._on_identity_dropdown_changed)
        tb_layout.addWidget(self.identity_selector)

        # Multi-Account Manager Button
        self.btn_account = QPushButton("👤 多账号 (a)")
        self.btn_account.clicked.connect(self.open_account_manager)
        tb_layout.addWidget(self.btn_account)

        # Archive View Button
        self.btn_archive = QPushButton("📦 归档库 (p)")
        self.btn_archive.clicked.connect(self.open_archive_view)
        tb_layout.addWidget(self.btn_archive)

        # Shortcut Help Button
        self.btn_help = QPushButton("⌨ 快捷键 (?)")
        self.btn_help.clicked.connect(self.show_shortcuts_help)
        tb_layout.addWidget(self.btn_help)

        root_layout.addWidget(toolbar)

        # 2. Main Stacked Pages
        self.stacked_widget = QStackedWidget()
        
        # Page 0: Video View
        self.video_view = VideoView()
        self.video_view.navigate_video.connect(self._on_navigate_to_video)
        self.video_view.navigate_up_space.connect(self._on_navigate_to_up_space)
        self.stacked_widget.addWidget(self.video_view)

        # Page 1: UP Space Deep View
        self.up_space_view = UPSpaceView()
        self.up_space_view.back_requested.connect(self._on_navigate_back)
        self.stacked_widget.addWidget(self.up_space_view)

        # Page 2: Passive Archive Inspector
        self.archive_view = PassiveArchiveView()
        self.archive_view.back_requested.connect(self._on_navigate_back)
        self.stacked_widget.addWidget(self.archive_view)

        root_layout.addWidget(self.stacked_widget)

        # 3. Status Bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("全键盘模式就绪: [j/k] 滚动  [Space] 播放/暂停  [d] 弹幕  [c] 评论  [u] UP主空间  [a] 账户管理  [?] 帮助")

    def _setup_keyboard_navigation(self) -> None:
        self.keyboard_mgr = KeyboardNavigationManager(self)
        QApplication.instance().installEventFilter(self.keyboard_mgr)

        self.keyboard_mgr.register_panel("player", self.video_view)
        self.keyboard_mgr.register_panel("comments", self.video_view.comment_view)
        self.keyboard_mgr.register_panel("recommendations", self.video_view.rcmd_scroll)

        # Connect actions
        self.keyboard_mgr.action_triggered.connect(self._handle_keyboard_action)

    def _setup_state_machine(self) -> None:
        state_machine.add_navigation_listener(self._on_state_machine_nav)
        state_machine.add_identity_listener(self._on_state_machine_identity_changed)
        state_machine.add_follow_listener(self._on_follow_event_captured)

    def _refresh_identity_selector(self) -> None:
        self.identity_selector.blockSignals(True)
        self.identity_selector.clear()
        for acc in account_manager.list_all_accounts():
            self.identity_selector.addItem(f"👤 {acc.name}", acc.id)

        curr_id = state_machine.current_identity_id
        for i in range(self.identity_selector.count()):
            if self.identity_selector.itemData(i) == curr_id:
                self.identity_selector.setCurrentIndex(i)
                break
        self.identity_selector.blockSignals(False)

    def _on_identity_dropdown_changed(self, index: int) -> None:
        acc_id = self.identity_selector.itemData(index)
        if acc_id:
            state_machine.switch_page_identity(acc_id)

    def _on_navigate_to_video(self, bvid: str) -> None:
        # Context inheritance: automatically inherits current page active identity
        state_machine.navigate_to("video", bvid)
        self.video_view.load_video(bvid)
        self.stacked_widget.setCurrentIndex(0)

    def _on_navigate_to_up_space(self, up_id: int, up_name: str) -> None:
        # Context inheritance: automatically inherits current page active identity
        state_machine.navigate_to("up_space", str(up_id), params={"up_name": up_name})
        self.up_space_view.load_up_profile(up_id, up_name)
        self.stacked_widget.setCurrentIndex(1)

    def _on_navigate_back(self) -> None:
        prev_ctx = state_machine.navigate_back()
        if prev_ctx:
            self._apply_page_context(prev_ctx)

    def _on_navigate_forward(self) -> None:
        fwd_ctx = state_machine.navigate_forward()
        if fwd_ctx:
            self._apply_page_context(fwd_ctx)

    def _apply_page_context(self, ctx: PageContext) -> None:
        if ctx.page_type == "video":
            self.video_view.load_video(ctx.target_id)
            self.stacked_widget.setCurrentIndex(0)
        elif ctx.page_type == "up_space":
            up_name = ctx.params.get("up_name", "UP主空间")
            self.up_space_view.load_up_profile(int(ctx.target_id), up_name)
            self.stacked_widget.setCurrentIndex(1)
        elif ctx.page_type == "archive":
            self.archive_view.refresh_data()
            self.stacked_widget.setCurrentIndex(2)

    def _on_state_machine_nav(self, ctx: PageContext) -> None:
        self.breadcrumb_label.setText(f"<b>Bilibili Plasma</b> > {ctx.page_type.upper()} ({ctx.target_id})")
        self._refresh_identity_selector()

    def _on_state_machine_identity_changed(self, identity_id: str, ctx: PageContext) -> None:
        self._refresh_identity_selector()
        acc = account_manager.get_account(identity_id)
        if acc:
            self.status_bar.showMessage(f"身份已切换为: {acc.name} (已绑定至当前页面上下文)", 4000)

    def _on_follow_event_captured(self, identity_id: str, up_id: int, up_name: str, is_following: bool) -> None:
        """
        Real-time follow listener hook. Pops up message dialog if config permits.
        """
        if is_following and config_instance.get("identity.auto_follow_message_prompt", True):
            dialog = FollowMessagePromptDialog(up_id, up_name, identity_id, self)
            dialog.exec()

    def _handle_keyboard_action(self, action: str) -> None:
        if action == "toggle_play":
            self.video_view.toggle_play()
        elif action == "toggle_danmaku":
            self.video_view.toggle_danmaku()
        elif action == "toggle_fullscreen":
            self.video_view.toggle_fullscreen()
        elif action == "focus_comment_input":
            self.video_view.comment_view.focus_input()
        elif action == "go_up_space":
            if self.video_view.video_info:
                self._on_navigate_to_up_space(self.video_view.video_info.up_id, self.video_view.video_info.up_name)
        elif action == "open_account_manager":
            self.open_account_manager()
        elif action == "open_archive_view":
            self.open_archive_view()
        elif action == "open_command_palette" or action == "focus_search":
            self.open_command_palette()

    def _on_search_entered(self) -> None:
        query = self.search_box.text().strip()
        if query:
            # Load video by bvid or show results
            if query.upper().startswith("BV"):
                self._on_navigate_to_video(query)
            else:
                self.open_command_palette()

    def open_account_manager(self) -> None:
        dialog = AccountManagerDialog(self)
        dialog.exec()
        self._refresh_identity_selector()

    def open_archive_view(self) -> None:
        state_machine.navigate_to("archive", "local_db")
        self.archive_view.refresh_data()
        self.stacked_widget.setCurrentIndex(2)

    def open_command_palette(self) -> None:
        dialog = CommandPaletteDialog(self)
        dialog.command_executed.connect(self._handle_keyboard_action)
        dialog.exec()

    def show_shortcuts_help(self) -> None:
        self.keyboard_mgr.show_shortcuts_help()
