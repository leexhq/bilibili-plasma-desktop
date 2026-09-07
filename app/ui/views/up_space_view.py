"""UP Space Deep Aggregated View
Displays the multi-identity follow matrix and exact follow timestamps for all configured accounts.
"""

from __future__ import annotations
import time
from typing import Optional, List, Dict, Any
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QFrame,
    QScrollArea
)

from app.core.account_manager import account_manager, Account
from app.core.storage import archive_db, archive_writer
from app.core.state_machine import state_machine
from app.core.network import bili_client

class UPSpaceView(QWidget):
    """
    UP Space View featuring the Multi-Identity Follow Matrix:
    Aggregates follow states and timestamps across all local accounts.
    """

    back_requested = Signal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.up_id: int = 998877
        self.up_name: str = "KDE_Plasma_Lab"
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        # Header Navigation & Breadcrumbs
        nav_bar = QHBoxLayout()
        self.btn_back = QPushButton("◀ 返回上一页 (Esc / Back)")
        self.btn_back.clicked.connect(self.back_requested.emit)
        nav_bar.addWidget(self.btn_back)

        self.breadcrumb_label = QLabel(f"UP主个人空间 > {self.up_name}")
        self.breadcrumb_label.setStyleSheet("color: #bdc3c7; font-size: 13px;")
        nav_bar.addWidget(self.breadcrumb_label)
        nav_bar.addStretch()

        layout.addLayout(nav_bar)

        # UP Profile Banner
        banner = QFrame()
        banner.setStyleSheet("""
        QFrame {
            background-color: #2a2e32;
            border: 1px solid #474d54;
            border-radius: 8px;
            padding: 16px;
        }
        """)
        b_layout = QHBoxLayout(banner)
        b_layout.setSpacing(16)

        # Avatar placeholder
        avatar_box = QLabel("KDE")
        avatar_box.setFixedSize(64, 64)
        avatar_box.setAlignment(Qt.AlignmentFlag.AlignCenter)
        avatar_box.setStyleSheet("""
        background-color: #3daee9;
        color: #ffffff;
        font-weight: bold;
        font-size: 18px;
        border-radius: 32px;
        """)
        b_layout.addWidget(avatar_box)

        # UP Info Text
        info_col = QVBoxLayout()
        self.up_name_label = QLabel(f"<h2>{self.up_name}</h2>")
        self.up_uid_label = QLabel(f"UID: {self.up_id}   •   粉丝数: 1,280,400   •   视频数: 142")
        self.up_uid_label.setStyleSheet("color: #bdc3c7;")
        self.up_sign_label = QLabel("专注于 KDE Plasma 6 桌面生态、Linux 核心技术与专业 Qt6 架构实战。")
        self.up_sign_label.setStyleSheet("color: #eff0f1;")

        info_col.addWidget(self.up_name_label)
        info_col.addWidget(self.up_uid_label)
        info_col.addWidget(self.up_sign_label)
        b_layout.addLayout(info_col)
        b_layout.addStretch()

        layout.addWidget(banner)

        # Section: Multi-Identity Follow Matrix (多身份聚合深度视图)
        matrix_header = QLabel("<h3>👥 本地多身份关注深度矩阵 (Multi-Identity Follow Matrix)</h3>")
        matrix_desc = QLabel("聚合展示本地所有登录身份对该 UP 主的独立关注状态与精确关注时间。支持单身份独立切换。")
        matrix_desc.setStyleSheet("color: #bdc3c7;")
        layout.addWidget(matrix_header)
        layout.addWidget(matrix_desc)

        # Follow Matrix Table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            "登录身份", "身份 MID", "当前关注状态", "精确关注时间", "独立操作"
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setMinimumHeight(180)
        layout.addWidget(self.table)

        layout.addStretch()

    def load_up_profile(self, up_id: int, up_name: str) -> None:
        self.up_id = up_id
        self.up_name = up_name
        self.breadcrumb_label.setText(f"UP主个人空间 > {self.up_name}")
        self.up_name_label.setText(f"<h2>{self.up_name}</h2>")
        self.up_uid_label.setText(f"UID: {self.up_id}   •   粉丝数: 1,280,400   •   视频数: 142")

        self.refresh_follow_matrix()

    def refresh_follow_matrix(self) -> None:
        """Queries SQLite and account manager to rebuild the aggregated follow matrix."""
        accounts = account_manager.list_all_accounts()
        saved_matrix = archive_db.get_up_follows_matrix(self.up_id)
        saved_dict = {row["account_id"]: row for row in saved_matrix}

        self.table.setRowCount(len(accounts))

        for row_idx, acc in enumerate(accounts):
            record = saved_dict.get(acc.id)
            is_following = bool(record["is_following"]) if record else False
            follow_timestamp = record["follow_time"] if record else 0

            # 1. Identity Name + Badge
            name_text = f"{acc.name}"
            if acc.id == state_machine.current_identity_id:
                name_text += " [当前活跃]"
            item_name = QTableWidgetItem(name_text)
            self.table.setItem(row_idx, 0, item_name)

            # 2. MID
            item_mid = QTableWidgetItem(str(acc.mid))
            self.table.setItem(row_idx, 1, item_mid)

            # 3. Status
            status_text = "✅ 已关注" if is_following else "❌ 未关注"
            item_status = QTableWidgetItem(status_text)
            if is_following:
                item_status.setForeground(Qt.GlobalColor.green)
            else:
                item_status.setForeground(Qt.GlobalColor.gray)
            self.table.setItem(row_idx, 2, item_status)

            # 4. Exact Follow Timestamp
            if follow_timestamp > 0:
                time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(follow_timestamp))
            else:
                time_str = "暂无关注记录"
            item_time = QTableWidgetItem(time_str)
            self.table.setItem(row_idx, 3, item_time)

            # 5. Independent Action Button
            btn_action = QPushButton("取消关注" if is_following else "关注该UP主")
            if is_following:
                btn_action.setProperty("class", "danger")
            else:
                btn_action.setProperty("class", "primary")

            # Connect with identity-isolated closure
            btn_action.clicked.connect(lambda _, a_id=acc.id, following=is_following: self._toggle_follow_for_account(a_id, following))
            self.table.setCellWidget(row_idx, 4, btn_action)

    def _toggle_follow_for_account(self, account_id: str, current_following: bool) -> None:
        new_state = not current_following
        bili_client.perform_follow(
            up_id=self.up_id,
            up_name=self.up_name,
            is_following=new_state,
            account_id=account_id
        )
        self.refresh_follow_matrix()
