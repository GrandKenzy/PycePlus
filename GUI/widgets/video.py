"""
PycePlus.GUI.widgets.video
VideoPlayer widget — loads video frame-by-frame using cv2 (OpenCV).
Falls back to a placeholder if cv2 is not installed.

The video is decoded in a background thread; only the latest frame
is held in memory (no full preload).

Parameters
----------
source     : str   path or URL to video file
width      : int   display width (0 = natural)
height     : int   display height (0 = natural)
autoplay   : bool
loop       : bool
fps        : float override frame rate (0 = use video's native fps)
"""
from __future__ import annotations

import os
import threading
import time
from typing import Callable

import pygame

from PycePlus.GUI.base import Base
from PycePlus.UI.tools.color import Color

try:
    import cv2 as _cv2
    _HAS_CV2 = True
except ImportError:
    _HAS_CV2 = False


# ──────────────────────────────────────────────────────────────────────────────
# VideoPlayer
# ──────────────────────────────────────────────────────────────────────────────

class VideoPlayer(Base):
    """Streaming video widget."""

    def __init__(
        self,
        father=None,
        source:   str   = "",
        width:    int   = 320,
        height:   int   = 240,
        autoplay: bool  = False,
        loop:     bool  = False,
        fps:      float = 0,
        style:    dict | None = None,
        on_end:   Callable | None = None,
        on_frame: Callable | None = None,
        x: int = 0,
        y: int = 0,
        name: str | None = None,
        page: str | None = None,
        visible: bool = True,
    ):
        _default = {
            "background_color": (0, 0, 0, 255),
            "border":           0,
        }
        _style = {**_default, **(style or {})}
        super().__init__(father, name, page, style=_style)

        self.source   = source
        self.loop     = loop
        self._fps_ovr = fps
        self._on_end  = on_end
        self._on_frame= on_frame
        self.visible  = visible

        self.rect    = pygame.Rect(x, y, width, height)
        self.texture = pygame.Surface((width, height), pygame.SRCALPHA)
        self.texture.fill((0, 0, 0, 255))

        # streaming state
        self._playing:  bool = False
        self._paused:   bool = False
        self._stopped:  bool = True
        self._pos:      float = 0.0     # current position seconds
        self._duration: float = 0.0
        self._nat_w:    int   = width
        self._nat_h:    int   = height
        self._native_fps: float = 30.0

        self._frame_lock   = threading.Lock()
        self._current_frame: pygame.Surface | None = None
        self._new_frame:    bool = False

        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()

        if not _HAS_CV2:
            self._draw_placeholder("cv2 not installed")
            self.mark_dirty()
            return

        if autoplay and source:
            self.play()
        else:
            self.mark_dirty()

    # ── playback control ─────────────────────────────────────────────────────

    def play(self, source: str | None = None) -> None:
        if source:
            self.source = source
        if not self.source or not _HAS_CV2:
            return
        self.stop()
        self._stop_event.clear()
        self._playing = True
        self._paused  = False
        self._stopped = False
        self._thread  = threading.Thread(
            target=self._decode_loop, daemon=True)
        self._thread.start()

    def pause(self) -> None:
        self._paused = not self._paused

    def stop(self) -> None:
        self._stop_event.set()
        self._playing = False
        self._paused  = False
        self._stopped = True
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        self._thread = None

    def seek(self, seconds: float) -> None:
        self._pos = max(0.0, seconds)

    @property
    def position(self) -> float:
        return self._pos

    @property
    def duration(self) -> float:
        return self._duration

    @property
    def is_playing(self) -> bool:
        return self._playing and not self._paused

    # ── decode thread ────────────────────────────────────────────────────────

    def _decode_loop(self) -> None:
        cap = _cv2.VideoCapture(self.source)
        if not cap.isOpened():
            self._draw_placeholder(f"Cannot open:\n{os.path.basename(self.source)}")
            self.mark_dirty()
            return

        self._native_fps  = cap.get(_cv2.CAP_PROP_FPS) or 30.0
        total_frames      = cap.get(_cv2.CAP_PROP_FRAME_COUNT)
        self._duration    = total_frames / self._native_fps if self._native_fps else 0
        fps               = self._fps_ovr or self._native_fps
        frame_delay       = 1.0 / max(fps, 1)

        self._nat_w = int(cap.get(_cv2.CAP_PROP_FRAME_WIDTH))
        self._nat_h = int(cap.get(_cv2.CAP_PROP_FRAME_HEIGHT))

        while not self._stop_event.is_set():
            if self._paused:
                time.sleep(0.05)
                continue

            t0 = time.perf_counter()
            ret, frame = cap.read()

            if not ret:
                if self.loop:
                    cap.set(_cv2.CAP_PROP_POS_FRAMES, 0)
                    self._pos = 0.0
                    continue
                else:
                    self._playing = False
                    self._stopped = True
                    if self._on_end:
                        self._on_end(self)
                    break

            self._pos = cap.get(_cv2.CAP_PROP_POS_MSEC) / 1000.0

            # Convert BGR → RGB → pygame Surface
            frame_rgb = _cv2.cvtColor(frame, _cv2.COLOR_BGR2RGB)
            w, h      = self.rect.width, self.rect.height
            fw, fh    = frame_rgb.shape[1], frame_rgb.shape[0]

            if (fw, fh) != (w, h):
                fw2 = w
                fh2 = int(fh * w / fw) if fw else h
                if fh2 > h:
                    fh2 = h
                    fw2 = int(fw * h / fh) if fh else w
                frame_rgb = _cv2.resize(frame_rgb, (fw2, fh2))
                fw, fh = fw2, fh2

            surf = pygame.surfarray.make_surface(
                frame_rgb.swapaxes(0, 1))

            with self._frame_lock:
                self._current_frame = surf
                self._new_frame     = True

            self.mark_dirty()

            if self._on_frame:
                self._on_frame(self, self._pos)

            elapsed = time.perf_counter() - t0
            sleep   = max(0.0, frame_delay - elapsed)
            self._stop_event.wait(sleep)

        cap.release()

    # ── draw helpers ─────────────────────────────────────────────────────────

    def _draw_placeholder(self, msg: str) -> None:
        w, h = self.rect.width, self.rect.height
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        surf.fill((20, 20, 20, 255))
        try:
            font = pygame.font.Font(None, 20)
            text = font.render(msg, True, (150, 150, 150))
            surf.blit(text, ((w - text.get_width())  // 2,
                              (h - text.get_height()) // 2))
        except Exception:
            pass
        with self._frame_lock:
            self._current_frame = surf
            self._new_frame     = True

    # ── render ────────────────────────────────────────────────────────────────

    def render_self(self) -> None:
        if self.texture is None:
            return

        w, h = self.rect.width, self.rect.height
        if self.texture.get_size() != (w, h):
            self.texture = pygame.Surface((w, h), pygame.SRCALPHA)

        self._style.fill_surface(self.texture)

        with self._frame_lock:
            if self._new_frame and self._current_frame is not None:
                frame = self._current_frame
                self._new_frame = False
            else:
                frame = self._current_frame

        if frame:
            fw, fh = frame.get_size()
            bx = (w - fw) // 2
            by = (h - fh) // 2
            self.texture.blit(frame, (bx, by))

        # Progress bar overlay
        if self._duration > 0:
            bar_h  = 4
            bar_y  = h - bar_h - 2
            prog   = min(1.0, self._pos / self._duration)
            bar_w  = int(w * prog)
            pygame.draw.rect(self.texture, (40, 40, 50, 200),
                             (0, bar_y, w, bar_h))
            if bar_w > 0:
                pygame.draw.rect(self.texture, (86, 156, 214, 220),
                                 (0, bar_y, bar_w, bar_h))

        # Paused icon
        if self._paused:
            try:
                font    = pygame.font.Font(None, 36)
                icon    = font.render("⏸", True, (200, 200, 200, 180))
                self.texture.blit(icon, (8, h - 36))
            except Exception:
                pass

        self._style.draw_border(self.texture)
        self.clear_dirty()

    def destroy(self) -> None:
        self.stop()
        super().destroy()
