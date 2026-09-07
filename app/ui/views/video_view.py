"""Main Video Player, Danmaku Engine, and 40 Recommendations View
Features:
- Resizable QSplitter layout (horizontally and vertically)
- Detachable Standalone Window (画中画/独立弹窗播放，支持置顶与自由缩放)
- Native PySide6.QtMultimedia (QMediaPlayer & QVideoWidget)
- LocalStreamProxy pipeline for real-time video playback and passive stream archiving
"""

from __future__ import annotations
import time
from typing import Optional, List
from PySide6.QtCore import Qt, QTimer, Signal, QUrl
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSlider, QComboBox, QTabWidget, QScrollArea, QFrame,
    QSplitter, QListWidget, QListWidgetItem, QSizePolicy,
    QMainWindow, QApplication
)

from app.models.video import VideoInfo, RecommendationItem
from app.models.comment import CommentNode
from app.models.danmaku import DanmakuParser
from app.mock_data import get_mock_danmaku_data
from app.ui.components.danmaku_overlay import DanmakuOverlay
from app.ui.components.video_card import VideoCardWidget
from app.ui.views.comment_view import CommentTreeView
from app.core.account_manager import account_manager
from app.core.state_machine import state_machine
from app.core.network import bili_client
from app.core.storage import archive_writer, archive_db
from app.core.config import config_instance


class DetachedPlayerWindow(QMainWindow):
    """
    Independent Standalone Player Window (Pop-out / Picture-in-Picture).
    Supports free resizing, window pinning (Always on Top), and re-embedding.
    """

    reembed_requested = Signal()

    def __init__(self, player_widget: QWidget, title: str = "Bilibili 独立播放窗口", parent: Optional[QWidget] = None):
        super().__init__(None)
        self.player_widget = player_widget
        self.setWindowTitle(f"🎬 {title} - 独立播放器")
        self.resize(1024, 620)
        self.setMinimumSize(480, 270)
        self.is_pinned = False

        self.setStyleSheet("""
        QMainWindow {
            background-color: #121416;
        }
        """)

        # Top Control & Title Bar
        toolbar = QFrame()
        toolbar.setStyleSheet("background-color: #232629; border-bottom: 1px solid #31363b; padding: 4px;")
        tb_layout = QHBoxLayout(toolbar)
        tb_layout.setContentsMargins(8, 4, 8, 4)

        self.title_lbl = QLabel(f"<b>🎬 {title}</b>")
        self.title_lbl.setStyleSheet("color: #eff0f1; font-size: 13px;")
        tb_layout.addWidget(self.title_lbl)
        tb_layout.addStretch()

        self.btn_pin = QPushButton("📌 窗口置顶: 关")
        self.btn_pin.setToolTip("保持播放器窗口始终处于其他窗口最前端")
        self.btn_pin.clicked.connect(self.toggle_pin)
        tb_layout.addWidget(self.btn_pin)

        self.btn_reembed = QPushButton("⬇ 还原嵌入到主界面")
        self.btn_reembed.setProperty("class", "primary")
        self.btn_reembed.clicked.connect(self.reembed_requested.emit)
        tb_layout.addWidget(self.btn_reembed)

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(toolbar)
        layout.addWidget(self.player_widget)
        self.setCentralWidget(central)

    def set_title(self, title: str) -> None:
        self.setWindowTitle(f"🎬 {title} - 独立播放器")
        self.title_lbl.setText(f"<b>🎬 {title}</b>")

    def toggle_pin(self) -> None:
        self.is_pinned = not self.is_pinned
        self.btn_pin.setText("📌 窗口置顶: 开" if self.is_pinned else "📌 窗口置顶: 关")
        pos = self.pos()
        size = self.size()
        flags = self.windowFlags()
        if self.is_pinned:
            self.setWindowFlags(flags | Qt.WindowType.WindowStaysOnTopHint)
        else:
            self.setWindowFlags(flags & ~Qt.WindowType.WindowStaysOnTopHint)
        self.resize(size)
        self.move(pos)
        self.show()

    def closeEvent(self, event) -> None:
        # Re-embed cleanly back into the main window when closed
        self.reembed_requested.emit()
        event.accept()


class VideoView(QWidget):
    """
    Video Playback view combining Native Qt6 QVideoWidget, QMediaPlayer,
    Danmaku overlay, resizable QSplitters, and detachable standalone window.
    """

    navigate_video = Signal(str)     # Emits target bvid
    navigate_up_space = Signal(int, str) # Emits (up_id, up_name)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.video_info: Optional[VideoInfo] = None
        self.playback_time_sec: float = 0.0
        self.total_duration_sec: float = 754.0
        self.detached_window: Optional[DetachedPlayerWindow] = None

        self._setup_media_player()
        self._setup_ui()
        self._setup_timer()

    def _setup_media_player(self) -> None:
        self.player = QMediaPlayer(self)
        self.audio_output = QAudioOutput(self)
        self.player.setAudioOutput(self.audio_output)
        self.audio_output.setVolume(0.85)

        # Signals
        self.player.positionChanged.connect(self._on_player_position_changed)
        self.player.durationChanged.connect(self._on_player_duration_changed)
        self.player.playbackStateChanged.connect(self._on_playback_state_changed)
        self.player.errorOccurred.connect(self._on_player_error)

    def _setup_ui(self) -> None:
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(6, 6, 6, 6)
        main_layout.setSpacing(6)

        # MAIN HORIZONTAL SPLITTER: Left (Player + Details) vs Right (40 Recommendations)
        self.h_splitter = QSplitter(Qt.Orientation.Horizontal)

        # LEFT VERTICAL SPLITTER: Top (Player) vs Bottom (Meta info + Comments)
        self.v_splitter = QSplitter(Qt.Orientation.Vertical)

        # 1. Player Host Wrapper (Contains player container or detached placeholder)
        self.player_host_widget = QWidget()
        self.player_host_layout = QVBoxLayout(self.player_host_widget)
        self.player_host_layout.setContentsMargins(0, 0, 0, 0)
        self.player_host_layout.setSpacing(0)

        # Placeholder Banner (Shown when player is detached in standalone window)
        self.detached_banner = QFrame()
        self.detached_banner.setStyleSheet("""
        QFrame {
            background-color: #1b1e20;
            border: 2px dashed #3daee9;
            border-radius: 8px;
            padding: 24px;
        }
        """)
        d_layout = QVBoxLayout(self.detached_banner)
        d_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_info = QLabel("<h3>📺 播放器正在独立窗口中运行</h3>")
        lbl_info.setStyleSheet("color: #3daee9;")
        lbl_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_hint = QLabel("您可以自由拖动调整独立窗口尺寸，或设置窗口置顶。")
        lbl_hint.setStyleSheet("color: #bdc3c7;")
        lbl_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        btn_restore = QPushButton("⬇ 还原到此处嵌入播放")
        btn_restore.setProperty("class", "primary")
        btn_restore.setFixedWidth(200)
        btn_restore.clicked.connect(self._reembed_player)

        d_layout.addWidget(lbl_info)
        d_layout.addWidget(lbl_hint)
        d_layout.addSpacing(10)
        d_layout.addWidget(btn_restore, alignment=Qt.AlignmentFlag.AlignCenter)
        self.detached_banner.hide()
        self.player_host_layout.addWidget(self.detached_banner)

        # Real Player Container
        self.player_container = QFrame()
        self.player_container.setMinimumSize(480, 270)
        self.player_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.player_container.setStyleSheet("""
        QFrame#PlayerContainer {
            background-color: #000000;
            border: 1px solid #31363b;
            border-radius: 6px;
        }
        """)
        self.player_container.setObjectName("PlayerContainer")

        player_box_layout = QVBoxLayout(self.player_container)
        player_box_layout.setContentsMargins(0, 0, 0, 0)
        player_box_layout.setSpacing(0)

        # Native QVideoWidget screen surface
        self.video_widget = QVideoWidget(self.player_container)
        self.video_widget.setStyleSheet("background-color: #000000;")
        self.video_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.player.setVideoOutput(self.video_widget)
        player_box_layout.addWidget(self.video_widget)

        # Danmaku Overlay on top of QVideoWidget
        self.danmaku_overlay = DanmakuOverlay(self.video_widget)

        # Player Controls Bar
        ctrl_bar = QFrame()
        ctrl_bar.setStyleSheet("background-color: #232629; padding: 4px; border-radius: 4px;")
        ctrl_layout = QVBoxLayout(ctrl_bar)
        ctrl_layout.setContentsMargins(8, 4, 8, 4)
        ctrl_layout.setSpacing(4)

        # Timeline Slider
        self.seek_slider = QSlider(Qt.Orientation.Horizontal)
        self.seek_slider.setRange(0, 1000)
        self.seek_slider.setValue(0)
        self.seek_slider.setStyleSheet("""
        QSlider::groove:horizontal {
            height: 4px;
            background: #474d54;
            border-radius: 2px;
        }
        QSlider::sub-page:horizontal {
            background: #3daee9;
            border-radius: 2px;
        }
        QSlider::handle:horizontal {
            background: #eff0f1;
            border: 1px solid #3daee9;
            width: 12px;
            margin-top: -4px;
            margin-bottom: -4px;
            border-radius: 6px;
        }
        """)
        self.seek_slider.sliderMoved.connect(self._on_slider_moved)
        ctrl_layout.addWidget(self.seek_slider)

        # Controls row
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self.btn_play = QPushButton("⏸ 暂停 (Space)")
        self.btn_play.clicked.connect(self.toggle_play)
        btn_row.addWidget(self.btn_play)

        self.time_label = QLabel("00:00 / 00:00")
        self.time_label.setStyleSheet("color: #eff0f1; font-size: 12px; font-family: monospace;")
        btn_row.addWidget(self.time_label)

        btn_row.addStretch()

        # Danmaku Toggle
        self.btn_danmaku = QPushButton("弹幕: 开 (d)")
        self.btn_danmaku.clicked.connect(self.toggle_danmaku)
        btn_row.addWidget(self.btn_danmaku)

        # Quality Selector
        self.quality_combo = QComboBox()
        self.quality_combo.addItems(["360P 流畅", "720P 高清", "1080P 高清", "4K 超清"])
        btn_row.addWidget(self.quality_combo)

        # Detach Pop-out Window Button
        self.btn_popout = QPushButton("⧉ 独立窗口")
        self.btn_popout.setToolTip("在独立窗口中播放 (支持拖动缩放、置顶与多屏)")
        self.btn_popout.clicked.connect(self.toggle_detached_window)
        btn_row.addWidget(self.btn_popout)

        # Passive Recording Indicator
        self.rec_badge = QLabel("● 播放器就绪")
        self.rec_badge.setStyleSheet("color: #27ae60; font-size: 11px; font-weight: bold;")
        btn_row.addWidget(self.rec_badge)

        self.btn_fullscreen = QPushButton("⛶ 全屏 (f)")
        self.btn_fullscreen.clicked.connect(self.toggle_fullscreen)
        btn_row.addWidget(self.btn_fullscreen)

        ctrl_layout.addLayout(btn_row)
        player_box_layout.addWidget(ctrl_bar)

        self.player_host_layout.addWidget(self.player_container)
        self.v_splitter.addWidget(self.player_host_widget)

        # 2. Lower Container (Metadata + Comments) in Scroll Area
        lower_scroll = QScrollArea()
        lower_scroll.setWidgetResizable(True)
        lower_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        lower_widget = QWidget()
        lower_layout = QVBoxLayout(lower_widget)
        lower_layout.setContentsMargins(0, 6, 0, 0)
        lower_layout.setSpacing(8)

        # Video Metadata & Action Bar
        meta_box = QFrame()
        meta_box.setStyleSheet("background-color: #2a2e32; border-radius: 6px; padding: 10px;")
        meta_layout = QVBoxLayout(meta_box)
        meta_layout.setSpacing(6)

        # Title + IP Location
        top_title_row = QHBoxLayout()
        self.title_label = QLabel("正在加载视频...")
        self.title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #eff0f1;")
        self.title_label.setWordWrap(True)
        top_title_row.addWidget(self.title_label)

        self.ip_badge = QLabel("IP属地: 未知")
        self.ip_badge.setStyleSheet("""
        background-color: #1e3a5f;
        color: #78b9e6;
        border-radius: 3px;
        padding: 2px 8px;
        font-size: 11px;
        font-weight: bold;
        """)
        top_title_row.addWidget(self.ip_badge)
        meta_layout.addLayout(top_title_row)

        # UP Info & Follow Hook
        up_row = QHBoxLayout()
        up_row.setSpacing(10)

        self.up_name_btn = QPushButton("👤 UP主: 加载中... (按 u 进入空间)")
        self.up_name_btn.setStyleSheet("font-weight: bold; text-align: left; background: transparent; border: none; color: #3daee9;")
        self.up_name_btn.clicked.connect(self._on_up_clicked)
        up_row.addWidget(self.up_name_btn)

        self.btn_follow = QPushButton("+ 关注 (实时监听)")
        self.btn_follow.setProperty("class", "primary")
        self.btn_follow.clicked.connect(self._on_follow_clicked)
        up_row.addWidget(self.btn_follow)

        up_row.addStretch()

        self.stat_label = QLabel("播放 --  •  弹幕 --")
        self.stat_label.setStyleSheet("color: #bdc3c7; font-size: 12px;")
        up_row.addWidget(self.stat_label)

        meta_layout.addLayout(up_row)

        # Social Action Bar (Like, Coin, Fav, Share)
        act_row = QHBoxLayout()
        act_row.setSpacing(12)

        self.btn_like = QPushButton("👍 点赞")
        self.btn_like.clicked.connect(self._on_like_clicked)
        act_row.addWidget(self.btn_like)

        self.btn_coin = QPushButton("🪙 投币")
        self.btn_coin.clicked.connect(self._on_coin_clicked)
        act_row.addWidget(self.btn_coin)

        self.btn_fav = QPushButton("⭐ 收藏")
        self.btn_fav.clicked.connect(self._on_fav_clicked)
        act_row.addWidget(self.btn_fav)

        self.btn_share = QPushButton("↗ 分享")
        act_row.addWidget(self.btn_share)

        act_row.addStretch()

        self.identity_badge = QLabel("当前活跃身份: 主号")
        self.identity_badge.setStyleSheet("color: #f39c12; font-size: 11px;")
        act_row.addWidget(self.identity_badge)

        meta_layout.addLayout(act_row)
        lower_layout.addWidget(meta_box)

        # Comments Tree View
        self.comment_view = CommentTreeView()
        lower_layout.addWidget(self.comment_view)

        lower_scroll.setWidget(lower_widget)
        self.v_splitter.addWidget(lower_scroll)

        # Generous default sizes: Top player 540px, bottom comments 360px
        self.v_splitter.setSizes([540, 360])
        self.h_splitter.addWidget(self.v_splitter)

        # RIGHT CONTAINER: 40 Related Recommendations
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(6)

        rcmd_header = QLabel("<h3>📺 相关推荐 (40 项全量加载)</h3>")
        rcmd_sub = QLabel("支持 j/k 逐项滚动，按 Enter 播放并继承当前身份")
        rcmd_sub.setStyleSheet("color: #bdc3c7; font-size: 11px;")
        right_layout.addWidget(rcmd_header)
        right_layout.addWidget(rcmd_sub)

        # Scroll Area for 40 Recommendation Cards
        self.rcmd_scroll = QScrollArea()
        self.rcmd_scroll.setWidgetResizable(True)
        self.rcmd_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        self.rcmd_container = QWidget()
        self.rcmd_cards_layout = QVBoxLayout(self.rcmd_container)
        self.rcmd_cards_layout.setContentsMargins(4, 4, 4, 4)
        self.rcmd_cards_layout.setSpacing(8)

        self.rcmd_scroll.setWidget(self.rcmd_container)
        right_layout.addWidget(self.rcmd_scroll)

        self.h_splitter.addWidget(right_widget)
        # Default horizontal sizes: Left 1020px, Right 360px
        self.h_splitter.setSizes([1020, 360])

        main_layout.addWidget(self.h_splitter)

    def _setup_timer(self) -> None:
        """Fallback timer for offline simulation mode when no native media is active."""
        self.timer = QTimer(self)
        self.timer.setInterval(100)
        self.timer.timeout.connect(self._on_fallback_timer_tick)
        self.timer.start()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        # Keep Danmaku overlay exactly matching the video widget canvas
        if self.video_widget:
            self.danmaku_overlay.setGeometry(self.video_widget.rect())

    # --- Detached Standalone Window Management ---

    def toggle_detached_window(self) -> None:
        if self.detached_window is not None:
            self._reembed_player()
        else:
            self._detach_player()

    def _detach_player(self) -> None:
        if self.detached_window is not None:
            return

        # Hide container from main layout and show placeholder banner
        self.player_host_layout.removeWidget(self.player_container)
        self.detached_banner.show()

        # Create detached window
        title = self.video_info.title if self.video_info else "Bilibili"
        self.detached_window = DetachedPlayerWindow(self.player_container, title=title, parent=self)
        self.detached_window.reembed_requested.connect(self._reembed_player)
        self.detached_window.show()

        self.btn_popout.setText("⬇ 还原嵌入")
        # Ensure danmaku overlay adjusts to new detached window dimensions
        QTimer.singleShot(100, lambda: self.danmaku_overlay.setGeometry(self.video_widget.rect()))

    def _reembed_player(self) -> None:
        if self.detached_window is None:
            return

        # Reparent back to main window layout
        self.player_host_layout.removeWidget(self.detached_banner)
        self.detached_banner.hide()

        # Central widget of detached window was central widget containing player_widget
        self.player_container.setParent(self.player_host_widget)
        self.player_host_layout.addWidget(self.player_container)
        self.player_host_layout.addWidget(self.detached_banner)

        # Close detached window
        w = self.detached_window
        self.detached_window = None
        w.close()
        w.deleteLater()

        self.btn_popout.setText("⧉ 独立窗口")
        self.player_container.show()
        self.video_widget.show()
        QTimer.singleShot(100, lambda: self.danmaku_overlay.setGeometry(self.video_widget.rect()))

    # --- Video Data & Playback Loading ---

    def load_video(self, bvid: str) -> None:
        """Loads video, pass-through interceptor archives into SQLite, and starts native media playback."""
        self.player.stop()

        # 1. Fetch video info (Passive Interception triggers inside)
        self.video_info = bili_client.fetch_video_detail(bvid)
        
        # 2. Update UI texts
        self.title_label.setText(self.video_info.title)
        self.ip_badge.setText(self.video_info.ip_location)
        self.up_name_btn.setText(f"👤 UP主: {self.video_info.up_name} (按 u 进入空间)")
        self.stat_label.setText(
            f"播放 {self.video_info.view:,}  •  弹幕 {self.video_info.danmaku:,}  •  {self.video_info.ip_location}"
        )
        self.btn_like.setText(f"👍 点赞 ({self.video_info.like:,})")
        self.btn_coin.setText(f"🪙 投币 ({self.video_info.coin:,})")
        self.btn_fav.setText(f"⭐ 收藏 ({self.video_info.favorite:,})")
        self.btn_share.setText(f"↗ 分享 ({self.video_info.share:,})")

        if self.detached_window:
            self.detached_window.set_title(self.video_info.title)

        # Identity status
        curr_acc = state_machine.current_account
        self.identity_badge.setText(f"当前活跃身份: {curr_acc.name}")

        # 3. Load Comments Tree (includes orphan nodes)
        comments_tree = bili_client.fetch_comments(oid=self.video_info.aid or 88776655)
        self.comment_view.set_comments(comments_tree, oid=self.video_info.aid)

        # 4. Load Danmaku (Normal, Mode 7, and BAS)
        raw_danmaku_data = get_mock_danmaku_data()
        normal_and_adv = []
        bas_scripts = []
        for d in raw_danmaku_data:
            if d["mode"] == 8: # BAS
                instructions = DanmakuParser.parse_bas_script(d["text"], time_offset=d["time"])
                bas_scripts.extend(instructions)
            elif d["mode"] == 7: # Mode 7
                p_str = f"{d['time']},7,{d['size']},{d['color']},1600000000,0,hash,1"
                adv = DanmakuParser.parse_xml_danmaku(p_str, d["text"])
                normal_and_adv.append(adv)
            else: # Normal
                p_str = f"{d['time']},{d['mode']},{d['size']},{d['color']},1600000000,0,hash,1"
                norm = DanmakuParser.parse_xml_danmaku(p_str, d["text"])
                normal_and_adv.append(norm)

        self.danmaku_overlay.set_danmaku_data(normal_and_adv, bas_scripts)

        # 5. Load 40 Recommendations
        rcmds = bili_client.fetch_recommendations(bvid)
        self._populate_recommendations(rcmds)

        # 6. Start Native Video Stream Playback & Passive Recording
        cid = self.video_info.cid or 62131
        stream_proxy_url = bili_client.fetch_play_stream_url(bvid, cid)
        if stream_proxy_url:
            self.rec_badge.setText("● 视频流播放与被动存档中")
            self.rec_badge.setStyleSheet("color: #27ae60; font-size: 11px; font-weight: bold;")
            self.player.setSource(QUrl(stream_proxy_url))
            self.player.play()
        else:
            self.rec_badge.setText("● 离线演示模拟中")
            self.rec_badge.setStyleSheet("color: #f39c12; font-size: 11px; font-weight: bold;")

    def _populate_recommendations(self, rcmds: List[RecommendationItem]) -> None:
        # Clear existing cards
        while self.rcmd_cards_layout.count() > 0:
            child = self.rcmd_cards_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        for item in rcmds:
            card = VideoCardWidget(item)
            card.clicked.connect(self._on_rcmd_card_clicked)
            self.rcmd_cards_layout.addWidget(card)

    def _on_rcmd_card_clicked(self, bvid: str) -> None:
        # Context inheritance: inherits current active identity
        self.navigate_video.emit(bvid)

    def _on_up_clicked(self) -> None:
        if self.video_info:
            self.navigate_up_space.emit(self.video_info.up_id, self.video_info.up_name)

    def _on_follow_clicked(self) -> None:
        if not self.video_info:
            return
        bili_client.perform_follow(
            up_id=self.video_info.up_id,
            up_name=self.video_info.up_name,
            is_following=True
        )
        self.btn_follow.setText("✓ 已关注")
        self.btn_follow.setEnabled(False)

    def _on_like_clicked(self) -> None:
        if self.video_info:
            self.video_info.like += 1
            self.btn_like.setText(f"👍 已赞 ({self.video_info.like:,})")
            archive_writer.enqueue("video", self.video_info.to_dict())

    def _on_coin_clicked(self) -> None:
        if self.video_info:
            self.video_info.coin += 2
            self.btn_coin.setText(f"🪙 投币+2 ({self.video_info.coin:,})")
            archive_writer.enqueue("video", self.video_info.to_dict())

    def _on_fav_clicked(self) -> None:
        if self.video_info:
            self.video_info.favorite += 1
            self.btn_fav.setText(f"⭐ 已收藏 ({self.video_info.favorite:,})")
            archive_writer.enqueue("video", self.video_info.to_dict())

    # --- Native QMediaPlayer Signal Handlers ---

    def _on_player_position_changed(self, pos_ms: int) -> None:
        self.playback_time_sec = pos_ms / 1000.0
        dur_ms = self.player.duration()
        if dur_ms > 0:
            val = int((pos_ms / dur_ms) * 1000)
            self.seek_slider.blockSignals(True)
            self.seek_slider.setValue(val)
            self.seek_slider.blockSignals(False)

            cur_m, cur_s = divmod(int(self.playback_time_sec), 60)
            tot_m, tot_s = divmod(int(dur_ms / 1000), 60)
            self.time_label.setText(f"{cur_m:02d}:{cur_s:02d} / {tot_m:02d}:{tot_s:02d}")

        self.danmaku_overlay.update_timeline(self.playback_time_sec)

    def _on_player_duration_changed(self, dur_ms: int) -> None:
        if dur_ms > 0:
            self.total_duration_sec = dur_ms / 1000.0
            cur_m, cur_s = divmod(int(self.playback_time_sec), 60)
            tot_m, tot_s = divmod(int(self.total_duration_sec), 60)
            self.time_label.setText(f"{cur_m:02d}:{cur_s:02d} / {tot_m:02d}:{tot_s:02d}")

    def _on_playback_state_changed(self, state: QMediaPlayer.PlaybackState) -> None:
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.btn_play.setText("⏸ 暂停 (Space)")
        else:
            self.btn_play.setText("▶ 播放 (Space)")

    def _on_player_error(self, error: QMediaPlayer.Error, error_string: str) -> None:
        print(f"[QMediaPlayer] Error ({error}): {error_string}")

    def _on_slider_moved(self, value: int) -> None:
        dur_ms = self.player.duration()
        if dur_ms > 0:
            target_pos = int((value / 1000.0) * dur_ms)
            self.player.setPosition(target_pos)
            self.playback_time_sec = target_pos / 1000.0
            self.danmaku_overlay.update_timeline(self.playback_time_sec)
        else:
            self.playback_time_sec = (value / 1000.0) * self.total_duration_sec
            self.danmaku_overlay.update_timeline(self.playback_time_sec)

    def _on_fallback_timer_tick(self) -> None:
        """Only animates if QMediaPlayer is not loaded with native stream."""
        if self.player.duration() > 0:
            return

        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.playback_time_sec += 0.1
            if self.playback_time_sec > self.total_duration_sec:
                self.playback_time_sec = 0.0

            val = int((self.playback_time_sec / self.total_duration_sec) * 1000)
            self.seek_slider.blockSignals(True)
            self.seek_slider.setValue(val)
            self.seek_slider.blockSignals(False)

            cur_m, cur_s = divmod(int(self.playback_time_sec), 60)
            tot_m, tot_s = divmod(int(self.total_duration_sec), 60)
            self.time_label.setText(f"{cur_m:02d}:{cur_s:02d} / {tot_m:02d}:{tot_s:02d}")
            self.danmaku_overlay.update_timeline(self.playback_time_sec)

    def toggle_play(self) -> None:
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
        else:
            self.player.play()

    def toggle_danmaku(self) -> None:
        enabled = self.danmaku_overlay.toggle_danmaku()
        self.btn_danmaku.setText("弹幕: 开 (d)" if enabled else "弹幕: 关 (d)")

    def toggle_fullscreen(self) -> None:
        win = self.detached_window if self.detached_window else self.window()
        if win.isFullScreen():
            win.showNormal()
        else:
            win.showFullScreen()
