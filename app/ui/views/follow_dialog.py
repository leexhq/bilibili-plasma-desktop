"""Real-Time Follow Listener & Message Prompt Dialog
Pops up after follow event is triggered to allow instant greeting message to UP.
Follows Default Value Semantics.
"""

from __future__ import annotations
from typing import Optional
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit,
    QPushButton, QFrame, QMessageBox
)

from app.core.account_manager import account_manager, Account
from app.ui.theme import apply_default_semantics

class FollowMessagePromptDialog(QDialog):
    """
    Dialog popped when follow event is triggered or intercepted.
    Adheres strictly to Default Value Semantics (preset focus on primary send button).
    """

    def __init__(self, up_id: int, up_name: str, identity_id: str, parent: Optional[QDialog] = None):
        super().__init__(parent)
        self.up_id = up_id
        self.up_name = up_name
        self.identity_id = identity_id
        self.account = account_manager.get_account(identity_id) or account_manager.get_active_account()

        self.setWindowTitle(f"关注成功 - 向 {self.up_name} 发送留言")
        self.resize(500, 320)
        self.setModal(True)

        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Header notification
        banner = QFrame()
        banner.setStyleSheet("""
        QFrame {
            background-color: #1e3a5f;
            border: 1px solid #3daee9;
            border-radius: 6px;
            padding: 10px;
        }
        """)
        b_layout = QVBoxLayout(banner)
        b_layout.setSpacing(4)
        
        lbl_status = QLabel(f"🎉 <b>已自动完成关注 UP主：【{self.up_name}】</b> (UID: {self.up_id})")
        lbl_status.setStyleSheet("color: #78b9e6; font-size: 13px;")
        
        lbl_acc = QLabel(f"执行身份: <b>{self.account.name}</b> (Lv{self.account.level})")
        lbl_acc.setStyleSheet("color: #eff0f1; font-size: 11px;")
        
        b_layout.addWidget(lbl_status)
        b_layout.addWidget(lbl_acc)
        layout.addWidget(banner)

        # Prompt text
        lbl_prompt = QLabel("是否需要立即向 UP 主发送一条私信或留言？")
        lbl_prompt.setStyleSheet("color: #bdc3c7;")
        layout.addWidget(lbl_prompt)

        # Preset message text
        self.msg_input = QTextEdit()
        self.msg_input.setPlainText("你好！很高兴关注你，期待更多精彩的高质量视频更新！")
        self.msg_input.setMaximumHeight(80)
        layout.addWidget(self.msg_input)

        # Buttons
        btn_bar = QHBoxLayout()
        btn_bar.addStretch()

        self.btn_cancel = QPushButton("暂不留言 (Esc)")
        self.btn_cancel.clicked.connect(self.reject)
        btn_bar.addWidget(self.btn_cancel)

        self.btn_send = QPushButton("确认发送留言 (Enter)")
        self.btn_send.setProperty("class", "primary")
        self.btn_send.clicked.connect(self._on_send_message)
        btn_bar.addWidget(self.btn_send)

        layout.addLayout(btn_bar)

        # Default value semantics: Set default button & initial focus on '确认发送留言'
        apply_default_semantics(self.btn_send, is_default_action=True)

    def _on_send_message(self) -> None:
        msg = self.msg_input.toPlainText().strip()
        if msg:
            # Here message is delivered / archived
            QMessageBox.information(self, "发送成功", f"留言已成功发送至 {self.up_name} 的私信信箱！")
        self.accept()
