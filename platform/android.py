"""
PycePlus.platform.android
=========================
Soporte de plataforma Android para PycePlus.

Detecta si estamos en Android (via python-for-android / Kivy ecosystem),
adapta las entradas táctiles a eventos de mouse de pygame, y expone
helpers para acceso a almacenamiento, vibración, sensores, etc.

Uso automático (no hace falta hacer nada):
    PycePlus detecta Android en __init__ y aplica automáticamente
    los adaptadores de entrada.

Uso manual:
    from PycePlus.platform.android import AndroidAdapter, is_android

    if is_android():
        adapter = AndroidAdapter()
        adapter.enable_touch_mouse()
        adapter.request_permission("CAMERA")
        adapter.vibrate(100)           # 100 ms
        path = adapter.get_external_storage()
"""
from __future__ import annotations

import os
import sys
import threading
from typing import Callable

import pygame

__all__ = [
    "is_android", "AndroidAdapter", "TouchEvent",
    "ANDROID_AVAILABLE",
]


# ──────────────────────────────────────────────────────────────────────────────
# Detección
# ──────────────────────────────────────────────────────────────────────────────

def is_android() -> bool:
    """True si ejecutamos bajo python-for-android / Android."""
    return (
        sys.platform == "android"
        or os.environ.get("ANDROID_ARGUMENT") is not None
        or os.environ.get("ANDROID_BOOTLOGO") is not None
        or os.path.exists("/data/data")  # directorio propio de Android
    )


ANDROID_AVAILABLE: bool = is_android()

try:
    import android          # type: ignore
    _ANDROID_MOD = android
except ImportError:
    _ANDROID_MOD = None

try:
    from android.permissions import request_permissions, Permission  # type: ignore
    _PERMS_AVAILABLE = True
except ImportError:
    _PERMS_AVAILABLE = False


# ──────────────────────────────────────────────────────────────────────────────
# TouchEvent
# ──────────────────────────────────────────────────────────────────────────────

class TouchEvent:
    """Representa un toque en pantalla táctil."""
    __slots__ = ("finger_id", "x", "y", "pressure", "dx", "dy", "phase")

    def __init__(
        self,
        finger_id: int,
        x: float, y: float,
        pressure: float = 1.0,
        dx: float = 0, dy: float = 0,
        phase: str = "began",   # "began" | "moved" | "ended"
    ):
        self.finger_id = finger_id
        self.x         = x
        self.y         = y
        self.pressure  = pressure
        self.dx        = dx
        self.dy        = dy
        self.phase     = phase

    def __repr__(self) -> str:
        return f"<TouchEvent finger={self.finger_id} ({self.x:.0f},{self.y:.0f}) {self.phase}>"


# ──────────────────────────────────────────────────────────────────────────────
# AndroidAdapter
# ──────────────────────────────────────────────────────────────────────────────

class AndroidAdapter:
    """
    Adaptador de plataforma Android.
    Gestiona entrada táctil, permisos, vibración, sensores y rutas.
    """

    def __init__(self):
        self._touches: dict[int, TouchEvent] = {}
        self._touch_callbacks: list[Callable[[TouchEvent], None]] = []
        self._mouse_emulation = False
        self._primary_finger: int | None = None

        # Escala táctil (pantallas Android usan coordenadas normalizadas 0-1)
        self._display_w, self._display_h = pygame.display.get_surface().get_size() \
            if pygame.display.get_surface() else (1080, 1920)

    # ── Touch → Mouse emulation ───────────────────────────────────────────

    def enable_touch_mouse(self, primary_only: bool = True) -> "AndroidAdapter":
        """
        Convierte eventos táctiles de pygame en eventos de mouse.
        Fundamental para que los widgets de PycePlus funcionen en Android
        sin cambios de código.

        Args:
            primary_only: solo el primer dedo emula el mouse
        """
        self._mouse_emulation = True
        self._primary_only    = primary_only
        return self

    def process_event(self, event: pygame.event.Event) -> list[pygame.event.Event]:
        """
        Procesa un evento pygame y devuelve eventos adicionales.

        Llama esto en el loop principal:
            for event in pygame.event.get():
                extra = adapter.process_event(event)
                for e in extra:
                    pygame.event.post(e)
                handle_event(event)
        """
        extra: list[pygame.event.Event] = []

        if event.type == pygame.FINGERDOWN:
            te = self._make_touch(event, "began")
            self._touches[event.finger_id] = te
            for cb in self._touch_callbacks:
                cb(te)

            if self._mouse_emulation:
                if self._primary_only and self._primary_finger is None:
                    self._primary_finger = event.finger_id
                if not self._primary_only or event.finger_id == self._primary_finger:
                    x, y = self._norm_to_px(event.x, event.y)
                    extra.append(pygame.event.Event(
                        pygame.MOUSEBUTTONDOWN,
                        pos=(x, y), button=1, touch=True,
                    ))

        elif event.type == pygame.FINGERMOTION:
            te = self._make_touch(event, "moved")
            self._touches[event.finger_id] = te
            for cb in self._touch_callbacks:
                cb(te)

            if self._mouse_emulation:
                if not self._primary_only or event.finger_id == self._primary_finger:
                    x, y = self._norm_to_px(event.x, event.y)
                    extra.append(pygame.event.Event(
                        pygame.MOUSEMOTION,
                        pos=(x, y), rel=(int(event.dx * self._display_w),
                                         int(event.dy * self._display_h)),
                        buttons=(1, 0, 0),
                    ))

        elif event.type == pygame.FINGERUP:
            te = self._make_touch(event, "ended")
            self._touches.pop(event.finger_id, None)
            for cb in self._touch_callbacks:
                cb(te)

            if self._mouse_emulation:
                if not self._primary_only or event.finger_id == self._primary_finger:
                    x, y = self._norm_to_px(event.x, event.y)
                    extra.append(pygame.event.Event(
                        pygame.MOUSEBUTTONUP,
                        pos=(x, y), button=1, touch=True,
                    ))
                    if event.finger_id == self._primary_finger:
                        self._primary_finger = None

        # Android back button → Escape
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_AC_BACK:
            extra.append(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE,
                                            mod=0, unicode=""))

        return extra

    def _norm_to_px(self, x: float, y: float) -> tuple[int, int]:
        """Coordenadas normalizadas (0-1) → píxeles de pantalla."""
        return (int(x * self._display_w), int(y * self._display_h))

    def _make_touch(self, event, phase: str) -> TouchEvent:
        x, y = self._norm_to_px(event.x, event.y)
        return TouchEvent(
            finger_id=event.finger_id,
            x=float(x), y=float(y),
            pressure=getattr(event, "pressure", 1.0),
            dx=getattr(event, "dx", 0) * self._display_w,
            dy=getattr(event, "dy", 0) * self._display_h,
            phase=phase,
        )

    def on_touch(self, cb: Callable[[TouchEvent], None]) -> "AndroidAdapter":
        """Registra un callback para eventos táctiles."""
        self._touch_callbacks.append(cb)
        return self

    @property
    def active_touches(self) -> list[TouchEvent]:
        return list(self._touches.values())

    # ── Display ───────────────────────────────────────────────────────────

    def set_display_size(self, w: int, h: int) -> None:
        """Actualizar si la ventana cambia de tamaño."""
        self._display_w = w
        self._display_h = h

    def request_fullscreen(self) -> None:
        """Activa pantalla completa (útil en Android)."""
        pygame.display.set_mode(
            (self._display_w, self._display_h),
            pygame.FULLSCREEN | pygame.NOFRAME
        )

    # ── Permissions ───────────────────────────────────────────────────────

    def request_permission(self, *permissions: str) -> None:
        """
        Solicita permisos de Android en tiempo de ejecución.

        Permisos comunes:
          "CAMERA", "READ_EXTERNAL_STORAGE", "WRITE_EXTERNAL_STORAGE",
          "RECORD_AUDIO", "ACCESS_FINE_LOCATION", "INTERNET"
        """
        if not _PERMS_AVAILABLE:
            return
        perms = [getattr(Permission, p, p) for p in permissions]
        request_permissions(perms)

    # ── Vibration ─────────────────────────────────────────────────────────

    def vibrate(self, milliseconds: int = 100) -> None:
        """Vibra el dispositivo."""
        try:
            if _ANDROID_MOD:
                _ANDROID_MOD.vibrate(milliseconds / 1000.0)
        except Exception:
            pass

    def vibrate_pattern(self, pattern_ms: list[int]) -> None:
        """
        Vibra con un patrón. Lista alternada de [off, on, off, on, ...]
        Ej: [0, 200, 100, 200] = espera 0ms, vibra 200ms, pausa 100ms, vibra 200ms.
        """
        def _pat():
            for i, ms in enumerate(pattern_ms):
                time_ms = ms
                if i % 2 == 1:  # on
                    self.vibrate(time_ms)
                    import time; time.sleep(time_ms / 1000.0)
                else:
                    import time; time.sleep(time_ms / 1000.0)
        threading.Thread(target=_pat, daemon=True).start()

    # ── Storage ───────────────────────────────────────────────────────────

    def get_files_dir(self) -> str:
        """Directorio de archivos interno de la app."""
        try:
            if _ANDROID_MOD:
                context = _ANDROID_MOD.mActivity
                return str(context.getFilesDir().getAbsolutePath())
        except Exception:
            pass
        return os.path.expanduser("~")

    def get_external_storage(self) -> str:
        """Directorio de almacenamiento externo (sdcard)."""
        # Variables de entorno estándar de Android
        for var in ("EXTERNAL_STORAGE", "SECONDARY_STORAGE"):
            path = os.environ.get(var)
            if path and os.path.exists(path):
                return path
        return "/sdcard"

    def get_cache_dir(self) -> str:
        """Directorio de caché de la app."""
        try:
            if _ANDROID_MOD:
                context = _ANDROID_MOD.mActivity
                return str(context.getCacheDir().getAbsolutePath())
        except Exception:
            pass
        return os.path.join(os.path.expanduser("~"), ".cache")

    # ── Screen orientation ────────────────────────────────────────────────

    def set_orientation(self, orientation: str = "landscape") -> None:
        """
        Sugiere la orientación de pantalla.
        orientation: "landscape" | "portrait" | "auto"
        """
        try:
            if _ANDROID_MOD:
                activity = _ANDROID_MOD.mActivity
                from jnius import autoclass  # type: ignore
                ActivityInfo = autoclass("android.content.pm.ActivityInfo")
                if orientation == "landscape":
                    activity.setRequestedOrientation(
                        ActivityInfo.SCREEN_ORIENTATION_LANDSCAPE)
                elif orientation == "portrait":
                    activity.setRequestedOrientation(
                        ActivityInfo.SCREEN_ORIENTATION_PORTRAIT)
                else:
                    activity.setRequestedOrientation(
                        ActivityInfo.SCREEN_ORIENTATION_UNSPECIFIED)
        except Exception:
            pass

    # ── Keyboard ──────────────────────────────────────────────────────────

    def show_keyboard(self) -> None:
        """Muestra el teclado virtual."""
        try:
            if _ANDROID_MOD:
                _ANDROID_MOD.show_keyboard()
        except Exception:
            pass

    def hide_keyboard(self) -> None:
        """Oculta el teclado virtual."""
        try:
            if _ANDROID_MOD:
                _ANDROID_MOD.hide_keyboard()
        except Exception:
            pass

    # ── Status bar ────────────────────────────────────────────────────────

    def hide_statusbar(self) -> None:
        """Oculta la barra de estado para pantalla completa real."""
        try:
            from jnius import autoclass  # type: ignore
            View = autoclass("android.view.View")
            activity = _ANDROID_MOD.mActivity
            window = activity.getWindow()
            decorView = window.getDecorView()
            decorView.setSystemUiVisibility(
                View.SYSTEM_UI_FLAG_FULLSCREEN |
                View.SYSTEM_UI_FLAG_HIDE_NAVIGATION |
                View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY
            )
        except Exception:
            pass

    # ── DPI ───────────────────────────────────────────────────────────────

    def get_dpi(self) -> float:
        """DPI real de la pantalla Android."""
        try:
            from jnius import autoclass  # type: ignore
            context = _ANDROID_MOD.mActivity
            dm = context.getResources().getDisplayMetrics()
            return float(dm.densityDpi)
        except Exception:
            from PycePlus.units import get_screen_dpi
            return get_screen_dpi()

    def __repr__(self) -> str:
        return f"<AndroidAdapter touches={len(self._touches)} emu={self._mouse_emulation}>"


# ──────────────────────────────────────────────────────────────────────────────
# Auto-init para PycePlus
# ──────────────────────────────────────────────────────────────────────────────

_global_adapter: AndroidAdapter | None = None

def get_adapter() -> AndroidAdapter | None:
    """Devuelve el AndroidAdapter global si estamos en Android."""
    return _global_adapter

def _auto_init() -> None:
    global _global_adapter
    if is_android() and _global_adapter is None:
        _global_adapter = AndroidAdapter()
        _global_adapter.enable_touch_mouse()

# Se llama desde PycePlus/__init__.py si is_android() es True