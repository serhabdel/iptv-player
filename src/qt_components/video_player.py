"""Video player component using QMediaPlayer + QVideoWidget."""
import asyncio
from typing import Optional, Callable, List
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSlider,
    QStackedWidget, QFrame, QDialog, QListWidget, QListWidgetItem,
    QMessageBox, QSizePolicy, QComboBox, QProgressBar, QToolButton,
)
from PySide6.QtCore import Qt, QTimer, QUrl, QSize, Signal, QEvent
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput, QMediaMetaData
from PySide6.QtMultimediaWidgets import QVideoWidget
import qtawesome as qta

from ..models.channel import Channel
from ..services.dlna_client import DLNACastService, DLNADevice
from ..services.stream_proxy import get_stream_proxy


class VideoPlayerComponent(QWidget):
    """Native Qt video player with controls and casting."""

    error = Signal(str)
    next_requested = Signal()
    prev_requested = Signal()
    theater_changed = Signal(bool)
    toggle_fullscreen_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_channel: Optional[Channel] = None
        self._is_playing = False
        self._dlna_service = DLNACastService()
        self._stream_proxy = get_stream_proxy()
        self._audio_tracks: List[dict] = []
        self._subtitle_tracks: List[dict] = []
        self._current_audio = 0
        self._current_subtitle = -1
        self._resume_ms = 0
        self._retry_count = 0
        self._max_retries = 3
        self._original_url = ""
        self._ext_fallbacks = ["mkv", "ts", "mp4", "avi"]
        self._ext_index = 0
        self._current_playback_url = ""
        self._episode_context: List[Channel] = []
        self._system_boost = 100
        self._muted = False
        self._last_volume = 100
        self._is_theater = False
        self._chrome_visible = True
        self._seek_bar_normal_visible = False

        # Auto-retry for transient MKV/WebM errors
        self._mkv_retry_timer = QTimer()
        self._mkv_retry_timer.setSingleShot(True)
        self._mkv_retry_timer.timeout.connect(self._do_mkv_retry)

        # Deferred fallback timer to break synchronous error cascades
        self._fallback_timer = QTimer()
        self._fallback_timer.setSingleShot(True)
        self._fallback_timer.timeout.connect(self._do_fallback_load)
        self._pending_fallback_url = ""

        self._setup_player()
        self._setup_ui()

    def _setup_player(self):
        self._audio_output = QAudioOutput()
        self._audio_output.setVolume(1.0)
        self._player = QMediaPlayer(self)
        self._player.setAudioOutput(self._audio_output)
        self._video_widget = QVideoWidget(self)
        self._player.setVideoOutput(self._video_widget)

        self._player.playbackStateChanged.connect(self._on_state_changed)
        self._player.errorOccurred.connect(self._on_error)
        self._player.bufferProgressChanged.connect(self._on_buffer_progress)
        self._player.mediaStatusChanged.connect(self._on_media_status)
        self._player.positionChanged.connect(self._on_position_changed)
        self._player.durationChanged.connect(self._on_duration_changed)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Top info bar
        self._info_bar = QWidget()
        self._info_bar.setObjectName("infoBar")
        info_layout = QHBoxLayout(self._info_bar)
        info_layout.setContentsMargins(16, 10, 16, 10)
        self._channel_label = QLabel("Select a channel")
        self._channel_label.setStyleSheet("font-weight: 700; font-size: 15px;")
        info_layout.addWidget(self._channel_label)
        info_layout.addStretch()
        self._quality_badge = QLabel("")
        self._quality_badge.setStyleSheet(
            "background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #22c55e, stop:1 #16a34a);"
            "color: white; padding: 3px 10px; border-radius: 6px; font-size: 10px; font-weight: bold;"
        )
        self._quality_badge.setVisible(False)
        info_layout.addWidget(self._quality_badge)
        layout.addWidget(self._info_bar)

        # Video area with overlays
        self._video_area = QFrame()
        video_layout = QVBoxLayout(self._video_area)
        video_layout.setContentsMargins(0, 0, 0, 0)
        video_layout.addWidget(self._video_widget, 1)
        self._video_widget.setStyleSheet("background-color: #000000;")
        layout.addWidget(self._video_area, 1)

        # YouTube-style seek bar — shown only for VOD/series content
        self._seek_bar = QWidget()
        self._seek_bar.setObjectName("seekBar")
        seek_layout = QHBoxLayout(self._seek_bar)
        seek_layout.setContentsMargins(16, 4, 16, 4)
        seek_layout.setSpacing(12)

        self._time_label = QLabel("0:00")
        self._time_label.setStyleSheet("font-size: 12px; min-width: 44px; color: rgba(255,255,255,0.85);")
        seek_layout.addWidget(self._time_label)

        self._seek_slider = QSlider(Qt.Horizontal)
        self._seek_slider.setRange(0, 0)
        self._seek_slider.setTracking(False)   # do NOT fire valueChanged during drag
        self._seek_slider.setSingleStep(5000)  # 5 s per arrow key
        self._seek_slider.setPageStep(30000)   # 30 s per PgUp/PgDn
        # Stylesheet: YouTube-style thin bar with gradient progress
        self._seek_slider.setStyleSheet("""
            QSlider { margin: 6px 0; }
            QSlider::groove:horizontal {
                height: 4px;
                background: rgba(255,255,255,0.20);
                border-radius: 2px;
            }
            QSlider::groove:horizontal:hover { height: 6px; margin: -1px 0; }
            QSlider::handle:horizontal {
                background: #ffffff;
                width: 14px; height: 14px;
                margin: -5px 0;
                border-radius: 7px;
                border: 2px solid #a855f7;
            }
            QSlider::handle:horizontal:hover {
                width: 18px; height: 18px;
                margin: -7px 0;
                border-radius: 9px;
                border: 2px solid #d08cff;
            }
            QSlider::sub-page:horizontal {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 #38bdf8, stop:0.5 #a855f7, stop:1 #f472b6);
                border-radius: 3px;
            }
        """)
        # Debounce timer: seek fires 120ms after the last drag movement
        self._seek_debounce = QTimer()
        self._seek_debounce.setSingleShot(True)
        self._seek_debounce.setInterval(120)
        self._seek_debounce.timeout.connect(self._do_seek)
        self._pending_seek_value = 0

        self._seek_slider.sliderMoved.connect(self._on_slider_moved)   # live label
        self._seek_slider.sliderReleased.connect(self._on_slider_released)  # final seek
        self._seek_slider.valueChanged.connect(self._on_seek_value_changed)  # keyboard
        seek_layout.addWidget(self._seek_slider, 1)

        self._duration_label = QLabel("0:00")
        self._duration_label.setStyleSheet("font-size: 12px; min-width: 44px; color: rgba(255,255,255,0.55);")
        seek_layout.addWidget(self._duration_label)

        self._seek_bar.setVisible(False)
        layout.addWidget(self._seek_bar)

        # Buffering overlay
        self._buffer_overlay = QWidget(self._video_area)
        self._buffer_overlay.setObjectName("bufferOverlay")
        self._buffer_overlay.setVisible(False)
        buf_layout = QVBoxLayout(self._buffer_overlay)
        self._buffer_label = QLabel("Buffering...")
        self._buffer_label.setAlignment(Qt.AlignCenter)
        self._buffer_label.setStyleSheet("font-size: 14px;")
        buf_layout.addStretch()
        buf_layout.addWidget(self._buffer_label)
        buf_layout.addStretch()

        # Error overlay
        self._error_overlay = QWidget(self._video_area)
        self._error_overlay.setObjectName("errorOverlay")
        self._error_overlay.setVisible(False)
        err_layout = QVBoxLayout(self._error_overlay)
        self._error_label = QLabel("Failed to load stream")
        self._error_label.setAlignment(Qt.AlignCenter)
        self._error_label.setStyleSheet("font-size: 16px; font-weight: 500;")
        err_layout.addStretch()
        err_layout.addWidget(self._error_label)
        retry_btn = QPushButton("Retry")
        retry_btn.setObjectName("primary")
        retry_btn.clicked.connect(self._retry_playback)
        err_layout.addWidget(retry_btn, alignment=Qt.AlignCenter)
        back_btn = QPushButton("Go Back")
        back_btn.clicked.connect(self._handle_error_back)
        err_layout.addWidget(back_btn, alignment=Qt.AlignCenter)
        err_layout.addStretch()

        # Welcome overlay
        self._welcome = QWidget(self._video_area)
        self._welcome.setObjectName("welcomeOverlay")
        wel_layout = QVBoxLayout(self._welcome)
        wel_msg = QLabel("Select a channel to start watching")
        wel_msg.setAlignment(Qt.AlignCenter)
        wel_msg.setStyleSheet("font-size: 16px;")
        wel_layout.addStretch()
        wel_layout.addWidget(wel_msg)
        wel_layout.addStretch()

        # Let mouse events pass through overlays to the video widget
        for overlay in (self._buffer_overlay, self._error_overlay, self._welcome):
            overlay.setAttribute(Qt.WA_TransparentForMouseEvents, True)

        # Double-click + mouse-move tracking for theater mode
        self._video_widget.setMouseTracking(True)
        self._video_widget.installEventFilter(self)

        # Timer to auto-hide chrome after 3 s of mouse inactivity
        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.setInterval(3000)
        self._hide_timer.timeout.connect(self._hide_chrome)

        # Control bar
        self._control_bar = QWidget()
        self._control_bar.setObjectName("controlBar")
        ctrl_layout = QHBoxLayout(self._control_bar)
        ctrl_layout.setContentsMargins(16, 8, 16, 8)
        ctrl_layout.setSpacing(6)

        _ICON_SZ = QSize(22, 22)
        _BTN_SZ = QSize(38, 38)

        self._prev_btn = QToolButton()
        self._prev_btn.setIcon(qta.icon("mdi.skip-previous", color="#d08cff"))
        self._prev_btn.setIconSize(_ICON_SZ)
        self._prev_btn.setFixedSize(_BTN_SZ)
        self._prev_btn.setToolTip("Previous")
        self._prev_btn.clicked.connect(self.prev_requested.emit)
        ctrl_layout.addWidget(self._prev_btn)

        self._play_btn = QToolButton()
        self._play_icon   = qta.icon("mdi.play-circle",  color="#ffffff")
        self._pause_icon  = qta.icon("mdi.pause-circle", color="#ffffff")
        self._play_btn.setIcon(self._play_icon)
        self._play_btn.setIconSize(QSize(30, 30))
        self._play_btn.setFixedSize(QSize(44, 44))
        self._play_btn.setToolTip("Play / Pause")
        self._play_btn.clicked.connect(self._toggle_play)
        ctrl_layout.addWidget(self._play_btn)

        self._next_btn = QToolButton()
        self._next_btn.setIcon(qta.icon("mdi.skip-next", color="#d08cff"))
        self._next_btn.setIconSize(_ICON_SZ)
        self._next_btn.setFixedSize(_BTN_SZ)
        self._next_btn.setToolTip("Next")
        self._next_btn.clicked.connect(self.next_requested.emit)
        ctrl_layout.addWidget(self._next_btn)

        # Volume
        vol_icon = QLabel()
        vol_icon.setPixmap(qta.icon("mdi.volume-high", color="#7b90b8").pixmap(QSize(18, 18)))
        ctrl_layout.addWidget(vol_icon)
        self._volume_slider = QSlider(Qt.Horizontal)
        self._volume_slider.setRange(0, 100)
        self._volume_slider.setValue(100)
        self._volume_slider.setFixedWidth(90)
        self._volume_slider.setToolTip("Volume")
        self._volume_slider.valueChanged.connect(self._on_volume)
        ctrl_layout.addWidget(self._volume_slider)
        self._volume_label = QLabel("100%")
        self._volume_label.setStyleSheet("font-size: 11px; min-width: 34px;")
        ctrl_layout.addWidget(self._volume_label)

        ctrl_layout.addStretch()

        # Boost
        boost_icon = QLabel()
        boost_icon.setPixmap(qta.icon("mdi.amplifier", color="#7b90b8").pixmap(QSize(16, 16)))
        ctrl_layout.addWidget(boost_icon)
        self._boost_slider = QSlider(Qt.Horizontal)
        self._boost_slider.setRange(100, 200)
        self._boost_slider.setValue(100)
        self._boost_slider.setFixedWidth(70)
        self._boost_slider.setToolTip("Audio boost")
        self._boost_slider.valueChanged.connect(self._on_boost)
        ctrl_layout.addWidget(self._boost_slider)

        # Rate
        self._rate_combo = QComboBox()
        self._rate_combo.addItems(["0.5×", "0.75×", "1×", "1.25×", "1.5×", "2×"])
        self._rate_combo.setCurrentIndex(2)
        self._rate_combo.setFixedWidth(68)
        self._rate_combo.setToolTip("Playback speed")
        self._rate_combo.currentTextChanged.connect(self._on_rate)
        ctrl_layout.addWidget(self._rate_combo)

        self._audio_btn = QToolButton()
        self._audio_btn.setIcon(qta.icon("mdi.waveform", color="#d08cff"))
        self._audio_btn.setIconSize(_ICON_SZ)
        self._audio_btn.setFixedSize(_BTN_SZ)
        self._audio_btn.setToolTip("Audio tracks")
        self._audio_btn.clicked.connect(self._show_audio_selector)
        ctrl_layout.addWidget(self._audio_btn)

        self._sub_btn = QToolButton()
        self._sub_btn.setIcon(qta.icon("mdi.subtitles-outline", color="#d08cff"))
        self._sub_btn.setIconSize(_ICON_SZ)
        self._sub_btn.setFixedSize(_BTN_SZ)
        self._sub_btn.setToolTip("Subtitles")
        self._sub_btn.clicked.connect(self._show_subtitle_selector)
        ctrl_layout.addWidget(self._sub_btn)

        self._cast_btn = QToolButton()
        self._cast_btn.setIcon(qta.icon("mdi.cast", color="#7b90b8"))
        self._cast_btn.setIconSize(_ICON_SZ)
        self._cast_btn.setFixedSize(_BTN_SZ)
        self._cast_btn.setToolTip("Cast to device")
        self._cast_btn.clicked.connect(self._show_cast_dialog)
        ctrl_layout.addWidget(self._cast_btn)

        self._fs_btn = QToolButton()
        self._fs_btn.setIcon(qta.icon("mdi.fullscreen", color="#7b90b8"))
        self._fs_btn.setIconSize(_ICON_SZ)
        self._fs_btn.setFixedSize(_BTN_SZ)
        self._fs_btn.setToolTip("Fullscreen (F11)")
        self._fs_btn.clicked.connect(self._toggle_fullscreen)
        ctrl_layout.addWidget(self._fs_btn)

        layout.addWidget(self._control_bar)

        self._update_overlays()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._position_overlays()

    def _position_overlays(self):
        size = self._video_area.size()
        for overlay in (self._buffer_overlay, self._error_overlay, self._welcome):
            overlay.setGeometry(0, 0, size.width(), size.height())

    def _update_overlays(self):
        self._welcome.setVisible(not self._is_playing)
        self._buffer_overlay.setVisible(False)
        self._error_overlay.setVisible(False)

    def set_resume_position(self, ms: int):
        self._resume_ms = ms

    def set_episode_context(self, episodes: List[Channel]):
        self._episode_context = episodes

    def play_channel(self, channel: Channel):
        self._current_channel = channel
        self._retry_count = 0
        self._ext_index = 0
        self._original_url = ""
        self._mkv_auto_retried = False
        self._current_playback_url = channel.url
        self._channel_label.setText(channel.name)
        self._detect_quality(channel.name)

        # Show seek bar for non-live content
        content_type = getattr(channel, "content_type", "live")
        is_seekable = content_type != "live"
        self._seek_bar_normal_visible = is_seekable
        self._seek_bar.setVisible(is_seekable)
        if not is_seekable:
            self._seek_slider.setRange(0, 0)
            self._time_label.setText("0:00")
            self._duration_label.setText("0:00")

        url = channel.url
        if self._stream_proxy.is_throttle_enabled():
            if not self._stream_proxy.is_running():
                asyncio.create_task(self._start_proxy_and_play(channel))
                return
            url = self._stream_proxy.register_stream(channel.url)

        self._current_playback_url = url
        self._load_stream(url)

    def _load_stream(self, url: str):
        self._current_playback_url = url
        self._player.stop()
        self._is_playing = False
        self._welcome.setVisible(False)
        self._error_overlay.setVisible(False)
        self._buffer_overlay.setVisible(True)
        self._position_overlays()

        self._player.setSource(QUrl(url))
        self._player.play()

    async def _start_proxy_and_play(self, channel: Channel):
        try:
            await self._stream_proxy.start()
            self.play_channel(channel)
        except Exception as e:
            self._on_error(QMediaPlayer.Error.ResourceError, f"Proxy error: {e}")

    def _detect_quality(self, name: str):
        name_u = name.upper()
        if "4K" in name_u or "UHD" in name_u or "2160" in name_u:
            self._quality_badge.setText("4K")
            self._quality_badge.setStyleSheet(
                "background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #a855f7, stop:1 #d946ef);"
                "color: white; padding: 3px 10px; border-radius: 6px; font-size: 10px; font-weight: bold;"
            )
        elif "FHD" in name_u or "1080" in name_u:
            self._quality_badge.setText("FHD")
            self._quality_badge.setStyleSheet(
                "background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #3b82f6, stop:1 #06b6d4);"
                "color: white; padding: 3px 10px; border-radius: 6px; font-size: 10px; font-weight: bold;"
            )
        elif "HD" in name_u or "720" in name_u:
            self._quality_badge.setText("HD")
            self._quality_badge.setStyleSheet(
                "background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #22c55e, stop:1 #10b981);"
                "color: white; padding: 3px 10px; border-radius: 6px; font-size: 10px; font-weight: bold;"
            )
        elif "SD" in name_u or "480" in name_u:
            self._quality_badge.setText("SD")
            self._quality_badge.setStyleSheet(
                "background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #f59e0b, stop:1 #f97316);"
                "color: white; padding: 3px 10px; border-radius: 6px; font-size: 10px; font-weight: bold;"
            )
        else:
            self._quality_badge.setText("")
        self._quality_badge.setVisible(bool(self._quality_badge.text()))

    def _on_state_changed(self, state):
        self._is_playing = state == QMediaPlayer.PlaybackState.PlayingState
        self._play_btn.setIcon(self._pause_icon if self._is_playing else self._play_icon)

    def _on_media_status(self, status):
        if status == QMediaPlayer.MediaStatus.LoadedMedia:
            self._buffer_overlay.setVisible(False)
            self._is_playing = True
            if self._resume_ms > 0:
                self._player.setPosition(self._resume_ms)
                self._resume_ms = 0
        elif status == QMediaPlayer.MediaStatus.EndOfMedia:
            self._is_playing = False
            # For live streams or very short playback, treat as an error
            content_type = getattr(self._current_channel, "content_type", "live")
            if content_type == "live" or self._player.position() < 5000:
                self._error_label.setText("Stream ended unexpectedly")
                self._error_overlay.setVisible(True)
                self._position_overlays()
        elif status == QMediaPlayer.MediaStatus.InvalidMedia:
            self._buffer_overlay.setVisible(False)
            self._is_playing = False
            # Extension fallback and error UI are handled by _on_error to avoid double attempts
        elif status == QMediaPlayer.MediaStatus.StalledMedia:
            self._buffer_overlay.setVisible(True)
            self._buffer_label.setText("Stalled... reconnecting")

    def _on_buffer_progress(self, progress):
        if progress < 100 and self._player.playbackState() != QMediaPlayer.PlaybackState.PlayingState:
            self._buffer_overlay.setVisible(True)
            self._buffer_label.setText(f"Buffering... {progress}%")
        else:
            self._buffer_overlay.setVisible(False)

    def _on_position_changed(self, position: int):
        # Never override slider position while user is dragging
        if self._seek_slider.isSliderDown():
            return
        # CRITICAL: block signals so setValue() doesn't emit valueChanged,
        # which would loop back to _on_seek_value_changed → setPosition()
        # and flood the decoder with ~25 unnecessary seeks/sec (at 25fps).
        self._seek_slider.blockSignals(True)
        self._seek_slider.setValue(position)
        self._seek_slider.blockSignals(False)
        self._time_label.setText(self._format_time(position))

    def _on_duration_changed(self, duration: int):
        self._seek_slider.setRange(0, duration)
        self._duration_label.setText(self._format_time(duration))

    def _on_slider_moved(self, value: int):
        """Called continuously while dragging — update label only."""
        self._time_label.setText(self._format_time(value))
        # Schedule a debounced seek so the video previews roughly where we're dragging
        self._pending_seek_value = value
        self._seek_debounce.start()

    def _on_slider_released(self):
        """Called when mouse button is released — do the definitive seek."""
        self._seek_debounce.stop()
        self._do_seek()

    def _do_seek(self):
        """Actually seek the player to the pending value."""
        if abs(self._player.position() - self._pending_seek_value) > 500:
            self._player.setPosition(self._pending_seek_value)

    def _on_seek_value_changed(self, value: int):
        """Only used for keyboard navigation (arrow/page keys), not mouse drag."""
        if not self._seek_slider.isSliderDown():
            if abs(self._player.position() - value) > 500:
                self._player.setPosition(value)
            self._time_label.setText(self._format_time(value))

    @staticmethod
    def _format_time(ms: int) -> str:
        s = ms // 1000
        m = s // 60
        h = m // 60
        s %= 60
        m %= 60
        if h:
            return f"{h}:{m:02d}:{s:02d}"
        return f"{m}:{s:02d}"

    def _on_error(self, error_code, error_string):
        print(f"Media error {error_code}: {error_string}")
        self._buffer_overlay.setVisible(False)
        self._is_playing = False

        # Detect MKV/WebM premature end / seek errors
        err_lower = error_string.lower()
        is_mkv_premature = "ended prematurely" in err_lower or "premature" in err_lower
        is_mkv_seek_fail = "seek to desired resync point failed" in err_lower or "resync point" in err_lower
        is_mkv_error = "matroska" in err_lower or "webm" in err_lower

        if is_mkv_premature or is_mkv_seek_fail or is_mkv_error:
            # Don't try extension fallback — the file itself may be damaged/incomplete
            pos = self._player.position()
            dur = self._player.duration()
            if dur > 0 and pos > 0 and pos >= dur * 0.95:
                # Near the end — probably just a truncated file we mostly finished
                self._error_label.setText("Playback complete\nFile may be truncated")
                self._error_overlay.setVisible(True)
                self._position_overlays()
                self.error.emit(error_string)
                return
            # Auto-retry once for transient MKV issues (network hiccup, partial cache)
            if not self._mkv_auto_retried and pos > 0:
                self._mkv_auto_retried = True
                self._resume_ms = max(0, pos - 5000)  # Resume ~5 s before failure
                self._mkv_retry_timer.start(1500)
                self._buffer_overlay.setVisible(True)
                self._buffer_label.setText("Reconnecting...")
                return
            # Retry exhausted — show error
            if is_mkv_seek_fail:
                self._error_label.setText("Seek failed in MKV/WebM\nFile may be damaged or incomplete")
            else:
                self._error_label.setText("Stream ended unexpectedly\nMKV/WebM file may be incomplete")
            self._error_overlay.setVisible(True)
            self._position_overlays()
            self.error.emit(error_string)
            return

        if self._try_next_extension():
            return
        self._error_label.setText(f"Failed to load stream\n{error_string}")
        self._error_overlay.setVisible(True)
        self._position_overlays()
        self.error.emit(error_string)

    def _try_next_extension(self) -> bool:
        if not self._current_channel:
            return False
        url = self._current_channel.url
        if "/series/" not in url and "/movie/" not in url:
            return False
        if not self._original_url:
            self._original_url = url
        if self._ext_index >= len(self._ext_fallbacks):
            return False
        import re
        base = re.sub(r'\.[a-zA-Z0-9]+$', '', self._original_url)
        new_url = f"{base}.{self._ext_fallbacks[self._ext_index]}"
        self._ext_index += 1
        # Skip if this produces the exact same URL we already tried
        if new_url == self._current_playback_url or new_url == self._original_url:
            return self._try_next_extension()
        self._current_playback_url = new_url
        # Defer load to break synchronous signal cascades from setSource()
        self._pending_fallback_url = new_url
        self._fallback_timer.start(100)
        return True

    def _do_fallback_load(self):
        """Load the pending fallback URL after a brief deferral."""
        if self._pending_fallback_url:
            self._load_stream(self._pending_fallback_url)
            self._pending_fallback_url = ""

    def _do_mkv_retry(self):
        """Auto-retry the same MKV/WebM stream after a transient error."""
        if not self._current_channel:
            return
        print(f"Auto-retrying MKV stream at ~{self._resume_ms} ms")
        self._error_overlay.setVisible(False)
        self._load_stream(self._current_playback_url)

    def toggle_play(self):
        """Toggle play/pause (public API for keyboard shortcuts)."""
        if self._player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self._player.pause()
        else:
            self._player.play()

    def _toggle_play(self):
        self.toggle_play()

    def seek_relative(self, ms: int):
        """Seek forward/backward by ms milliseconds."""
        pos = self._player.position()
        dur = self._player.duration()
        new_pos = max(0, min(dur if dur > 0 else pos, pos + ms))
        self._player.setPosition(new_pos)

    def adjust_volume(self, delta: int):
        """Adjust volume by delta percentage points."""
        new_vol = max(0, min(100, int(self._audio_output.volume() * 100) + delta))
        self._audio_output.setVolume(new_vol / 100.0)
        self._volume_slider.setValue(new_vol)
        self._volume_label.setText(f"{new_vol}%")
        if new_vol > 0 and self._muted:
            self._muted = False

    def toggle_mute(self):
        """Toggle mute/unmute."""
        if self._muted:
            self._audio_output.setVolume(self._last_volume / 100.0)
            self._volume_slider.setValue(self._last_volume)
            self._volume_label.setText(f"{self._last_volume}%")
            self._muted = False
        else:
            self._last_volume = int(self._audio_output.volume() * 100)
            self._audio_output.setVolume(0.0)
            self._volume_slider.setValue(0)
            self._volume_label.setText("Muted")
            self._muted = True

    def _on_volume(self, value):
        self._audio_output.setVolume(value / 100.0)
        self._volume_label.setText(f"{value}%")
        self._last_volume = value
        if value > 0 and self._muted:
            self._muted = False

    def _on_boost(self, value):
        self._system_boost = value

    def _on_rate(self, text):
        try:
            rate = float(text.replace("×", "").replace("x", "").strip())
            self._player.setPlaybackRate(rate)
        except ValueError:
            pass

    @staticmethod
    def _track_label(meta, fallback_index: int, prefix: str = "") -> str:
        """Build a human-readable label from QMediaMetaData."""
        try:
            lang = meta.stringValue(QMediaMetaData.Key.Language) if meta else ""
            title = meta.stringValue(QMediaMetaData.Key.Title) if meta else ""
        except Exception:
            lang = title = ""
        parts = [p for p in (prefix, lang, title) if p]
        if parts:
            return " ".join(parts)
        return f"Track {fallback_index + 1}"

    def _show_audio_selector(self):
        tracks = []
        audio_meta_list = self._player.audioTracks()
        for i, meta in enumerate(audio_meta_list):
            label = self._track_label(meta, i)
            tracks.append({"index": i, "label": label})
        if not tracks:
            QMessageBox.information(self, "Audio Tracks", "No audio tracks available")
            return
        dialog = TrackSelectorDialog("Audio", tracks, self._current_audio, self)
        if dialog.exec() == QDialog.Accepted:
            self._current_audio = dialog.selected_index
            self._player.setActiveAudioTrack(dialog.selected_index)

    def _show_subtitle_selector(self):
        tracks = [{"index": -1, "label": "Off"}]
        sub_meta_list = self._player.subtitleTracks()
        for i, meta in enumerate(sub_meta_list):
            label = self._track_label(meta, i, prefix="Sub")
            tracks.append({"index": i, "label": label})
        dialog = TrackSelectorDialog("Subtitles", tracks, self._current_subtitle, self)
        if dialog.exec() == QDialog.Accepted:
            self._current_subtitle = dialog.selected_index
            self._player.setActiveSubtitleTrack(dialog.selected_index)

    def _show_cast_dialog(self):
        dialog = CastDialog(self._dlna_service, self._current_channel, self)
        dialog.exec()

    def _toggle_fullscreen(self):
        self.toggle_fullscreen_requested.emit()

    def _set_theater_mode(self, active: bool):
        self._is_theater = active
        self._fs_btn.setIcon(qta.icon("mdi.fullscreen-exit" if active else "mdi.fullscreen", color="#7b90b8"))
        if active:
            self._hide_chrome()
        else:
            self._show_chrome_permanently()
        self.theater_changed.emit(active)

    def _show_chrome_temporarily(self):
        self._info_bar.setVisible(True)
        self._seek_bar.setVisible(self._seek_bar_normal_visible)
        self._control_bar.setVisible(True)
        self._chrome_visible = True
        self._hide_timer.start(3000)

    def _hide_chrome(self):
        self._info_bar.setVisible(False)
        self._seek_bar.setVisible(False)
        self._control_bar.setVisible(False)
        self._chrome_visible = False

    def _show_chrome_permanently(self):
        self._info_bar.setVisible(True)
        self._seek_bar.setVisible(self._seek_bar_normal_visible)
        self._control_bar.setVisible(True)
        self._chrome_visible = True
        self._hide_timer.stop()

    def set_theater_mode(self, active: bool):
        self._set_theater_mode(active)

    def eventFilter(self, obj, event):
        if obj is self._video_widget:
            if event.type() == QEvent.Type.MouseButtonDblClick:
                self._toggle_fullscreen()
                return True
            if event.type() == QEvent.Type.MouseMove and self._is_theater:
                self._show_chrome_temporarily()
        return super().eventFilter(obj, event)

    def _retry_playback(self):
        if not self._current_channel:
            return
        self._retry_count += 1
        if self._retry_count <= self._max_retries:
            self._error_overlay.setVisible(False)
            self._buffer_overlay.setVisible(True)
            self._load_stream(self._current_playback_url)
        else:
            self._error_label.setText("Unable to connect\nMaximum retry attempts reached.")

    def _handle_error_back(self):
        self._error_overlay.setVisible(False)
        self._retry_count = 0
        self._ext_index = 0
        self._original_url = ""
        self._current_playback_url = ""
        self._pending_fallback_url = ""
        self._welcome.setVisible(True)
        self.stop()

    def stop(self):
        self._player.stop()
        self._is_playing = False
        self._welcome.setVisible(True)
        self._buffer_overlay.setVisible(False)
        self._error_overlay.setVisible(False)
        self._mkv_retry_timer.stop()
        self._seek_debounce.stop()
        self._hide_timer.stop()
        self._fallback_timer.stop()
        self._pending_fallback_url = ""

    def cleanup_resources(self):
        """Stop DLNA casting and stream proxy to prevent background leaks."""
        try:
            asyncio.create_task(self._dlna_service.stop_casting())
        except Exception:
            pass
        if self._stream_proxy.is_running():
            try:
                asyncio.create_task(self._stream_proxy.stop())
            except Exception:
                pass

    def get_position_info(self) -> tuple:
        return (self._player.position(), self._player.duration())


class TrackSelectorDialog(QDialog):
    def __init__(self, title: str, tracks: List[dict], current: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumSize(300, 250)
        self.selected_index = current
        layout = QVBoxLayout(self)
        self._list = QListWidget()
        for t in tracks:
            item = QListWidgetItem(t["label"])
            item.setData(Qt.UserRole, t["index"])
            self._list.addItem(item)
            if t["index"] == current:
                item.setSelected(True)
        self._list.itemClicked.connect(self._select)
        layout.addWidget(self._list)
        btn = QPushButton("Close")
        btn.clicked.connect(self.accept)
        layout.addWidget(btn)

    def _select(self, item):
        self.selected_index = item.data(Qt.UserRole)
        self.accept()


class CastDialog(QDialog):
    def __init__(self, dlna: DLNACastService, channel: Optional[Channel], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Cast to Device")
        self.setMinimumSize(400, 300)
        self._dlna = dlna
        self._channel = channel
        layout = QVBoxLayout(self)
        self._status = QLabel("Scanning for devices...")
        layout.addWidget(self._status)
        self._list = QListWidget()
        self._list.itemClicked.connect(self._cast_to)
        layout.addWidget(self._list)
        self._scan_btn = QPushButton("Scan")
        self._scan_btn.clicked.connect(self._scan)
        layout.addWidget(self._scan_btn)
        self._stop_btn = QPushButton("Stop Casting")
        self._stop_btn.clicked.connect(self._stop_cast)
        layout.addWidget(self._stop_btn)
        QTimer.singleShot(100, self._scan)

    def _scan(self):
        self._list.clear()
        self._status.setText("Scanning...")
        asyncio.create_task(self._do_scan())

    async def _do_scan(self):
        devices = await self._dlna.discover_devices()
        self._list.clear()
        if not devices:
            self._status.setText("No devices found")
            return
        self._status.setText(f"Found {len(devices)} device(s)")
        for d in devices:
            item = QListWidgetItem(d.name)
            item.setData(Qt.UserRole, d)
            self._list.addItem(item)

    def _cast_to(self, item):
        device = item.data(Qt.UserRole)
        if self._channel:
            asyncio.create_task(self._dlna.cast_to_device(device, self._channel.url, self._channel.name))
            self._status.setText(f"Casting to {device.name}")

    def _stop_cast(self):
        asyncio.create_task(self._dlna.stop_casting())
        self._status.setText("Casting stopped")
