"""Passive Local Data Archive Inspector View
Inspects SQLite persisted data and confirms zero-extra-network-request guarantees.
"""

from __future__ import annotations
import time
from typing import Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView,
    QFrame
)

from app.core.storage import archive_db
from app.core.config import config_instance

class PassiveArchiveView(QWidget):
    """
    Inspector view displaying SQLite archived data captured passively from the network layer.
    """

    back_requested = Signal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Nav bar
        nav_bar = QHBoxLayout()
        self.btn_back = QPushButton("◀ 返回主界面 (Esc)")
        self.btn_back.clicked.connect(self.back_requested.emit)
        nav_bar.addWidget(self.btn_back)

        title = QLabel("<h3>📦 被动式零开销本地数据存档库 (Passive Archive DB)</h3>")
        nav_bar.addWidget(title)
        nav_bar.addStretch()

        self.btn_refresh = QPushButton("🔄 刷新数据 (r)")
        self.btn_refresh.clicked.connect(self.refresh_data)
        nav_bar.addWidget(self.btn_refresh)

        layout.addLayout(nav_bar)

        # Principles Notice
        notice = QFrame()
        notice.setStyleSheet("""
        QFrame {
            background-color: #1e3a5f;
            border: 1px solid #3daee9;
            border-radius: 6px;
            padding: 10px;
        }
        """)
        n_layout = QVBoxLayout(notice)
        n_lbl1 = QLabel("<b>零额外网络请求原则</b>：所有落盘数据均在客户端网络拦截层被动截获，严禁触发重复请求。")
        n_lbl2 = QLabel(f"<b>当前数据库文件</b>: {config_instance.get('archiving.db_path')}  |  <b>流录制状态</b>: {'启用' if config_instance.get('archiving.stream_recording.enabled') else '禁用'}")
        n_lbl1.setStyleSheet("color: #78b9e6;")
        n_lbl2.setStyleSheet("color: #eff0f1;")
        n_layout.addWidget(n_lbl1)
        n_layout.addWidget(n_lbl2)
        layout.addWidget(notice)

        # Tabs for Videos, Comments, Timeseries, Offline Queue
        self.tabs = QTabWidget()

        # Tab 1: Archived Videos
        self.video_table = QTableWidget()
        self.video_table.setColumnCount(6)
        self.video_table.setHorizontalHeaderLabels(["BV号", "视频标题", "UP主", "IP属地", "归档时间", "AID/CID"])
        self.video_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.video_table.verticalHeader().setVisible(False)
        self.tabs.addTab(self.video_table, "视频元数据 (Videos)")

        # Tab 2: Archived Comments
        self.comment_table = QTableWidget()
        self.comment_table.setColumnCount(6)
        self.comment_table.setHorizontalHeaderLabels(["RPID", "评论内容", "获赞", "IP属地", "孤儿容错", "时间戳"])
        self.comment_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.comment_table.verticalHeader().setVisible(False)
        self.tabs.addTab(self.comment_table, "评论流归档 (Comments)")

        # Tab 3: Dynamic Timeseries Logs
        self.ts_table = QTableWidget()
        self.ts_table.setColumnCount(6)
        self.ts_table.setHorizontalHeaderLabels(["目标类型", "目标ID", "记录时间", "点赞数", "播放/投币", "评论数"])
        self.ts_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.ts_table.verticalHeader().setVisible(False)
        self.tabs.addTab(self.ts_table, "动态时序变动 (Timeseries)")

        # Tab 4: Offline Disaster Queue
        self.offline_table = QTableWidget()
        self.offline_table.setColumnCount(5)
        self.offline_table.setHorizontalHeaderLabels(["操作ID", "操作类型", "身份ID", "状态", "创建时间"])
        self.offline_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.offline_table.verticalHeader().setVisible(False)
        self.tabs.addTab(self.offline_table, "离线容灾队列 (Offline Queue)")

        layout.addWidget(self.tabs)

    def refresh_data(self) -> None:
        # Load Videos
        videos = archive_db.get_archived_videos(limit=50)
        self.video_table.setRowCount(len(videos))
        for row_idx, v in enumerate(videos):
            self.video_table.setItem(row_idx, 0, QTableWidgetItem(str(v["bvid"])))
            self.video_table.setItem(row_idx, 1, QTableWidgetItem(str(v["title"])))
            self.video_table.setItem(row_idx, 2, QTableWidgetItem(str(v["up_name"])))
            self.video_table.setItem(row_idx, 3, QTableWidgetItem(str(v["ip_location"])))
            time_s = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(v["updated_at"])) if v["updated_at"] else "-"
            self.video_table.setItem(row_idx, 4, QTableWidgetItem(time_s))
            self.video_table.setItem(row_idx, 5, QTableWidgetItem(f"{v['aid']} / {v['cid']}"))

        # Load Comments (Sample for current OID)
        sample_comments = archive_db.get_archived_comments_for_oid(88776655)
        self.comment_table.setRowCount(len(sample_comments))
        for row_idx, c in enumerate(sample_comments):
            self.comment_table.setItem(row_idx, 0, QTableWidgetItem(str(c["rpid"])))
            self.comment_table.setItem(row_idx, 1, QTableWidgetItem(str(c["content"])))
            self.comment_table.setItem(row_idx, 2, QTableWidgetItem(f"👍 {c['like_count']}"))
            self.comment_table.setItem(row_idx, 3, QTableWidgetItem(str(c["ip_location"])))
            orphan_str = "⚠️ 是 (孤儿保护)" if c["is_orphan"] else "否"
            item_orphan = QTableWidgetItem(orphan_str)
            if c["is_orphan"]:
                item_orphan.setForeground(Qt.GlobalColor.yellow)
            self.comment_table.setItem(row_idx, 4, item_orphan)
            ctime_s = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(c["ctime"])) if c["ctime"] else "-"
            self.comment_table.setItem(row_idx, 5, QTableWidgetItem(ctime_s))

        # Load Timeseries
        ts_entries = archive_db.get_timeseries("BV1xx411c7mD")
        self.ts_table.setRowCount(len(ts_entries))
        for row_idx, t in enumerate(ts_entries):
            self.ts_table.setItem(row_idx, 0, QTableWidgetItem(str(t["target_type"])))
            self.ts_table.setItem(row_idx, 1, QTableWidgetItem(str(t["target_id"])))
            t_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(t["timestamp"]))
            self.ts_table.setItem(row_idx, 2, QTableWidgetItem(t_str))
            self.ts_table.setItem(row_idx, 3, QTableWidgetItem(f"{t['like_count']:,}"))
            self.ts_table.setItem(row_idx, 4, QTableWidgetItem(f"{t['view_count']:,} / {t['coin_count']:,}"))
            self.ts_table.setItem(row_idx, 5, QTableWidgetItem(f"{t['reply_count']:,}"))

        # Load Offline Actions
        offline_actions = archive_db.get_pending_offline_actions()
        self.offline_table.setRowCount(len(offline_actions))
        for row_idx, act in enumerate(offline_actions):
            self.offline_table.setItem(row_idx, 0, QTableWidgetItem(str(act["id"])))
            self.offline_table.setItem(row_idx, 1, QTableWidgetItem(str(act["action_type"])))
            self.offline_table.setItem(row_idx, 2, QTableWidgetItem(str(act["account_id"])))
            self.offline_table.setItem(row_idx, 3, QTableWidgetItem(str(act["status"])))
            created_s = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(act["created_at"]))
            self.offline_table.setItem(row_idx, 4, QTableWidgetItem(created_s))
