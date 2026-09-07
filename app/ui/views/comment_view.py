"""Hierarchical Comment Tree View with Robust Orphan Fallback
Renders nested comment threads, IP location badges, and graceful fallback for deleted parents.
"""

from __future__ import annotations
from typing import List, Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit,
    QPushButton, QTreeWidget, QTreeWidgetItem, QComboBox,
    QFrame, QHeaderView
)

from app.models.comment import CommentNode
from app.core.account_manager import account_manager, Account
from app.core.state_machine import state_machine
from app.core.storage import archive_writer

class CommentTreeView(QWidget):
    """
    Renders comment threads as an interactive hierarchical tree.
    Guarantees zero crashes on missing/deleted parent nodes with Fallback badges.
    """

    comment_submitted = Signal(str, str)  # Emits (content, identity_id)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.current_oid: int = 0
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # Header with Stats & Identity Isolation Selector
        top_bar = QHBoxLayout()
        self.header_label = QLabel("💬 评论区 (Comments) - 按 c 快速跳转输入")
        self.header_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #eff0f1;")
        top_bar.addWidget(self.header_label)

        top_bar.addStretch()

        # Commenting Identity Selector (Identity Isolation)
        top_bar.addWidget(QLabel("发送身份:"))
        self.identity_combo = QComboBox()
        self.identity_combo.setToolTip("选择以此身份发送评论 (操作身份隔离)")
        self._refresh_identity_options()
        top_bar.addWidget(self.identity_combo)

        layout.addLayout(top_bar)

        # Comment Input Area
        input_container = QFrame()
        input_container.setStyleSheet("""
        QFrame {
            background-color: #2a2e32;
            border: 1px solid #474d54;
            border-radius: 6px;
            padding: 4px;
        }
        """)
        input_layout = QVBoxLayout(input_container)
        input_layout.setContentsMargins(8, 8, 8, 8)
        input_layout.setSpacing(6)

        self.input_text = QTextEdit()
        self.input_text.setPlaceholderText("发一条友善的评论 (按 Tab 切换到发送按钮，按 Esc 退出输入模式)...")
        self.input_text.setMaximumHeight(60)
        input_layout.addWidget(self.input_text)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        
        self.btn_send = QPushButton("发布评论 (Enter)")
        self.btn_send.setProperty("class", "primary")
        self.btn_send.clicked.connect(self._on_send_comment)
        btn_row.addWidget(self.btn_send)

        input_layout.addLayout(btn_row)
        layout.addWidget(input_container)

        # Tree Widget for Comments
        self.tree_widget = QTreeWidget()
        self.tree_widget.setHeaderLabels(["评论内容与层级", "时间 / IP 属地", "获赞"])
        self.tree_widget.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tree_widget.header().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.tree_widget.header().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.tree_widget.setAnimated(True)
        self.tree_widget.setAlternatingRowColors(True)
        layout.addWidget(self.tree_widget)

    def _refresh_identity_options(self) -> None:
        self.identity_combo.clear()
        for acc in account_manager.list_all_accounts():
            self.identity_combo.addItem(f"{acc.name} (Lv{acc.level})", acc.id)
        
        # Default value semantics: select active page identity
        active_id = state_machine.current_identity_id
        for i in range(self.identity_combo.count()):
            if self.identity_combo.itemData(i) == active_id:
                self.identity_combo.setCurrentIndex(i)
                break

    def set_comments(self, comments_tree: List[CommentNode], oid: int) -> None:
        self.current_oid = oid
        self.tree_widget.clear()
        self._refresh_identity_options()

        total_count = 0
        def add_node_to_tree(node: CommentNode, parent_item: Optional[QTreeWidgetItem] = None) -> QTreeWidgetItem:
            nonlocal total_count
            total_count += 1
            item = QTreeWidgetItem(parent_item or self.tree_widget)

            # Column 0: Member Name & Content + Fallback Tag
            display_text = f"👤 {node.member_name}:  {node.content}"
            if node.is_fallback_placeholder:
                display_text = f"⚠️ [系统占位: 原父评论已失效/删除] - {node.content}"
            elif node.is_orphan:
                display_text = f"🔖 [原回复已失效] {display_text}"

            item.setText(0, display_text)

            # Column 1: Time and IP Location
            time_and_loc = f"{node.formatted_time}  •  {node.location}"
            item.setText(1, time_and_loc)

            # Column 2: Likes
            item.setText(2, f"👍 {node.like_count}")

            # Styling for Orphan / Fallback Placeholder Nodes
            if node.is_fallback_placeholder:
                item.setForeground(0, Qt.GlobalColor.darkYellow)
                item.setToolTip(0, "父评论已被删除或未加载，系统自动挂载占位保护界面渲染")
            elif node.is_orphan:
                item.setForeground(0, Qt.GlobalColor.yellow)

            # Recursively render children
            for child in node.children:
                add_node_to_tree(child, item)

            return item

        for root in comments_tree:
            add_node_to_tree(root)

        self.tree_widget.expandAll()
        self.header_label.setText(f"💬 评论区 (共 {total_count} 条已解析) - 支持孤儿节点容错")

    def _on_send_comment(self) -> None:
        text = self.input_text.toPlainText().strip()
        if not text:
            return

        selected_id = self.identity_combo.currentData()
        acc = account_manager.get_account(selected_id) or account_manager.get_active_account()

        # Build dynamic comment node
        import time
        new_node = CommentNode(
            rpid=int(time.time() * 1000) % 1000000000,
            oid=self.current_oid,
            type=1,
            mid=acc.mid,
            member_name=acc.name,
            content=text,
            ctime=int(time.time()),
            like_count=0,
            location="IP属地: 本地",
            is_orphan=False
        )

        # Passive archive write
        archive_writer.enqueue("comment", {
            "rpid": new_node.rpid,
            "oid": new_node.oid,
            "type": new_node.type,
            "mid": new_node.mid,
            "member_name": new_node.member_name,
            "root_id": 0,
            "parent_id": 0,
            "ctime": new_node.ctime,
            "content": new_node.content,
            "like_count": 0,
            "location": new_node.location,
            "is_orphan": False
        })

        # Add to UI top
        item = QTreeWidgetItem(self.tree_widget)
        item.setText(0, f"👤 {new_node.member_name}:  {new_node.content}")
        item.setText(1, f"{new_node.formatted_time}  •  {new_node.location}")
        item.setText(2, "👍 0")
        item.setForeground(0, Qt.GlobalColor.cyan)
        self.tree_widget.insertTopLevelItem(0, item)

        self.input_text.clear()
        self.comment_submitted.emit(text, selected_id)

    def focus_input(self) -> None:
        self.input_text.setFocus()
