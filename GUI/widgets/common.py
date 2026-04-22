"""
PycePlus.GUI.widgets.common
Button, Label, Checkbox, Image widgets.
All use dirty-flag rendering and the CSS style system.
"""
from __future__ import annotations

import os
import threading
from typing import Callable, Literal

import pygame

from PycePlus.GUI.base import Base
from PycePlus.GUI.interface_man.style import compile_style
from PycePlus.UI.tools.color import Color, colorType
from PycePlus.UI.tools.font  import Font

# ──────────────────────────────────────────────────────────────────────────────
# Image LRU cache
# ──────────────────────────────────────────────────────────────────────────────

class _ImageCache:
    _MAX  = 128
    _lock = threading.RLock()
    _store: dict[str, pygame.Surface] = {}
    _order: list[str]                 = []

    @classmethod
    def load(cls, path: str) -> pygame.Surface:
        with cls._lock:
            if path in cls._store:
                cls._order.remove(path)
                cls._order.append(path)
                return cls._store[path]
        surf = pygame.image.load(path).convert_alpha()
        with cls._lock:
            cls._store[path] = surf
            cls._order.append(path)
            if len(cls._order) > cls._MAX:
                oldest = cls._order.pop(0)
                cls._store.pop(oldest, None)
        return surf

    @classmethod
    def invalidate(cls, path: str | None = None) -> None:
        with cls._lock:
            if path:
                cls._store.pop(path, None)
                if path in cls._order:
                    cls._order.remove(path)
            else:
                cls._store.clear()
                cls._order.clear()


_img_cache = _ImageCache()


# ──────────────────────────────────────────────────────────────────────────────
# Button
# ──────────────────────────────────────────────────────────────────────────────

class Button(Base):
    """
    Modern push-button widget.

    Parameters
    ----------
    text          : str
    width, height : int
    font          : Font | None
    style         : dict | None   CSS-like style
    hover_style   : dict | None   applied on hover
    active_style  : dict | None   applied while pressed
    x, y          : int
    on_click      : Callable | None
    """

    def __init__(
        self,
        father=None,
        text:         str  = "Button",
        width:        int  = 120,
        height:       int  = 36,
        font:         Font | None = None,
        style:        dict | None = None,
        hover_style:  dict | None = None,
        active_style: dict | None = None,
        x: int = 0,
        y: int = 0,
        on_click: Callable | None = None,
        name: str | None = None,
        page: str | None = None,
        visible: bool = True,
    ):
        _default_style = {
            "background_color": (52, 120, 220, 255),
            "color":            (255, 255, 255, 255),
            "border_radius":    8,
            "border":           0,
            "padding_left":     12,
            "padding_right":    12,
            "text_align":       "center",
            "cursor":           "hand",
            "font_size":        14,
        }
        _style = {**_default_style, **(style or {})}

        super().__init__(father, name, page, style=_style)
        self.rect    = pygame.Rect(x, y, width, height)
        self.texture = pygame.Surface((width, height), pygame.SRCALPHA)
        self.visible = visible
        self.text    = text
        self._font   = font or Font(None, self._style.font_size)

        self._hover_style_raw  = {**_style, **(hover_style  or {"background_color": (72, 140, 240, 255)})}
        self._active_style_raw = {**_style, **(active_style or {"background_color": (32, 90, 180, 255)})}
        self._hover_cs  = compile_style(self._hover_style_raw)
        self._active_cs = compile_style(self._active_style_raw)

        self._pressed = False
        if on_click:
            self.bind("mouse.button.left.click", lambda w, _: on_click())

        # auto-mark dirty on hover/leave/press for visual state change
        self.bind("mouse.hover",                 lambda w, _: w.mark_dirty())
        self.bind("mouse.leave",                 lambda w, _: w.mark_dirty())
        self.bind("mouse.button.left.click",     lambda w, _: self._set_pressed(True))
        self.bind("mouse.button.left.release",   lambda w, _: self._set_pressed(False))
        self.mark_dirty()

    def _set_pressed(self, v: bool) -> None:
        self._pressed = v
        self.mark_dirty()

    @property
    def label(self) -> str:
        return self.text

    @label.setter
    def label(self, v: str) -> None:
        self.text = v
        self.mark_dirty()

    def render_self(self) -> None:
        if not self._dirty or self.texture is None:
            return

        w, h = self.rect.width, self.rect.height
        if self.texture.get_size() != (w, h):
            self.texture = pygame.Surface((w, h), pygame.SRCALPHA)

        cs = (self._active_cs if self._pressed
              else (self._hover_cs if self.is_hover else self._style))

        cs.fill_surface(self.texture)

        # text
        txt_surf = self._font.render(self.text, cs.color)
        if txt_surf:
            tw, th  = txt_surf.get_size()
            ta      = cs.text_align
            if ta == "center":
                tx = (w - tw) // 2
            elif ta == "right":
                tx = w - cs.pad_right - tw
            else:
                tx = cs.pad_left
            ty = (h - th) // 2
            self.texture.blit(txt_surf, (tx, ty))

        cs.draw_border(self.texture)
        self.clear_dirty()


# ──────────────────────────────────────────────────────────────────────────────
# Label
# ──────────────────────────────────────────────────────────────────────────────

class Label(Base):
    """
    Static or dynamic text label.

    Parameters
    ----------
    text          : str
    width, height : int  (0 = auto-size to text)
    font          : Font | None
    style         : dict | None
    auto_size     : bool   resize to fit text each frame
    """

    def __init__(
        self,
        father=None,
        text:       str  = "",
        width:      int  = 0,
        height:     int  = 0,
        font:       Font | None = None,
        style:      dict | None = None,
        auto_size:  bool = True,
        x: int = 0,
        y: int = 0,
        name: str | None = None,
        page: str | None = None,
        visible: bool = True,
    ):
        _default_style = {
            "background_color": (0, 0, 0, 0),
            "color":            (220, 220, 220, 255),
            "font_size":        14,
        }
        _style = {**_default_style, **(style or {})}
        super().__init__(father, name, page, style=_style)
        self._font     = font or Font(None, self._style.font_size)
        self._text     = text
        self.auto_size = auto_size
        self.visible   = visible

        w, h = self._measure()
        self.rect    = pygame.Rect(x, y, max(width, w), max(height, h))
        self.texture = pygame.Surface((self.rect.width or 1,
                                       self.rect.height or 1), pygame.SRCALPHA)
        self.mark_dirty()

    @property
    def text(self) -> str:
        return self._text

    @text.setter
    def text(self, v: str) -> None:
        self._text = str(v)
        self.mark_dirty()

    def _measure(self) -> tuple[int, int]:
        try:
            return self._font.size(self._text)
        except Exception:
            return (0, 0)

    def render_self(self) -> None:
        if not self._dirty:
            return

        if self.auto_size:
            w, h = self._measure()
            w = max(w + self._style.pad_left + self._style.pad_right, 1)
            h = max(h + self._style.pad_top  + self._style.pad_bottom, 1)
            if (w, h) != (self.rect.width, self.rect.height):
                self.rect.width  = w
                self.rect.height = h
                self.texture = pygame.Surface((w, h), pygame.SRCALPHA)

        if self.texture is None:
            return

        self._style.fill_surface(self.texture)
        txt_surf = self._font.render(self._text, self._style.color)
        if txt_surf:
            ta = self._style.text_align
            tw, th = txt_surf.get_size()
            w, h   = self.rect.width, self.rect.height
            if ta == "center":
                tx = (w - tw) // 2
            elif ta == "right":
                tx = w - self._style.pad_right - tw
            else:
                tx = self._style.pad_left
            ty = self._style.pad_top
            self.texture.blit(txt_surf, (tx, ty))
        self._style.draw_border(self.texture)
        self.clear_dirty()


# ──────────────────────────────────────────────────────────────────────────────
# Checkbox
# ──────────────────────────────────────────────────────────────────────────────

class Checkbox(Base):
    """
    Toggle checkbox widget.

    Parameters
    ----------
    text          : str   label beside the box
    checked       : bool
    box_size      : int   size of the tick box (px)
    check_color   : colorType
    style         : dict | None
    on_change     : Callable[[bool], None] | None
    """

    def __init__(
        self,
        father=None,
        text:         str  = "",
        checked:      bool = False,
        box_size:     int  = 18,
        check_color:  colorType = (80, 160, 255, 255),
        font:         Font | None = None,
        style:        dict | None = None,
        on_change:    Callable | None = None,
        x: int = 0,
        y: int = 0,
        name: str | None = None,
        page: str | None = None,
        visible: bool = True,
    ):
        _default = {
            "background_color": (0, 0, 0, 0),
            "color":            (220, 220, 220, 255),
            "border_radius":    4,
            "font_size":        14,
            "cursor":           "hand",
        }
        _style = {**_default, **(style or {})}
        super().__init__(father, name, page, style=_style)

        self._checked     = checked
        self.box_size     = box_size
        self.check_color  = Color.makefrom(check_color)
        self._font        = font or Font(None, self._style.font_size)
        self._text        = text
        self._on_change   = on_change
        self.visible      = visible

        fw, _ = self._font.size(text) if text else (0, 0)
        w = box_size + (8 + fw if text else 0) + 4
        h = max(box_size, self._font.size("A")[1] if text else box_size) + 4
        self.rect    = pygame.Rect(x, y, w, h)
        self.texture = pygame.Surface((w, h), pygame.SRCALPHA)

        self.bind("mouse.button.left.click", self._toggle)
        self.mark_dirty()

    @property
    def checked(self) -> bool:
        return self._checked

    @checked.setter
    def checked(self, v: bool) -> None:
        if v != self._checked:
            self._checked = bool(v)
            if self._on_change:
                self._on_change(self._checked)
            self._fire(32)  # value.change
            self.mark_dirty()

    def _toggle(self, widget, pos) -> None:
        self.checked = not self._checked

    def render_self(self) -> None:
        if not self._dirty or self.texture is None:
            return

        w, h = self.rect.width, self.rect.height
        self._style.fill_surface(self.texture)

        bs  = self.box_size
        bx  = self._style.pad_left + 2
        by  = (h - bs) // 2
        box = pygame.Rect(bx, by, bs, bs)

        box_bg  = (50, 50, 60, 255)
        box_bdr = (100, 100, 120, 255)
        if self._checked:
            box_bg = self.check_color

        pygame.draw.rect(self.texture, box_bg, box, border_radius=4)
        pygame.draw.rect(self.texture, box_bdr, box, 1, border_radius=4)

        if self._checked:
            # Draw check-mark
            m = bs // 5
            p1 = (bx + m,      by + bs // 2)
            p2 = (bx + bs // 2 - m, by + bs - m * 2)
            p3 = (bx + bs - m, by + m * 2)
            pygame.draw.lines(self.texture, (255, 255, 255, 255), False,
                               [p1, p2, p3], 2)

        if self._text:
            txt_surf = self._font.render(self._text, self._style.color)
            if txt_surf:
                tx = bx + bs + 8
                ty = (h - txt_surf.get_height()) // 2
                self.texture.blit(txt_surf, (tx, ty))

        self._style.draw_border(self.texture)
        self.clear_dirty()


# ──────────────────────────────────────────────────────────────────────────────
# Image
# ──────────────────────────────────────────────────────────────────────────────

class Image(Base):
    """
    Image widget with LRU cache.

    Parameters
    ----------
    source      : str | pygame.Surface   file path or pre-loaded surface
    width       : int   0 = natural width
    height      : int   0 = natural height
    keep_ratio  : bool  maintain aspect ratio when resizing
    style       : dict | None
    """

    def __init__(
        self,
        father=None,
        source:     str | pygame.Surface | None = None,
        width:      int  = 0,
        height:     int  = 0,
        keep_ratio: bool = True,
        style:      dict | None = None,
        x: int = 0,
        y: int = 0,
        name: str | None = None,
        page: str | None = None,
        visible: bool = True,
    ):
        _default = {
            "background_color": (0, 0, 0, 0),
        }
        _style = {**_default, **(style or {})}
        super().__init__(father, name, page, style=_style)

        self._source     = source
        self._orig:  pygame.Surface | None = None
        self._scaled:pygame.Surface | None = None
        self.keep_ratio  = keep_ratio
        self.visible     = visible
        self._path:  str | None = None

        self._load_source(source)

        nat_w = self._orig.get_width()  if self._orig else 0
        nat_h = self._orig.get_height() if self._orig else 0
        w = width  or nat_w
        h = height or nat_h
        self.rect    = pygame.Rect(x, y, max(w, 1), max(h, 1))
        self.texture = pygame.Surface((self.rect.width, self.rect.height),
                                      pygame.SRCALPHA)
        self.mark_dirty()

    def _load_source(self, source) -> None:
        if source is None:
            self._orig = None
        elif isinstance(source, str):
            self._path = source
            try:
                self._orig = _img_cache.load(source)
            except Exception:
                self._orig = None
        elif isinstance(source, pygame.Surface):
            self._orig = source

    def set_source(self, source: str | pygame.Surface) -> None:
        self._load_source(source)
        self.mark_dirty()

    def _scale(self) -> pygame.Surface | None:
        if self._orig is None:
            return None
        w, h = self.rect.width, self.rect.height
        ow, oh = self._orig.get_size()
        if self.keep_ratio and ow and oh:
            ratio = min(w / ow, h / oh)
            nw    = max(1, int(ow * ratio))
            nh    = max(1, int(oh * ratio))
        else:
            nw, nh = w, h
        return pygame.transform.smoothscale(self._orig, (nw, nh))

    def render_self(self) -> None:
        if not self._dirty or self.texture is None:
            return

        w, h = self.rect.width, self.rect.height
        if self.texture.get_size() != (w, h):
            self.texture = pygame.Surface((w, h), pygame.SRCALPHA)

        self._style.fill_surface(self.texture)
        scaled = self._scale()
        if scaled:
            sw, sh = scaled.get_size()
            sx = (w - sw) // 2
            sy = (h - sh) // 2
            self.texture.blit(scaled, (sx, sy))
        self._style.draw_border(self.texture)
        self.clear_dirty()
