"""High-Performance Danmaku Rendering Overlay Widget
Renders Normal rolling, Top/Bottom fixed, Mode 7 positioned, and BAS script danmaku.
"""

from __future__ import annotations
import math
from typing import List, Dict, Any, Optional
from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import (
    QPainter, QColor, QFont, QPen, QPainterPath, QFontMetrics
)
from PySide6.QtWidgets import QWidget

from app.models.danmaku import (
    NormalDanmaku, AdvancedDanmaku, BASDanmakuInstruction, DanmakuParser
)

class DanmakuOverlay(QWidget):
    """
    Transparent overlay placed directly on top of the video display.
    Uses QPainter with anti-aliasing and text outline stroke for maximum clarity.
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self.is_enabled = True
        self.danmaku_list: List[NormalDanmaku | AdvancedDanmaku] = []
        self.bas_instructions: List[BASDanmakuInstruction] = []
        self.current_time_sec: float = 0.0

        # Rendering parameters
        self.global_opacity: float = 0.9
        self.font_family: str = "Noto Sans, Segoe UI, sans-serif"

    def set_danmaku_data(self, normal_and_adv: List[Any], bas_scripts: List[BASDanmakuInstruction]) -> None:
        self.danmaku_list = sorted(normal_and_adv, key=lambda d: getattr(d, "time_offset", 0.0))
        self.bas_instructions = sorted(bas_scripts, key=lambda b: b.time_offset)
        self.update()

    def update_timeline(self, current_time: float) -> None:
        self.current_time_sec = current_time
        if self.is_enabled:
            self.update()

    def toggle_danmaku(self) -> bool:
        self.is_enabled = not self.is_enabled
        self.update()
        return self.is_enabled

    def paintEvent(self, event) -> None:
        if not self.is_enabled:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        width = float(self.width())
        height = float(self.height())
        if width <= 0 or height <= 0:
            return

        curr_t = self.current_time_sec

        # 1. Render Normal & Mode 7 Danmaku
        # Visible time window: items launched within last 6 seconds
        window_duration = 6.0
        active_items = [
            d for d in self.danmaku_list
            if d.time_offset <= curr_t <= (d.time_offset + (d.duration if isinstance(d, AdvancedDanmaku) else window_duration))
        ]

        track_height = 32.0
        max_tracks = max(1, int((height * 0.75) // track_height))

        for idx, dm in enumerate(active_items):
            if isinstance(dm, AdvancedDanmaku):
                self._draw_advanced_danmaku(painter, dm, curr_t, width, height)
            elif isinstance(dm, NormalDanmaku):
                track_idx = idx % max_tracks
                y_pos = (track_idx + 1) * track_height
                self._draw_normal_danmaku(painter, dm, curr_t, width, y_pos, window_duration)

        # 2. Render BAS Dynamic Danmaku
        for bas in self.bas_instructions:
            if bas.time_offset <= curr_t <= (bas.time_offset + bas.duration):
                self._draw_bas_danmaku(painter, bas, curr_t, width, height)

    def _draw_normal_danmaku(
        self,
        painter: QPainter,
        dm: NormalDanmaku,
        curr_t: float,
        width: float,
        y_pos: float,
        window_duration: float
    ) -> None:
        font = QFont(self.font_family, int(dm.font_size * 0.75), QFont.Weight.Bold)
        painter.setFont(font)
        fm = QFontMetrics(font)
        text_width = fm.horizontalAdvance(dm.text)

        elapsed = curr_t - dm.time_offset
        progress = max(0.0, min(1.0, elapsed / window_duration))

        if dm.is_rolling:
            # Rolling: moves from width down to -text_width
            x_pos = width - progress * (width + text_width)
        elif dm.is_top:
            x_pos = (width - text_width) / 2.0
            y_pos = 40.0
        elif dm.is_bottom:
            x_pos = (width - text_width) / 2.0
            y_pos = self.height() - 50.0
        else:
            x_pos = width - progress * (width + text_width)

        # Stroke (Outline for high contrast)
        path = QPainterPath()
        path.addText(QPointF(x_pos, y_pos), font, dm.text)

        color = QColor(dm.color_hex)
        color.setAlphaF(self.global_opacity)

        # Draw black stroke border
        stroke_pen = QPen(QColor(0, 0, 0, int(220 * self.global_opacity)), 2.5)
        stroke_pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.strokePath(path, stroke_pen)
        painter.fillPath(path, color)

    def _draw_advanced_danmaku(
        self,
        painter: QPainter,
        dm: AdvancedDanmaku,
        curr_t: float,
        width: float,
        height: float
    ) -> None:
        norm_x, norm_y, alpha, rot_z = dm.get_interpolated_state(curr_t)
        abs_x = norm_x * width
        abs_y = norm_y * height

        painter.save()
        painter.translate(abs_x, abs_y)
        if rot_z != 0.0:
            painter.rotate(rot_z)

        font = QFont(self.font_family, int(dm.font_size * 0.8), QFont.Weight.Bold)
        painter.setFont(font)

        path = QPainterPath()
        path.addText(QPointF(0, 0), font, dm.text)

        color = QColor(f"#{dm.color:06X}")
        color.setAlphaF(alpha * self.global_opacity)

        stroke_pen = QPen(QColor(0, 0, 0, int(220 * alpha * self.global_opacity)), 2.5)
        painter.strokePath(path, stroke_pen)
        painter.fillPath(path, color)
        painter.restore()

    def _draw_bas_danmaku(
        self,
        painter: QPainter,
        bas: BASDanmakuInstruction,
        curr_t: float,
        width: float,
        height: float
    ) -> None:
        state = bas.evaluate(curr_t)
        if not state.get("visible", False):
            return

        x = state.get("x", 0.5) * width
        y = state.get("y", 0.5) * height
        alpha = state.get("alpha", 1.0)
        font_size = state.get("fontSize", 24)
        color_str = state.get("color", "#FFDD57")
        text = state.get("text", "")

        painter.save()
        painter.translate(x, y)

        font = QFont(self.font_family, int(font_size * 0.8), QFont.Weight.Bold)
        painter.setFont(font)

        path = QPainterPath()
        path.addText(QPointF(0, 0), font, text)

        try:
            color = QColor(color_str)
        except Exception:
            color = QColor("#FFDD57")
        color.setAlphaF(alpha * self.global_opacity)

        stroke_pen = QPen(QColor(20, 20, 20, int(230 * alpha * self.global_opacity)), 3.0)
        painter.strokePath(path, stroke_pen)
        painter.fillPath(path, color)
        painter.restore()
