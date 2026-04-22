"""
PycePlus.GUI.base
Extensible base widget class with:
  • dirty-flag rendering (only redraw if changed)
  • CSS-style `style` dict support
  • Full event map (mouse, keyboard, focus, drag/drop, lifecycle)
  • Thread-safe dirty propagation via RLock
"""
from __future__ import annotations

import threading
from typing import Callable, Any, Literal, TYPE_CHECKING

if TYPE_CHECKING:
    from PycePlus.GUI.frame import Frame

import pygame

from PycePlus.UI.window import Window
from PycePlus.UI.tools.color import Color, colorType
from PycePlus.UI import Application
from PycePlus.GUI.interface_man import Tree
from PycePlus.GUI.interface_man.style import compile_style, CompiledStyle

# ──────────────────────────────────────────────────────────────────────────────
# Event identifier literals
# ──────────────────────────────────────────────────────────────────────────────

wEvents = Literal[
    "mouse.button.left.click",   "mouse.button.left.release",   "mouse.button.left.repeat",
    "mouse.button.middle.click", "mouse.button.middle.release", "mouse.button.middle.repeat",
    "mouse.button.right.click",  "mouse.button.right.release",  "mouse.button.right.repeat",
    "mouse.hover", "mouse.leave", "mouse.hovering",
    "mouse.button.left.double-click",
    "mouse.button.right.double-click",
    "mouse.button.middle.double-click",
    "mouse.scroll.up", "mouse.scroll.down",
    "mouse.drag.start", "mouse.drag.move", "mouse.drag.end",
    "key.down", "key.up", "key.repeat",
    "focus.gain", "focus.lose",
    "drop.file", "drop.text",
    "widget.create", "widget.delete", "widget.update",
    "widget.resize", "widget.move",
    "value.change",
]

wEvents_Map: dict[str, int] = {
    "mouse.button.left.click":           0,
    "mouse.button.left.release":         1,
    "mouse.button.left.repeat":          2,
    "mouse.button.middle.click":         3,
    "mouse.button.middle.release":       4,
    "mouse.button.middle.repeat":        5,
    "mouse.button.right.click":          6,
    "mouse.button.right.release":        7,
    "mouse.button.right.repeat":         8,
    "mouse.hover":                       9,
    "mouse.leave":                       10,
    "mouse.hovering":                    11,
    "mouse.button.left.double-click":    12,
    "mouse.button.right.double-click":   13,
    "mouse.button.middle.double-click":  14,
    "mouse.scroll.up":                   15,
    "mouse.scroll.down":                 16,
    "mouse.drag.start":                  17,
    "mouse.drag.move":                   18,
    "mouse.drag.end":                    19,
    "key.down":                          20,
    "key.up":                            21,
    "key.repeat":                        22,
    "focus.gain":                        23,
    "focus.lose":                        24,
    "drop.file":                         25,
    "drop.text":                         26,
    "widget.create":                     27,
    "widget.delete":                     28,
    "widget.update":                     29,
    "widget.resize":                     30,
    "widget.move":                       31,
    "value.change":                      32,
}

_ROM_SIZE = len(wEvents_Map)

Cursors = Literal[
    "arrow","ibeam","wait","crosshair","waitarrow",
    "sizenwse","sizenesw","sizewe","sizens","sizeall","no","hand",
]
Cursors_Map = {
    "arrow": 0, "ibeam": 1, "wait": 2, "crosshair": 3,
    "waitarrow": 4, "sizenwse": 5, "sizenesw": 6, "sizewe": 7,
    "sizens": 8, "sizeall": 9, "no": 10, "hand": 11,
}


class Padding:
    __slots__ = ("left", "right", "top", "bottom")

    def __init__(self, left=0, right=0, top=0, bottom=0):
        self.left   = left;  self.right  = right
        self.top    = top;   self.bottom = bottom

    @property
    def all(self):
        return self.left, self.right, self.top, self.bottom

    def set_pad(self, left=None, right=None, top=None, bottom=None):
        if left   is not None: self.left   = left
        if right  is not None: self.right  = right
        if top    is not None: self.top    = top
        if bottom is not None: self.bottom = bottom


class Outline:
    def __init__(self, width=0, color=None, border_radius=0,
                 border_top_left_radius=0, border_top_right_radius=0,
                 border_bottom_right_radius=0, border_bottom_left_radius=0,
                 sides=(1, 1, 1, 1)):
        self.width                     = width
        self.color                     = color or Color(0, 0, 0)
        self.border_radius             = border_radius
        self.border_top_left_radius    = border_top_left_radius
        self.border_top_right_radius   = border_top_right_radius
        self.border_bottom_right_radius= border_bottom_right_radius
        self.border_bottom_left_radius = border_bottom_left_radius
        self.sides                     = sides
        self.gradient_colors: list     = []
        self.type: str                 = "normal"
        self.gradient_type: str        = "horizontal"


# ──────────────────────────────────────────────────────────────────────────────
# Base
# ──────────────────────────────────────────────────────────────────────────────

class Base:
    """
    Root of every PycePlus widget.

    Constructor kwargs
    ------------------
    father  : Frame | Window | None
    name    : str | None
    page    : str | None
    style   : dict | None   CSS-like style dictionary
    """

    def __init__(
        self,
        father: "Frame | None | Window",
        name:   str | None,
        page:   str | None,
        style:  dict | None = None,
    ):
        self._lock = threading.RLock()

        self.father = father or Window
        self.name   = name or f"{self.__class__.__name__}-{id(self)}"
        self.page   = page or Tree.current_page()

        # geometry
        self.rect    = pygame.Rect(0, 0, 0, 0)
        self.padding = Padding()
        self.outline = Outline()

        # rendering
        self.texture:          pygame.Surface | None = None
        self.background_color: Color = Color(30, 30, 30)
        self.color:            Color = Color(220, 220, 220)
        self.default_color:    Color = Color(220, 220, 220)
        self.cursor:           int   = 0
        self.visible:          bool  = True

        # style
        self._style_raw: dict       = style or {}
        self._style: CompiledStyle  = compile_style(self._style_raw)
        self._apply_style()

        # state
        self.is_focus:  bool = False
        self.is_hover:  bool = False
        self._dirty:    bool = True

        # drag
        self._dragging:    bool = False
        self._drag_origin: tuple[int, int] = (0, 0)

        # event callbacks
        self._ROM: dict[int, Callable | None] = {i: None for i in range(_ROM_SIZE)}

        # double-click / button flags
        self._timers = [0.0, 0.0, 0.0]
        self._bflags = [0,   0,   0]

        # register
        if self._is_root_father():
            Tree.put(self)
        else:
            self.father.put(self)

        self._fire(27)   # widget.create

    # ── internal helpers ─────────────────────────────────────────────────────

    def _is_root_father(self) -> bool:
        return self.father is Window or isinstance(self.father, type(Window))

    # ── style ─────────────────────────────────────────────────────────────────

    def _apply_style(self) -> None:
        s = self._style
        self.background_color.update(s.background_color)
        self.color.update(s.color)
        self.padding.set_pad(s.pad_left, s.pad_right, s.pad_top, s.pad_bottom)
        self.outline.width                     = s.border
        self.outline.color                     = s.border_color
        self.outline.border_radius             = s.border_radius
        self.outline.border_top_left_radius    = s.border_top_left_radius
        self.outline.border_top_right_radius   = s.border_top_right_radius
        self.outline.border_bottom_left_radius = s.border_bottom_left_radius
        self.outline.border_bottom_right_radius= s.border_bottom_right_radius
        self.cursor = Cursors_Map.get(s.cursor, 0)

    def set_style(self, style: dict) -> "Base":
        with self._lock:
            self._style_raw = style
            self._style     = compile_style(style)
            self._apply_style()
            self.mark_dirty()
        return self

    def update_style(self, **kwargs) -> "Base":
        return self.set_style({**self._style_raw, **kwargs})

    @property
    def style(self) -> CompiledStyle:
        return self._style

    # ── dirty ─────────────────────────────────────────────────────────────────

    def mark_dirty(self) -> None:
        with self._lock:
            self._dirty = True
        Application.REFRESH = True
        if self.is_father_widget() and hasattr(self.father, "mark_dirty"):
            self.father.mark_dirty()

    def clear_dirty(self) -> None:
        with self._lock:
            self._dirty = False

    @property
    def is_dirty(self) -> bool:
        return self._dirty

    # ── event binding ─────────────────────────────────────────────────────────

    def bind(self, event: int | wEvents, callback: Callable | None) -> "Base":
        eid = event if isinstance(event, int) else wEvents_Map[event]
        self._ROM[eid] = callback
        return self

    def unbind(self, event: int | wEvents) -> "Base":
        eid = event if isinstance(event, int) else wEvents_Map[event]
        self._ROM[eid] = None
        return self

    def _fire(self, event_id: int, *args) -> None:
        cb = self._ROM.get(event_id)
        if cb:
            try:
                cb(self, *args)
            except Exception:
                import traceback; traceback.print_exc()

    # ── geometry ──────────────────────────────────────────────────────────────

    def get_size(self) -> tuple[int, int]:
        return self.rect.width, self.rect.height

    @property
    def width(self)   -> int: return self.rect.width
    @property
    def height(self)  -> int: return self.rect.height
    @property
    def x(self)       -> int: return self.rect.x
    @property
    def y(self)       -> int: return self.rect.y
    @property
    def right(self)   -> int: return self.rect.right
    @property
    def bottom(self)  -> int: return self.rect.bottom
    @property
    def center(self)          -> tuple[int,int]: return self.rect.center
    @property
    def centerx(self) -> int: return self.rect.centerx
    @property
    def centery(self) -> int: return self.rect.centery

    @property
    def abs_x(self)      -> int:
        return self.rect.x + (self.father.abs_x if self.is_father_widget() else 0)
    @property
    def abs_y(self)      -> int:
        return self.rect.y + (self.father.abs_y if self.is_father_widget() else 0)
    @property
    def abs_right(self)  -> int:
        return self.rect.right  + (self.father.abs_x if self.is_father_widget() else 0)
    @property
    def abs_bottom(self) -> int:
        return self.rect.bottom + (self.father.abs_y if self.is_father_widget() else 0)
    @property
    def abs_pos(self)    -> tuple[int,int]:
        return (self.abs_x, self.abs_y)

    def move_to(self, x: int, y: int) -> "Base":
        self.rect.x = x
        self.rect.y = y
        self._fire(31)
        self.mark_dirty()
        return self

    def resize_to(self, w: int, h: int) -> "Base":
        self.rect.width  = w
        self.rect.height = h
        if self.texture and (self.texture.get_width() != w or
                             self.texture.get_height() != h):
            self.texture = pygame.Surface((w, h), pygame.SRCALPHA)
        self._fire(30)
        self.mark_dirty()
        return self

    # ── hierarchy ─────────────────────────────────────────────────────────────

    def is_father_widget(self) -> bool:
        return (
            self.father is not Window
            and not isinstance(self.father, type)
            and hasattr(self.father, "put")
        )

    def unlink(self) -> None:
        if self.is_father_widget():
            self.father.unparent(self)
            self.father = Window

    def destroy(self) -> None:
        self._fire(28)
        self.unlink()
        Tree.remove(self)
        if self.texture:
            self.texture = None

    def is_container(self) -> bool:
        return False

    def get_childrens(self) -> list:
        return []

    def update(self) -> None:
        self.mark_dirty()

    # ── render ────────────────────────────────────────────────────────────────

    def render_self(self) -> None:
        """Subclasses override this to draw into self.texture."""
        if self.texture is None:
            return
        self.style.fill_surface(self.texture)
        self.style.draw_border(self.texture)
        self.clear_dirty()

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.name!r} rect={self.rect}>"
