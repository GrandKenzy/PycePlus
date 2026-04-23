"""
PycePlus.units
==============
Sistema de medidas: px, percent (%), dpi, vw, vh.

Uso:
    from PycePlus.units import px, pct, dpi, vw, vh, resolve

    btn_width  = pct(50)   # 50% del contenedor/ventana
    btn_height = dpi(0.5)  # 0.5 pulgadas lógicas según DPI de pantalla
    label_x    = px(20)    # 20 píxeles absolutos
    header_w   = vw(80)    # 80% del ancho de viewport

    # Para resolver un valor al renderizar:
    actual_w = resolve(btn_width, parent_width=800)
"""
from __future__ import annotations

import ctypes
import sys
from dataclasses import dataclass
from typing import Union

import pygame

__all__ = [
    "UnitValue", "px", "pct", "dpi", "vw", "vh",
    "resolve", "resolve_rect",
    "get_screen_dpi", "UnitRect",
]


# ──────────────────────────────────────────────────────────────────────────────
# Screen DPI detection
# ──────────────────────────────────────────────────────────────────────────────

_DPI_CACHE: float | None = None

def get_screen_dpi() -> float:
    """
    Devuelve el DPI lógico de la pantalla principal.
    Intenta SDL → OS → fallback 96.
    """
    global _DPI_CACHE
    if _DPI_CACHE is not None:
        return _DPI_CACHE

    # SDL2 / pygame 2.x
    try:
        dpi_tuple = pygame.display.get_display_sizes()[0]  # (w, h) in mm not available here
    except Exception:
        pass

    # pygame ≥ 2.1.3 tiene get_display_dpi
    try:
        hdpi, vdpi, ddpi = pygame.display.get_display_dpi()  # type: ignore[attr-defined]
        _DPI_CACHE = float((hdpi + vdpi) / 2)
        return _DPI_CACHE
    except Exception:
        pass

    # Windows: ctypes shcore
    if sys.platform == "win32":
        try:
            shcore = ctypes.windll.shcore  # type: ignore[attr-defined]
            dpi = ctypes.c_uint(0)
            shcore.GetDpiForMonitor(None, 0, ctypes.byref(dpi), ctypes.byref(dpi))
            _DPI_CACHE = float(dpi.value) if dpi.value > 0 else 96.0
            return _DPI_CACHE
        except Exception:
            pass

    # Linux / X11
    try:
        import subprocess
        out = subprocess.check_output(["xdpyinfo"], stderr=subprocess.DEVNULL, timeout=2)
        for line in out.decode().splitlines():
            if "dots per inch" in line:
                _DPI_CACHE = float(line.split()[-3])
                return _DPI_CACHE
    except Exception:
        pass

    _DPI_CACHE = 96.0
    return _DPI_CACHE


# ──────────────────────────────────────────────────────────────────────────────
# UnitValue
# ──────────────────────────────────────────────────────────────────────────────

_UNIT_PX  = "px"
_UNIT_PCT = "pct"
_UNIT_DPI = "dpi"
_UNIT_VW  = "vw"
_UNIT_VH  = "vh"
_UNIT_EM  = "em"


@dataclass(frozen=True)
class UnitValue:
    """
    Valor con unidad de medida.
    No se evalúa hasta que se llama resolve().
    """
    value: float
    unit: str   # "px" | "pct" | "dpi" | "vw" | "vh" | "em"

    def __add__(self, other: "UnitValue | int | float") -> "UnitValue":
        if isinstance(other, UnitValue) and other.unit == self.unit:
            return UnitValue(self.value + other.value, self.unit)
        # px fallback
        return UnitValue(
            resolve(self) + resolve(other),
            _UNIT_PX
        )

    def __sub__(self, other: "UnitValue | int | float") -> "UnitValue":
        if isinstance(other, UnitValue) and other.unit == self.unit:
            return UnitValue(self.value - other.value, self.unit)
        return UnitValue(resolve(self) - resolve(other), _UNIT_PX)

    def __mul__(self, factor: float) -> "UnitValue":
        return UnitValue(self.value * factor, self.unit)

    def __rmul__(self, factor: float) -> "UnitValue":
        return self.__mul__(factor)

    def __repr__(self) -> str:
        return f"UnitValue({self.value}{self.unit})"


# ──────────────────────────────────────────────────────────────────────────────
# Constructors
# ──────────────────────────────────────────────────────────────────────────────

def px(n: float) -> UnitValue:
    """Píxeles absolutos."""
    return UnitValue(float(n), _UNIT_PX)

def pct(n: float) -> UnitValue:
    """Porcentaje del tamaño del contenedor/ventana (0-100)."""
    return UnitValue(float(n), _UNIT_PCT)

def dpi(inches: float) -> UnitValue:
    """Pulgadas lógicas — se convierte a px según DPI de pantalla."""
    return UnitValue(float(inches), _UNIT_DPI)

def vw(n: float) -> UnitValue:
    """Porcentaje del ancho del viewport (0-100)."""
    return UnitValue(float(n), _UNIT_VW)

def vh(n: float) -> UnitValue:
    """Porcentaje del alto del viewport (0-100)."""
    return UnitValue(float(n), _UNIT_VH)

def em(n: float) -> UnitValue:
    """Múltiplo del font-size base (default 14px)."""
    return UnitValue(float(n), _UNIT_EM)


# ──────────────────────────────────────────────────────────────────────────────
# Resolver
# ──────────────────────────────────────────────────────────────────────────────

_ViewportSize: tuple[int, int] = (800, 600)

def set_viewport(w: int, h: int) -> None:
    """Llamar al crear/redimensionar la ventana para que vw/vh funcionen."""
    global _ViewportSize
    _ViewportSize = (max(1, int(w)), max(1, int(h)))


def resolve(
    value: "UnitValue | int | float",
    parent_size: int | float = 0,
    base_font_px: int = 14,
) -> int:
    """
    Convierte un UnitValue a píxeles enteros.

    Args:
        value       : UnitValue, int o float
        parent_size : tamaño del padre en px (para % )
        base_font_px: tamaño de fuente base (para em)

    Returns:
        int en píxeles.
    """
    if isinstance(value, (int, float)):
        return int(value)

    v = value.value
    unit = value.unit

    if unit == _UNIT_PX:
        return int(v)
    if unit == _UNIT_PCT:
        return int(v / 100.0 * parent_size)
    if unit == _UNIT_DPI:
        return int(v * get_screen_dpi())
    if unit == _UNIT_VW:
        return int(v / 100.0 * _ViewportSize[0])
    if unit == _UNIT_VH:
        return int(v / 100.0 * _ViewportSize[1])
    if unit == _UNIT_EM:
        return int(v * base_font_px)
    return int(v)


@dataclass
class UnitRect:
    """Rect con soporte de unidades."""
    x: UnitValue | int = 0
    y: UnitValue | int = 0
    width: UnitValue | int = 0
    height: UnitValue | int = 0

    def resolve(
        self,
        parent_w: int = 0,
        parent_h: int = 0,
    ) -> tuple[int, int, int, int]:
        return (
            resolve(self.x, parent_w),
            resolve(self.y, parent_h),
            resolve(self.width, parent_w),
            resolve(self.height, parent_h),
        )

    def to_pygame_rect(
        self,
        parent_w: int = 0,
        parent_h: int = 0,
    ) -> pygame.Rect:
        return pygame.Rect(*self.resolve(parent_w, parent_h))


def resolve_rect(
    style: dict,
    parent_w: int = 0,
    parent_h: int = 0,
) -> dict:
    """
    Toma un dict de estilo y resuelve todos los UnitValue a int.
    Útil antes de pasar a compile_style().
    """
    out = {}
    for k, v in style.items():
        if isinstance(v, UnitValue):
            if k in ("width", "x"):
                out[k] = resolve(v, parent_w)
            elif k in ("height", "y"):
                out[k] = resolve(v, parent_h)
            else:
                out[k] = resolve(v, max(parent_w, parent_h))
        else:
            out[k] = v
    return out