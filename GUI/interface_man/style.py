"""
PycePlus.GUI.interface_man.style
CSS-like style system with compiled-surface cache.

Supported properties:
  color, background_color, background_gradient (list of colors + direction)
  border, border_color, border_radius,
  border_top_left_radius, border_top_right_radius,
  border_bottom_left_radius, border_bottom_right_radius
  padding, padding_left/right/top/bottom
  text_align  ('left' | 'center' | 'right')
  align_items ('start' | 'center' | 'end' | 'stretch')
  font_size, font_family, font_bold, font_italic, font_underline
  opacity (0.0–1.0)
  cursor
"""
from __future__ import annotations

import hashlib
import threading
from typing import Any

import pygame

from PycePlus.UI.tools.color import Color, colorType

# ──────────────────────────────────────────────────────────────────────────────
# Defaults
# ──────────────────────────────────────────────────────────────────────────────

_DEFAULTS: dict[str, Any] = {
    "color":                     (220, 220, 220, 255),
    "background_color":          (30, 30, 30, 255),
    "background_gradient":       None,       # list[(color, color, 'h'|'v')]
    "border":                    0,
    "border_color":              (80, 80, 80, 255),
    "border_radius":             0,
    "border_top_left_radius":    -1,
    "border_top_right_radius":   -1,
    "border_bottom_left_radius": -1,
    "border_bottom_right_radius":-1,
    "padding":                   0,
    "padding_left":              0,
    "padding_right":             0,
    "padding_top":               0,
    "padding_bottom":            0,
    "text_align":                "left",
    "align_items":               "start",
    "font_size":                 14,
    "font_family":               None,
    "font_bold":                 False,
    "font_italic":               False,
    "font_underline":            False,
    "opacity":                   1.0,
    "cursor":                    "arrow",
}

# ──────────────────────────────────────────────────────────────────────────────
# CompiledStyle  — immutable after build
# ──────────────────────────────────────────────────────────────────────────────

class CompiledStyle:
    """Resolved style ready to be consumed by a widget renderer."""

    __slots__ = (
        "color", "background_color", "background_gradient",
        "border", "border_color",
        "border_radius",
        "border_top_left_radius", "border_top_right_radius",
        "border_bottom_left_radius", "border_bottom_right_radius",
        "pad_left", "pad_right", "pad_top", "pad_bottom",
        "text_align", "align_items",
        "font_size", "font_family", "font_bold", "font_italic", "font_underline",
        "opacity", "cursor",
    )

    def __init__(self, raw: dict[str, Any]):
        d = {**_DEFAULTS, **raw}

        # ── colours ──────────────────────────────────────────────────────────
        self.color              = Color.makefrom(d["color"])
        self.background_color   = Color.makefrom(d["background_color"])
        self.background_gradient = d["background_gradient"]
        self.border_color       = Color.makefrom(d["border_color"])

        # ── border ────────────────────────────────────────────────────────────
        self.border                    = int(d["border"])
        self.border_radius             = int(d["border_radius"])
        # per-corner: -1 means fall back to border_radius
        br = self.border_radius
        self.border_top_left_radius    = int(d["border_top_left_radius"])     if d["border_top_left_radius"]    >= 0 else br
        self.border_top_right_radius   = int(d["border_top_right_radius"])    if d["border_top_right_radius"]   >= 0 else br
        self.border_bottom_left_radius = int(d["border_bottom_left_radius"])  if d["border_bottom_left_radius"] >= 0 else br
        self.border_bottom_right_radius= int(d["border_bottom_right_radius"]) if d["border_bottom_right_radius"]>= 0 else br

        # ── padding ───────────────────────────────────────────────────────────
        pad = int(d["padding"])
        self.pad_left   = int(d["padding_left"])   or pad
        self.pad_right  = int(d["padding_right"])  or pad
        self.pad_top    = int(d["padding_top"])    or pad
        self.pad_bottom = int(d["padding_bottom"]) or pad

        # ── layout ───────────────────────────────────────────────────────────
        self.text_align  = str(d["text_align"])
        self.align_items = str(d["align_items"])

        # ── typography ───────────────────────────────────────────────────────
        self.font_size      = int(d["font_size"])
        self.font_family    = d["font_family"]
        self.font_bold      = bool(d["font_bold"])
        self.font_italic    = bool(d["font_italic"])
        self.font_underline = bool(d["font_underline"])

        # ── misc ─────────────────────────────────────────────────────────────
        self.opacity = float(d["opacity"])
        self.cursor  = str(d["cursor"])

    # ── gradient helper ───────────────────────────────────────────────────────

    def build_gradient_surface(self, width: int, height: int) -> pygame.Surface:
        """Render a linear gradient to a Surface."""
        grad = self.background_gradient
        if not grad or len(grad) < 2:
            surf = pygame.Surface((width, height), pygame.SRCALPHA)
            surf.fill(self.background_color)
            return surf

        c1 = Color.makefrom(grad[0])
        c2 = Color.makefrom(grad[1])
        direction = grad[2] if len(grad) > 2 else "h"

        surf = pygame.Surface((width, height), pygame.SRCALPHA)
        steps = width if direction == "h" else height

        for i in range(steps):
            t  = i / max(steps - 1, 1)
            r  = int(c1.r + (c2.r - c1.r) * t)
            g  = int(c1.g + (c2.g - c1.g) * t)
            b  = int(c1.b + (c2.b - c1.b) * t)
            a  = int(c1.a + (c2.a - c1.a) * t)
            col = (r, g, b, a)
            if direction == "h":
                pygame.draw.line(surf, col, (i, 0), (i, height - 1))
            else:
                pygame.draw.line(surf, col, (0, i), (width - 1, i))
        return surf

    # ── fill surface helper ───────────────────────────────────────────────────

    def fill_surface(self, surf: pygame.Surface) -> None:
        """Fill *surf* with background (gradient or solid), respecting border-radius."""
        w, h = surf.get_size()
        surf.fill((0, 0, 0, 0))

        if self.background_gradient:
            bg = self.build_gradient_surface(w, h)
        else:
            bg = pygame.Surface((w, h), pygame.SRCALPHA)
            bg.fill(self.background_color)

        # Clip to rounded rect
        mask = pygame.Surface((w, h), pygame.SRCALPHA)
        mask.fill((0, 0, 0, 0))
        pygame.draw.rect(mask, (255, 255, 255, 255), (0, 0, w, h),
                         border_radius=self.border_radius,
                         border_top_left_radius=self.border_top_left_radius,
                         border_top_right_radius=self.border_top_right_radius,
                         border_bottom_left_radius=self.border_bottom_left_radius,
                         border_bottom_right_radius=self.border_bottom_right_radius)
        bg.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        surf.blit(bg, (0, 0))

    # ── border draw helper ────────────────────────────────────────────────────

    def draw_border(self, surf: pygame.Surface) -> None:
        if self.border <= 0:
            return
        w, h = surf.get_size()
        pygame.draw.rect(surf, self.border_color, (0, 0, w, h),
                         width=self.border,
                         border_radius=self.border_radius,
                         border_top_left_radius=self.border_top_left_radius,
                         border_top_right_radius=self.border_top_right_radius,
                         border_bottom_left_radius=self.border_bottom_left_radius,
                         border_bottom_right_radius=self.border_bottom_right_radius)


# ──────────────────────────────────────────────────────────────────────────────
# StyleCache  — LRU-like cache keyed by dict-hash
# ──────────────────────────────────────────────────────────────────────────────

class StyleCache:
    """Thread-safe cache for CompiledStyle objects, keyed by raw-dict hash."""

    _MAX = 512
    _lock = threading.RLock()
    _store: dict[str, CompiledStyle] = {}
    _order: list[str] = []

    @classmethod
    def _hash(cls, raw: dict) -> str:
        h = hashlib.md5(str(sorted(raw.items())).encode(), usedforsecurity=False)
        return h.hexdigest()

    @classmethod
    def get(cls, raw: dict) -> CompiledStyle:
        key = cls._hash(raw)
        with cls._lock:
            if key in cls._store:
                cls._order.remove(key)
                cls._order.append(key)
                return cls._store[key]
            compiled = CompiledStyle(raw)
            cls._store[key] = compiled
            cls._order.append(key)
            if len(cls._order) > cls._MAX:
                oldest = cls._order.pop(0)
                cls._store.pop(oldest, None)
            return compiled

    @classmethod
    def invalidate(cls) -> None:
        with cls._lock:
            cls._store.clear()
            cls._order.clear()


# ──────────────────────────────────────────────────────────────────────────────
# Public helper
# ──────────────────────────────────────────────────────────────────────────────

def compile_style(raw: dict | None) -> CompiledStyle:
    """Return a cached CompiledStyle for *raw* dict (or defaults if None)."""
    return StyleCache.get(raw or {})
