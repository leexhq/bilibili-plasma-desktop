"""Keyboard-First Navigation System & Event Filter
Implements full Vim-like and Tab/Arrow focus navigation across the entire client.
"""

from __future__ import annotations
from typing import Optional, Dict, Callable, List
from PySide6.QtCore import QObject, QEvent, Qt, Signal
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import (
    QWidget, QLineEdit, QTextEdit, QPlainTextEdit,
    QListWidget, QTreeWidget, QScrollArea, QDialog,
    QVBoxLayout, QLabel, QHBoxLayout, QPushButton, QTableWidget
)

class KeyboardShortcutHelpDialog(QDialog):
    """Breeze-styled Keyboard Shortcut Reference Overlay (? or F1)"""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("全键盘操作与快捷键指南 (Keyboard Navigation)")
        self.resize(640, 520)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        header = QLabel("<h2>⌨ 全键盘导航与快捷键体系 (Vim-Like & Grid)</h2>")
        desc = QLabel("本客户端遵循 Keyboard-First 规范，无需鼠标即可访问全部功能与视图。")
        desc.setStyleSheet("color: #bdc3c7;")
        layout.addWidget(header)
        layout.addWidget(desc)

        table = QTableWidget(14, 3)
        table.setHorizontalHeaderLabels(["按键 / 组合键", "操作上下文", "说明"])
        table.horizontalHeader().setStretchLastSection(True)
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectRows)

        shortcuts = [
            ("j / Down", "全局列表/页面", "向下滚动 / 移动至下一项评论或推荐视频"),
            ("k / Up", "全局列表/页面", "向上滚动 / 移动至上一项评论或推荐视频"),
            ("h / Left", "主导航网格", "向左切换面板焦点 (侧边栏 / 播放器)"),
            ("l / Right", "主导航网格", "向右切换面板焦点 (播放器 / 评论与推荐)"),
            ("g", "滚动区域", "直接跳转到页面/列表顶部 (Home)"),
            ("G (Shift+g)", "滚动区域", "直接跳转到页面/列表底部 (End)"),
            ("Space", "播放器", "播放 / 暂停视频"),
            ("f", "播放器", "进入 / 退出全屏播放"),
            ("m", "播放器", "静音 / 取消静音"),
            ("d", "弹幕引擎", "开启 / 关闭弹幕渲染图层"),
            ("c", "交互系统", "快速跳转到当前视频的评论输入框并进入编辑态"),
            ("u", "身份上下文", "跳转到当前视频 UP 主空间 (深度聚合多身份视图)"),
            ("a", "多身份管理", "弹出多账号管理与 SESSDATA / Cookie 切换弹窗"),
            ("? / F1", "帮助系统", "呼出本键盘快捷键帮助手册 (Esc 退出)"),
        ]

        for row, (key, ctx, note) in enumerate(shortcuts):
            from PySide6.QtWidgets import QTableWidgetItem
            table.setItem(row, 0, QTableWidgetItem(key))
            table.setItem(row, 1, QTableWidgetItem(ctx))
            table.setItem(row, 2, QTableWidgetItem(note))

        layout.addWidget(table)

        btn_box = QHBoxLayout()
        btn_close = QPushButton("关闭 (Esc / Enter)")
        btn_close.clicked.connect(self.accept)
        btn_close.setDefault(True)
        btn_close.setFocus()
        btn_box.addStretch()
        btn_box.addWidget(btn_close)
        layout.addLayout(btn_box)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() in (Qt.Key.Key_Escape, Qt.Key.Key_Return):
            self.accept()
        else:
            super().keyPressEvent(event)


class KeyboardNavigationManager(QObject):
    """
    Global Event Filter capturing keyboard events application-wide.
    Provides seamless switching between 'Normal Mode' and 'Input Mode'.
    """

    action_triggered = Signal(str)

    def __init__(self, main_window: QWidget):
        super().__init__()
        self.main_window = main_window
        self.panels: Dict[str, QWidget] = {}
        self.active_panel_name: str = "player"

    def register_panel(self, name: str, widget: QWidget) -> None:
        self.panels[name] = widget

    def set_active_panel(self, name: str) -> None:
        if name in self.panels:
            self.active_panel_name = name
            widget = self.panels[name]
            widget.setFocus()

    def _is_input_widget(self, widget: Optional[QWidget]) -> bool:
        if widget is None:
            return False
        return isinstance(widget, (QLineEdit, QTextEdit, QPlainTextEdit))

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if event.type() == QEvent.Type.KeyPress:
            key_event: QKeyEvent = event
            key = key_event.key()
            text = key_event.text()
            modifiers = key_event.modifiers()

            focused = self.main_window.focusWidget()
            is_input = self._is_input_widget(focused)

            # In Input Mode: Allow Esc to return focus to normal navigation
            if is_input:
                if key == Qt.Key.Key_Escape:
                    focused.clearFocus()
                    self.main_window.setFocus()
                    return True
                # Let regular typing continue untouched
                return False

            # In Normal Mode: Handle Vim keys & Shortcuts
            if modifiers & Qt.KeyboardModifier.ControlModifier:
                if key == Qt.Key.Key_K:
                    self.action_triggered.emit("open_command_palette")
                    return True
                return False

            # Vim-like Navigation
            if key == Qt.Key.Key_J or key == Qt.Key.Key_Down:
                self._handle_scroll(down=True)
                return True
            elif key == Qt.Key.Key_K or key == Qt.Key.Key_Up:
                self._handle_scroll(down=False)
                return True
            elif key == Qt.Key.Key_H or key == Qt.Key.Key_Left:
                self._switch_panel_relative(-1)
                return True
            elif key == Qt.Key.Key_L or key == Qt.Key.Key_Right:
                self._switch_panel_relative(1)
                return True
            elif text == "g":
                self._handle_jump_edge(top=True)
                return True
            elif text == "G":
                self._handle_jump_edge(top=False)
                return True
            elif key == Qt.Key.Key_Space:
                self.action_triggered.emit("toggle_play")
                return True
            elif text == "f":
                self.action_triggered.emit("toggle_fullscreen")
                return True
            elif text == "m":
                self.action_triggered.emit("toggle_mute")
                return True
            elif text == "d":
                self.action_triggered.emit("toggle_danmaku")
                return True
            elif text == "c":
                self.action_triggered.emit("focus_comment_input")
                return True
            elif text == "u":
                self.action_triggered.emit("go_up_space")
                return True
            elif text == "a":
                self.action_triggered.emit("open_account_manager")
                return True
            elif text == "p":
                self.action_triggered.emit("open_archive_view")
                return True
            elif text == "/" or key == Qt.Key.Key_Slash:
                self.action_triggered.emit("focus_search")
                return True
            elif text == "?" or key == Qt.Key.Key_F1:
                self.show_shortcuts_help()
                return True

        return super().eventFilter(watched, event)

    def _handle_scroll(self, down: bool) -> None:
        focused = self.main_window.focusWidget()
        if isinstance(focused, (QListWidget, QTreeWidget)):
            cur = focused.currentRow() if isinstance(focused, QListWidget) else 0
            if isinstance(focused, QListWidget):
                next_row = min(focused.count() - 1, cur + 1) if down else max(0, cur - 1)
                focused.setCurrentRow(next_row)
            return

        # Fallback to general scroll areas
        scroll_area = self.main_window.findChild(QScrollArea)
        if scroll_area:
            bar = scroll_area.verticalScrollBar()
            step = 80
            bar.setValue(bar.value() + (step if down else -step))

    def _handle_jump_edge(self, top: bool) -> None:
        focused = self.main_window.focusWidget()
        if isinstance(focused, QListWidget):
            focused.setCurrentRow(0 if top else focused.count() - 1)
            return
        scroll_area = self.main_window.findChild(QScrollArea)
        if scroll_area:
            bar = scroll_area.verticalScrollBar()
            bar.setValue(bar.minimum() if top else bar.maximum())

    def _switch_panel_relative(self, direction: int) -> None:
        keys = list(self.panels.keys())
        if not keys:
            return
        try:
            curr_idx = keys.index(self.active_panel_name)
        except ValueError:
            curr_idx = 0
        new_idx = (curr_idx + direction) % len(keys)
        self.set_active_panel(keys[new_idx])

    def show_shortcuts_help(self) -> None:
        dialog = KeyboardShortcutHelpDialog(self.main_window)
        dialog.exec()
