from __future__ import annotations

import hashlib
import threading
from typing import Any

import numpy as np
import pygame

from PycePlus.UI.tools.color import Color

_DEFAULTS: dict[str, Any] = {
    "color": (220, 220, 220, 255),
    "background_color": (30, 30, 30, 255),
    "background_gradient": None,
    "border": 0,
    "border_color": (80, 80, 80, 255),
    "border_radius": 0,
    'x': 0,
    'y': 0,
    'width': 10,
    'height': 10,
    "border_top_left_radius": -1,
    "border_top_right_radius": -1,
    "border_bottom_left_radius": -1,
    "border_bottom_right_radius": -1,
    "padding": 0,
    "padding_left": 0,
    "padding_right": 0,
    "padding_top": 0,
    "padding_bottom": 0,
    "text_align": "left",
    "align_items": "start",
    "font_size": 14,
    "font_family": None,
    "font_bold": False,
    "font_italic": False,
    "font_underline": False,
    "opacity": 1.0,
    "cursor": "arrow",
    "effects": None,
}


def _rgba(value: Any) -> tuple[int, int, int, int]:
    c = Color.makefrom(value)
    return c.r, c.g, c.b, c.a


def _apply_noise(surf: pygame.Surface, strength: float = 0.0) -> None:
    if strength <= 0:
        return
    try:
        arr = pygame.surfarray.pixels3d(surf)
        noise = np.random.randint(-int(255 * strength), int(255 * strength) + 1, arr.shape, dtype=np.int16)
        arr[:] = np.clip(arr.astype(np.int16) + noise, 0, 255).astype(np.uint8)
        del arr
    except Exception:
        pass


def _apply_vignette(surf: pygame.Surface, strength: float = 0.25) -> None:
    if strength <= 0:
        return
    try:
        arr = pygame.surfarray.pixels3d(surf)
        w, h = surf.get_size()
        yy, xx = np.ogrid[:h, :w]
        cx, cy = w / 2.0, h / 2.0
        dist = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
        max_dist = np.sqrt(cx ** 2 + cy ** 2) or 1.0
        mask = 1.0 - np.clip(dist / max_dist, 0.0, 1.0)
        mask = (mask ** 1.5 * strength).reshape(h, w, 1)
        arr[:] = np.clip(arr.astype(np.float32) * (1.0 - mask), 0, 255).astype(np.uint8)
        del arr
    except Exception:
        pass



def _normalize_effects(effects: Any) -> dict[str, Any]:
    if not isinstance(effects, dict):
        return {}
    normalized: dict[str, Any] = {}
    for key, value in effects.items():
        normalized[str(key).strip().lower().replace("-", "_")] = value
    return normalized


def _blur_surface(surf: pygame.Surface, radius: int) -> pygame.Surface:
    radius = max(0, int(radius))
    if radius <= 0:
        return surf.copy()

    w, h = surf.get_size()
    if w <= 1 or h <= 1:
        return surf.copy()

    # Cheap blur via downscale/upscale. Good enough for soft shadows.
    factor = max(1, radius // 2 + 1)
    small_w = max(1, w // factor)
    small_h = max(1, h // factor)
    tmp = pygame.transform.smoothscale(surf, (small_w, small_h))
    return pygame.transform.smoothscale(tmp, (w, h))


def _draw_shadow_rect(
    target: pygame.Surface,
    rect: pygame.Rect,
    color: tuple[int, int, int, int],
    blur: int = 0,
    spread: int = 0,
    border_radius: int = 0,
    border_top_left_radius: int = -1,
    border_top_right_radius: int = -1,
    border_bottom_left_radius: int = -1,
    border_bottom_right_radius: int = -1,
) -> None:
    shadow = pygame.Surface(target.get_size(), pygame.SRCALPHA)

    rr = pygame.Rect(rect)
    if spread:
        rr.inflate_ip(int(spread) * 2, int(spread) * 2)
    pygame.draw.rect(
        shadow,
        color,
        rr,
        border_radius=max(0, int(border_radius) + int(spread)),
        border_top_left_radius=border_top_left_radius if border_top_left_radius >= 0 else max(0, int(border_radius) + int(spread)),
        border_top_right_radius=border_top_right_radius if border_top_right_radius >= 0 else max(0, int(border_radius) + int(spread)),
        border_bottom_left_radius=border_bottom_left_radius if border_bottom_left_radius >= 0 else max(0, int(border_radius) + int(spread)),
        border_bottom_right_radius=border_bottom_right_radius if border_bottom_right_radius >= 0 else max(0, int(border_radius) + int(spread)),
    )

    if blur > 0:
        shadow = _blur_surface(shadow, blur)

    target.blit(shadow, (0, 0))


class CompiledStyle:
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
        "effects", "x", "y", "width", "height",
    )

    def __init__(self, raw: dict[str, Any]):
        d = {**_DEFAULTS, **raw}
        self.color = Color.makefrom(d["color"])
        self.background_color = Color.makefrom(d["background_color"])
        self.background_gradient = d["background_gradient"]
        self.border_color = Color.makefrom(d["border_color"])
        self.border = int(d["border"])
        self.border_radius = int(d["border_radius"])
        br = self.border_radius
        self.border_top_left_radius = int(d["border_top_left_radius"]) if d["border_top_left_radius"] >= 0 else br
        self.border_top_right_radius = int(d["border_top_right_radius"]) if d["border_top_right_radius"] >= 0 else br
        self.border_bottom_left_radius = int(d["border_bottom_left_radius"]) if d["border_bottom_left_radius"] >= 0 else br
        self.border_bottom_right_radius = int(d["border_bottom_right_radius"]) if d["border_bottom_right_radius"] >= 0 else br
        pad = int(d["padding"])
        self.pad_left = int(d["padding_left"]) or pad
        self.pad_right = int(d["padding_right"]) or pad
        self.pad_top = int(d["padding_top"]) or pad
        self.pad_bottom = int(d["padding_bottom"]) or pad
        self.text_align = str(d["text_align"])
        self.align_items = str(d["align_items"])
        self.font_size = int(d["font_size"])
        self.font_family = d["font_family"]
        self.font_bold = bool(d["font_bold"])
        self.x = d.get("x")
        self.y = d.get("y")
        self.width = d.get("width")
        self.height = d.get("height")
        self.font_italic = bool(d["font_italic"])
        self.font_underline = bool(d["font_underline"])
        self.opacity = float(d["opacity"])
        self.cursor = str(d["cursor"])
        self.effects = _normalize_effects(d.get("effects"))

    def _effect(self, *names: str) -> Any:
        for name in names:
            key = str(name).strip().lower().replace("-", "_")
            if key in self.effects:
                return self.effects[key]
        return None

    def _shadow_cfg(self, *names: str) -> dict[str, Any] | None:
        raw = self._effect(*names)
        if raw is None or raw is False:
            return None
        if raw is True:
            return {}
        if isinstance(raw, dict):
            return raw
        if isinstance(raw, (tuple, list)):
            out: dict[str, Any] = {}
            if len(raw) >= 2:
                out["offset"] = (raw[0], raw[1])
            if len(raw) >= 3:
                out["blur"] = raw[2]
            if len(raw) >= 4:
                out["color"] = raw[3]
            return out
        return None

    def apply_box_shadow(self, surf: pygame.Surface) -> None:
        cfg = self._shadow_cfg("box_shadow", "shadow_box")
        if not cfg:
            return

        w, h = surf.get_size()
        if w <= 0 or h <= 0:
            return

        offset = cfg.get("offset", (4, 4))
        if not isinstance(offset, (tuple, list)) or len(offset) < 2:
            offset = (4, 4)
        blur = int(cfg.get("blur", cfg.get("radius", 8) or 8))
        spread = int(cfg.get("spread", 0))
        color = Color.makefrom(cfg.get("color", (0, 0, 0, 120)))
        alpha = cfg.get("alpha", cfg.get("opacity", None))
        if alpha is not None:
            try:
                color.a = max(0, min(255, int(float(alpha) * 255 if float(alpha) <= 1 else float(alpha))))
            except Exception:
                pass

        rect = pygame.Rect(0, 0, w, h)
        rect.move_ip(int(offset[0]), int(offset[1]))
        _draw_shadow_rect(
            surf,
            rect,
            (color.r, color.g, color.b, color.a),
            blur=blur,
            spread=spread,
            border_radius=self.border_radius,
            border_top_left_radius=self.border_top_left_radius,
            border_top_right_radius=self.border_top_right_radius,
            border_bottom_left_radius=self.border_bottom_left_radius,
            border_bottom_right_radius=self.border_bottom_right_radius,
        )

    def blit_text_with_shadow(
        self,
        surf: pygame.Surface,
        font: Any,
        text: str,
        color: Any,
        pos: tuple[int, int],
    ) -> None:
        cfg = self._shadow_cfg("text_shadow", "shadow_text")
        if cfg:
            offset = cfg.get("offset", (2, 2))
            if not isinstance(offset, (tuple, list)) or len(offset) < 2:
                offset = (2, 2)
            blur = int(cfg.get("blur", cfg.get("radius", 2) or 2))
            color_shadow = Color.makefrom(cfg.get("color", (0, 0, 0, 160)))
            alpha = cfg.get("alpha", cfg.get("opacity", None))
            if alpha is not None:
                try:
                    color_shadow.a = max(0, min(255, int(float(alpha) * 255 if float(alpha) <= 1 else float(alpha))))
                except Exception:
                    pass

            shadow_surf = font.render(text, color_shadow)
            if shadow_surf:
                if blur > 0:
                    shadow_surf = _blur_surface(shadow_surf, blur)
                surf.blit(shadow_surf, (int(pos[0]) + int(offset[0]), int(pos[1]) + int(offset[1])))

        txt_surf = font.render(text, color)
        if txt_surf:
            surf.blit(txt_surf, pos)

    def build_gradient_surface(self, width: int, height: int) -> pygame.Surface:
        grad = self.background_gradient
        surf = pygame.Surface((width, height), pygame.SRCALPHA)
        if not grad or len(grad) < 2:
            surf.fill(self.background_color)
            return surf

        c1 = Color.makefrom(grad[0])
        c2 = Color.makefrom(grad[1])
        direction = grad[2] if len(grad) > 2 else "h"

        if direction == "h":
            t = np.linspace(0.0, 1.0, max(2, width), dtype=np.float32)
            row = np.stack([
                (c1.r + (c2.r - c1.r) * t),
                (c1.g + (c2.g - c1.g) * t),
                (c1.b + (c2.b - c1.b) * t),
                (c1.a + (c2.a - c1.a) * t),
            ], axis=1).astype(np.uint8)
            arr = np.repeat(row[np.newaxis, :, :], height, axis=0)
        else:
            t = np.linspace(0.0, 1.0, max(2, height), dtype=np.float32)
            col = np.stack([
                (c1.r + (c2.r - c1.r) * t),
                (c1.g + (c2.g - c1.g) * t),
                (c1.b + (c2.b - c1.b) * t),
                (c1.a + (c2.a - c1.a) * t),
            ], axis=1).astype(np.uint8)
            arr = np.repeat(col[:, np.newaxis, :], width, axis=1)

        try:
            rgb = arr[:, :, :3]
            alpha = arr[:, :, 3]
            pygame.surfarray.blit_array(surf, rgb.swapaxes(0, 1))
            alpha_surf = pygame.Surface((width, height), pygame.SRCALPHA)
            alpha_arr = pygame.surfarray.pixels_alpha(alpha_surf)
            alpha_arr[:] = alpha.swapaxes(0, 1)
            del alpha_arr
            surf.blit(alpha_surf, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        except Exception:
            surf.fill(_rgba(c1))
        return surf

    def fill_surface(self, surf: pygame.Surface) -> None:
        w, h = surf.get_size()
        surf.fill((0, 0, 0, 0))

        # Box shadow is painted first so it can glow outside the rounded rect.
        self.apply_box_shadow(surf)

        bg = self.build_gradient_surface(w, h) if self.background_gradient else pygame.Surface((w, h), pygame.SRCALPHA)
        if not self.background_gradient:
            bg.fill(self.background_color)

        mask = pygame.Surface((w, h), pygame.SRCALPHA)
        mask.fill((0, 0, 0, 0))
        pygame.draw.rect(
            mask, (255, 255, 255, 255), (0, 0, w, h),
            border_radius=self.border_radius,
            border_top_left_radius=self.border_top_left_radius,
            border_top_right_radius=self.border_top_right_radius,
            border_bottom_left_radius=self.border_bottom_left_radius,
            border_bottom_right_radius=self.border_bottom_right_radius,
        )
        bg.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)

        opacity = max(0.0, min(1.0, float(self.opacity)))
        if opacity < 1.0:
            alpha = pygame.Surface((w, h), pygame.SRCALPHA)
            alpha.fill((255, 255, 255, int(255 * opacity)))
            bg.blit(alpha, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

        effects = self.effects or {}
        _apply_noise(bg, float(effects.get("noise", 0.0)))
        if effects.get("vignette"):
            _apply_vignette(bg, float(effects.get("vignette_strength", 0.25)))

        surf.blit(bg, (0, 0))

    def draw_border(self, surf: pygame.Surface) -> None:
        if self.border <= 0:
            return
        w, h = surf.get_size()
        pygame.draw.rect(
            surf, self.border_color, (0, 0, w, h),
            width=self.border,
            border_radius=self.border_radius,
            border_top_left_radius=self.border_top_left_radius,
            border_top_right_radius=self.border_top_right_radius,
            border_bottom_left_radius=self.border_bottom_left_radius,
            border_bottom_right_radius=self.border_bottom_right_radius,
        )


class StyleCache:
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
                if key in cls._order:
                    cls._order.remove(key)
                cls._order.append(key)
                return cls._store[key]

            style = CompiledStyle(raw)
            cls._store[key] = style
            cls._order.append(key)
            if len(cls._order) > cls._MAX:
                oldest = cls._order.pop(0)
                cls._store.pop(oldest, None)
            return style


def compile_style(raw: dict[str, Any] | None) -> CompiledStyle:
    return StyleCache.get(raw or {})
