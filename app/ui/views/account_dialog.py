"""Multi-Account Identity Manager Dialog
Supports SESSDATA / Cookie quick import and switching with Default Value Semantics.
"""

from __future__ import annotations
from typing import Optional
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QTextEdit, QLineEdit, QGroupBox,
    QMessageBox
)

from app.core.account_manager import account_manager, Account
from app.core.state_machine import state_machine
from app.ui.theme import apply_default_semantics

class AccountManagerDialog(QDialog):
    """
    Multi-Account Modal strictly adhering to Default Value Semantics:
    The active identity is pre-selected, and primary button has initial focus.
    """

    def __init__(self, parent: Optional[QDialog] = None):
        super().__init__(parent)
        self.setWindowTitle("多身份账户管理器 (Multi-Identity Manager)")
        self.resize(580, 480)
        self.setModal(True)

        self._setup_ui()
        self._load_accounts()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        layout.addWidget(QLabel("<h3>👤 多账号管理与身份切换</h3>"))
        layout.addWidget(QLabel("支持通过 SESSDATA / Cookie 快速导入身份。支持页面路由身份上下文继承。"))

        # Account List
        self.acc_list = QListWidget()
        self.acc_list.setStyleSheet("font-size: 13px;")
        layout.addWidget(self.acc_list)

        # Action Buttons for Selected Account
        btn_bar = QHBoxLayout()
        self.btn_set_active = QPushButton("设为当前活跃身份 (Enter)")
        self.btn_set_active.setProperty("class", "primary")
        self.btn_set_active.clicked.connect(self._on_set_active)
        btn_bar.addWidget(self.btn_set_active)

        self.btn_delete = QPushButton("删除身份")
        self.btn_delete.setProperty("class", "danger")
        self.btn_delete.clicked.connect(self._on_delete_account)
        btn_bar.addWidget(self.btn_delete)
        btn_bar.addStretch()

        layout.addLayout(btn_bar)

        # Quick Import Box
        import_group = QGroupBox("快速导入 (SESSDATA 或完整 Cookie 字符串)")
        import_layout = QVBoxLayout(import_group)

        self.input_name = QLineEdit()
        self.input_name.setPlaceholderText("账户备注名称 (例如: 工作小号)")
        import_layout.addWidget(self.input_name)

        self.input_cookie = QTextEdit()
        self.input_cookie.setPlaceholderText("粘贴浏览器 Cookie 或包含 SESSDATA=xxx; bili_jct=yyy 的内容...")
        self.input_cookie.setMaximumHeight(65)
        import_layout.addWidget(self.input_cookie)

        import_btn_row = QHBoxLayout()
        import_btn_row.addStretch()
        self.btn_import = QPushButton("一键导入并保存")
        self.btn_import.clicked.connect(self._on_import_cookie)
        import_btn_row.addWidget(self.btn_import)
        import_layout.addLayout(import_btn_row)

        layout.addWidget(import_group)

        # Close button (Esc)
        bottom_bar = QHBoxLayout()
        bottom_bar.addStretch()
        self.btn_close = QPushButton("完成 (Esc)")
        self.btn_close.clicked.connect(self.accept)
        bottom_bar.addWidget(self.btn_close)
        layout.addLayout(bottom_bar)

        # Default Value Semantics: focus on the primary action button
        apply_default_semantics(self.btn_set_active, is_default_action=True)

    def _load_accounts(self) -> None:
        self.acc_list.clear()
        active_id = state_machine.current_identity_id
        accounts = account_manager.list_all_accounts()

        active_row = 0
        for idx, acc in enumerate(accounts):
            is_active = (acc.id == active_id)
            label = f"[{'★ 活跃' if is_active else '   备用'}] {acc.name} (MID: {acc.mid}) - Lv{acc.level} {'[大会员]' if acc.is_vip else ''}"
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, acc.id)
            if is_active:
                item.setForeground(Qt.GlobalColor.cyan)
                active_row = idx
            self.acc_list.addItem(item)

        # Default selection
        if self.acc_list.count() > 0:
            self.acc_list.setCurrentRow(active_row)

    def _on_set_active(self) -> None:
        item = self.acc_list.currentItem()
        if not item:
            return
        acc_id = item.data(Qt.ItemDataRole.UserRole)
        state_machine.switch_page_identity(acc_id)
        self._load_accounts()

    def _on_delete_account(self) -> None:
        item = self.acc_list.currentItem()
        if not item:
            return
        acc_id = item.data(Qt.ItemDataRole.UserRole)
        account_manager.remove_account(acc_id)
        self._load_accounts()

    def _on_import_cookie(self) -> None:
        raw = self.input_cookie.toPlainText().strip()
        name = self.input_name.text().strip() or None
        if not raw:
            QMessageBox.warning(self, "提示", "请输入有效的 Cookie 或 SESSDATA 字符串。")
            return

        if "SESSDATA=" not in raw and len(raw) > 20:
            # User provided direct SESSDATA value
            raw = f"SESSDATA={raw}; bili_jct=mock_csrf; DedeUserID=88888"

        acc = account_manager.import_from_cookie(raw, name=name)
        self.input_cookie.clear()
        self.input_name.clear()
        self._load_accounts()
        QMessageBox.information(self, "导入成功", f"身份 [{acc.name}] 已成功录入！")
