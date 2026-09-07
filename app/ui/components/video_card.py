"""KDE Breeze Video Card Component
Keyboard-accessible card widget for recommendation lists and search results.
"""

from __future__ import annotations
from typing import Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeyEvent, QColor
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QSizePolicy
)

from app.models.video import RecommendationItem

class VideoCardWidget(QFrame):
    clicked = Signal(str)  # Emits bvid

    def __init__(self, item: RecommendationItem, parent: Optional[QFrame] = None):
        super().__init__(parent)
        self.item = item
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._setup_ui()

    def _setup_ui(self) -> None:
        self.setStyleSheet("""
        VideoCardWidget {
            background-color: #2a2e32;
            border: 1px solid #474d54;
            border-radius: 6px;
            padding: 8px;
        }
        VideoCardWidget:hover {
            background-color: #353b41;
            border-color: #3daee9;
        }
        VideoCardWidget:focus {
            border: 2px solid #3daee9;
            background-color: #31363b;
        }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(10)

        # Left Thumbnail Box
        thumb_box = QFrame()
        thumb_box.setFixedSize(110, 68)
        thumb_box.setStyleSheet("""
        QFrame {
            background-color: #1b1e20;
            border-radius: 4px;
            border: 1px solid #3c4248;
        }
        """)
        thumb_layout = QVBoxLayout(thumb_box)
        thumb_layout.setContentsMargins(4, 4, 4, 4)
        thumb_layout.addStretch()

        dur_label = QLabel(self.item.duration)
        dur_label.setStyleSheet("""
        background-color: rgba(0, 0, 0, 0.75);
        color: #eff0f1;
        font-size: 10px;
        border-radius: 2px;
        padding: 1px 4px;
        """)
        dur_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        thumb_layout.addWidget(dur_label, alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom)

        layout.addWidget(thumb_box)

        # Right Info Box
        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)

        # Title
        title_lbl = QLabel(self.item.title)
        title_lbl.setWordWrap(True)
        title_lbl.setStyleSheet("font-weight: 600; font-size: 12px; color: #eff0f1;")
        info_layout.addWidget(title_lbl)

        # UP author and IP location
        meta_layout = QHBoxLayout()
        meta_layout.setSpacing(8)

        up_lbl = QLabel(f"👤 {self.item.up_name}")
        up_lbl.setStyleSheet("color: #bdc3c7; font-size: 11px;")
        meta_layout.addWidget(up_lbl)

        loc_lbl = QLabel(self.item.ip_location)
        loc_lbl.setStyleSheet("""
        background-color: #1e3a5f;
        color: #78b9e6;
        border-radius: 2px;
        padding: 1px 4px;
        font-size: 10px;
        """)
        meta_layout.addWidget(loc_lbl)

        if self.item.rcmd_reason:
            rcmd_lbl = QLabel(self.item.rcmd_reason)
            rcmd_lbl.setStyleSheet("""
            background-color: #43281c;
            color: #f39c12;
            border-radius: 2px;
            padding: 1px 4px;
            font-size: 10px;
            """)
            meta_layout.addWidget(rcmd_lbl)

        meta_layout.addStretch()
        info_layout.addLayout(meta_layout)

        # Play & Danmaku counts
        stat_layout = QHBoxLayout()
        stat_layout.setSpacing(12)
        stat_lbl = QLabel(f"▶ {self.item.play_count:,}   💬 {self.item.danmaku_count:,}")
        stat_lbl.setStyleSheet("color: #7f8c8d; font-size: 11px;")
        stat_layout.addWidget(stat_lbl)
        stat_layout.addStretch()
        info_layout.addLayout(stat_layout)

        layout.addLayout(info_layout)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.item.bvid)
        super().mousePressEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
            self.clicked.emit(self.item.bvid)
        else:
            super().keyPressEvent(event)
