"""KDE KRunner / Vim-Style Command Palette
Keyboard-first command launcher invoked via '/' or 'Ctrl+K'.
"""

from __future__ import annotations
from typing import Optional, List, Tuple, Callable
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLineEdit, QListWidget, QListWidgetItem,
    QLabel
)

from app.ui.theme import apply_default_semantics

class CommandPaletteDialog(QDialog):
    """
    Lightweight popup modal for quick command execution and navigation.
    Adheres strictly to Keyboard-First & Default Value Semantics.
    """

    command_executed = Signal(str)

    def __init__(self, parent: Optional[QDialog] = None):
        super().__init__(parent)
        self.setWindowTitle("快捷指令与动作面板 (KRunner / Command Palette)")
        self.resize(520, 320)
        self.setModal(True)
        # Frameless or clean dialog style
        self.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)

        self.commands: List[Tuple[str, str, str]] = [
            ("switch_account", "👤 切换操作身份 (Account Manager)", "打开多账号管理弹窗，支持 Cookie / SESSDATA 导入"),
            ("view_archive", "📦 打开本地被动数据归档库 (Archive Inspector)", "查看网络层被动截获并存盘的 SQLite 视频与评论库"),
            ("go_up_space", "👥 查看当前 UP 主空间 (UP Space Deep View)", "聚合展示所有登录身份的关注状态与时间戳"),
            ("toggle_danmaku", "💬 开启 / 关闭弹幕图层 (Toggle Danmaku)", "切换普通弹幕、Mode 7 及 BAS 弹幕渲染"),
            ("focus_comment", "✍ 跳转到评论输入框 (Comment Input)", "进入评论区直接发表评论 (支持身份隔离选择)"),
            ("show_shortcuts", "⌨ 显示全键盘快捷键指南 (Keyboard Help)", "查看完整 Vim-like 及 Tab 网格键位映射表"),
            ("toggle_play", "⏯ 播放 / 暂停视频 (Play / Pause)", "切换当前视频流播放状态"),
        ]

        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        self.setStyleSheet("""
        QDialog {
            background-color: #232629;
            border: 2px solid #3daee9;
            border-radius: 8px;
        }
        """)

        header = QLabel("⚡ 快速指令 (输入关键词过滤，Enter 执行，Esc 退出)")
        header.setStyleSheet("color: #78b9e6; font-weight: bold; font-size: 11px;")
        layout.addWidget(header)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("输入操作名称或指令...")
        self.search_input.textChanged.connect(self._filter_commands)
        layout.addWidget(self.search_input)

        self.cmd_list = QListWidget()
        self.cmd_list.setStyleSheet("font-size: 13px;")
        self.cmd_list.itemActivated.connect(self._on_item_activated)
        layout.addWidget(self.cmd_list)

        self._populate_list(self.commands)

        # Default value semantics: Focus search bar, select first item
        apply_default_semantics(self.search_input)
        if self.cmd_list.count() > 0:
            self.cmd_list.setCurrentRow(0)

    def _populate_list(self, items: List[Tuple[str, str, str]]) -> None:
        self.cmd_list.clear()
        for cmd_id, label, desc in items:
            item = QListWidgetItem(f"{label}  -  {desc}")
            item.setData(Qt.ItemDataRole.UserRole, cmd_id)
            self.cmd_list.addItem(item)
        if self.cmd_list.count() > 0:
            self.cmd_list.setCurrentRow(0)

    def _filter_commands(self, text: str) -> None:
        query = text.strip().lower()
        if not query:
            self._populate_list(self.commands)
            return

        filtered = [
            (cid, lbl, desc) for cid, lbl, desc in self.commands
            if query in lbl.lower() or query in desc.lower() or query in cid.lower()
        ]
        self._populate_list(filtered)

    def _on_item_activated(self, item: QListWidgetItem) -> None:
        cmd_id = item.data(Qt.ItemDataRole.UserRole)
        self.command_executed.emit(cmd_id)
        self.accept()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        key = event.key()
        if key == Qt.Key.Key_Escape:
            self.reject()
        elif key == Qt.Key.Key_Down:
            cur = self.cmd_list.currentRow()
            self.cmd_list.setCurrentRow(min(self.cmd_list.count() - 1, cur + 1))
        elif key == Qt.Key.Key_Up:
            cur = self.cmd_list.currentRow()
            self.cmd_list.setCurrentRow(max(0, cur - 1))
        elif key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            item = self.cmd_list.currentItem()
            if item:
                self._on_item_activated(item)
        else:
            super().keyPressEvent(event)
