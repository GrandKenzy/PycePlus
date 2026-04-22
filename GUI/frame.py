"""
PycePlus.GUI.frame
Layout containers: Frame (base), FlexFrame, GridFrame, FlowFrame, FreeFrame.

All layouts composite children lazily (dirty-flag based).
"""
from __future__ import annotations

import threading
from typing import Literal, TYPE_CHECKING

import pygame

from PycePlus.GUI.base import Base, Padding, Outline, Cursors
from PycePlus.UI.window import Window
from PycePlus.UI.tools.color import Color, colorType

if TYPE_CHECKING:
    pass


# ──────────────────────────────────────────────────────────────────────────────
# Frame  — base container
# ──────────────────────────────────────────────────────────────────────────────

class Frame(Base):
    """
    Base scrollable container. Children are laid out in absolute coords
    unless overridden by a layout subclass.

    Extra parameters (beyond Base)
    --------------------------------
    width, height          : int
    background_color       : colorType
    border_*               : border style params (forwarded to style)
    padding_*              : padding params
    scrollable             : bool
    scroll_orientation     : 'auto' | 'vertical' | 'horizontal' | 'both'
    x, y                   : int  initial position
    """

    def __init__(
        self,
        father: "Frame | Window | None" = None,
        width:  int   = 200,
        height: int   = 200,
        background_color: colorType = (30, 30, 30, 255),
        border_width:  int   = 0,
        border_color:  colorType = (80, 80, 80, 255),
        border_radius: int   = 0,
        border_top_left_radius:    int = -1,
        border_top_right_radius:   int = -1,
        border_bottom_right_radius:int = -1,
        border_bottom_left_radius: int = -1,
        padding_left:   int = 0,
        padding_right:  int = 0,
        padding_top:    int = 0,
        padding_bottom: int = 0,
        scrollable:     bool = False,
        scroll_orientation: Literal["auto","vertical","horizontal","both"] = "auto",
        x: int = 0,
        y: int = 0,
        cursor: Cursors = "arrow",
        name:   str | None = None,
        page:   str | None = None,
        visible: bool = True,
        style:  dict | None = None,
    ):
        _style = style or {}
        _style.setdefault("background_color",           background_color)
        _style.setdefault("border",                     border_width)
        _style.setdefault("border_color",               border_color)
        _style.setdefault("border_radius",              border_radius)
        _style.setdefault("border_top_left_radius",     border_top_left_radius)
        _style.setdefault("border_top_right_radius",    border_top_right_radius)
        _style.setdefault("border_bottom_right_radius", border_bottom_right_radius)
        _style.setdefault("border_bottom_left_radius",  border_bottom_left_radius)
        _style.setdefault("padding_left",   padding_left)
        _style.setdefault("padding_right",  padding_right)
        _style.setdefault("padding_top",    padding_top)
        _style.setdefault("padding_bottom", padding_bottom)
        _style.setdefault("cursor",         cursor)

        super().__init__(father, name, page, style=_style)

        self.rect    = pygame.Rect(x, y, width, height)
        self.texture = pygame.Surface((width, height), pygame.SRCALPHA)
        self.visible = visible

        self.scrollable         = scrollable
        self.scroll_orientation = scroll_orientation
        self._scroll_x: int     = 0
        self._scroll_y: int     = 0

        self._children_lock = threading.RLock()
        self.childrens: list[Base] = []

    # ── child management ─────────────────────────────────────────────────────

    def put(self, widget: Base) -> None:
        """Register a widget as a child."""
        with self._children_lock:
            if widget not in self.childrens:
                self.childrens.append(widget)
                widget.father = self
                widget.page   = self.page
        self.mark_dirty()

    def parent(self, widget: Base) -> None:
        self.put(widget)

    def unparent(self, widget: Base) -> None:
        with self._children_lock:
            if widget in self.childrens:
                self.childrens.remove(widget)
                widget.father = Window
        self.mark_dirty()

    def get_childrens(self) -> list[Base]:
        with self._children_lock:
            return list(self.childrens)

    def is_children(self, widget: Base) -> bool:
        return widget in self.childrens

    def is_container(self) -> bool:
        return True

    # ── scroll helpers ────────────────────────────────────────────────────────

    def scroll(self, dx: int = 0, dy: int = 0) -> None:
        self._scroll_x += dx
        self._scroll_y += dy
        self.mark_dirty()

    def scroll_to(self, x: int = 0, y: int = 0) -> None:
        self._scroll_x = x
        self._scroll_y = y
        self.mark_dirty()

    # ── render ────────────────────────────────────────────────────────────────

    def _layout_children(self) -> None:
        """Override in subclasses to position children before composite."""
        pass

    def render_self(self) -> None:
        """Fill background. Children are composited in composite_children."""
        if self.texture is None or (
            self.texture.get_width()  != self.rect.width or
            self.texture.get_height() != self.rect.height
        ):
            self.texture = pygame.Surface(
                (self.rect.width, self.rect.height), pygame.SRCALPHA)

        self.style.fill_surface(self.texture)
        self.clear_dirty()

    def composite_children(self) -> None:
        """Blit all visible children onto self.texture."""
        if self.texture is None:
            return
        self._layout_children()
        s = self.style
        clip_rect = pygame.Rect(
            s.pad_left, s.pad_top,
            max(1, self.rect.width  - s.pad_left - s.pad_right),
            max(1, self.rect.height - s.pad_top  - s.pad_bottom),
        )
        for child in self.get_childrens():
            if not child.visible or child.page != self.page:
                continue
            if child.texture is None:
                continue
            dest = (
                child.rect.x + self._scroll_x,
                child.rect.y + self._scroll_y,
            )
            self.texture.blit(child.texture, dest)
        self.style.draw_border(self.texture)


# ──────────────────────────────────────────────────────────────────────────────
# FlexFrame
# ──────────────────────────────────────────────────────────────────────────────

class FlexFrame(Frame):
    """
    Flexbox-like layout.

    Parameters
    ----------
    direction   : 'row' | 'column'
    wrap        : bool
    gap         : int   gap between items (px)
    justify     : 'start' | 'center' | 'end' | 'space-between' | 'space-around'
    align       : 'start' | 'center' | 'end' | 'stretch'
    """

    def __init__(
        self,
        father=None,
        direction: Literal["row","column"] = "row",
        wrap:      bool = False,
        gap:       int  = 0,
        justify:   Literal["start","center","end","space-between","space-around"] = "start",
        align:     Literal["start","center","end","stretch"] = "start",
        **kwargs,
    ):
        super().__init__(father, **kwargs)
        self.direction = direction
        self.wrap      = wrap
        self.gap       = gap
        self.justify   = justify
        self.align     = align

    def _layout_children(self) -> None:
        s   = self.style
        pad_h = s.pad_left + s.pad_right
        pad_v = s.pad_top  + s.pad_bottom
        avail_w = max(1, self.rect.width  - pad_h)
        avail_h = max(1, self.rect.height - pad_v)

        children = [c for c in self.get_childrens()
                    if c.visible and c.page == self.page]
        if not children:
            return

        is_row = (self.direction == "row")
        gap    = self.gap

        # position along main axis
        sizes  = [c.width if is_row else c.height for c in children]
        total  = sum(sizes) + gap * max(0, len(children) - 1)

        if self.justify == "start":
            origins = self._place_start(sizes, gap)
        elif self.justify == "end":
            limit   = avail_w if is_row else avail_h
            origins = [limit - total + o for o in self._place_start(sizes, gap)]
        elif self.justify == "center":
            limit   = avail_w if is_row else avail_h
            off     = (limit - total) // 2
            origins = [off + o for o in self._place_start(sizes, gap)]
        elif self.justify == "space-between":
            origins = self._place_between(sizes, avail_w if is_row else avail_h)
        elif self.justify == "space-around":
            origins = self._place_around(sizes, avail_w if is_row else avail_h)
        else:
            origins = self._place_start(sizes, gap)

        cross_size = avail_h if is_row else avail_w

        for i, child in enumerate(children):
            main_pos  = s.pad_left + (s.pad_top if not is_row else 0) + origins[i]
            cross_dim = child.height if is_row else child.width

            if self.align == "start":
                cross_pos = s.pad_top if is_row else s.pad_left
            elif self.align == "end":
                cross_pos = (s.pad_top + cross_size - cross_dim) if is_row else (s.pad_left + cross_size - cross_dim)
            elif self.align == "center":
                cross_pos = (s.pad_top + (cross_size - cross_dim) // 2) if is_row else (s.pad_left + (cross_size - cross_dim) // 2)
            elif self.align == "stretch":
                cross_pos = s.pad_top if is_row else s.pad_left
                if is_row:
                    child.resize_to(child.width, cross_size)
                else:
                    child.resize_to(cross_size, child.height)
            else:
                cross_pos = s.pad_top if is_row else s.pad_left

            if is_row:
                child.rect.x = main_pos
                child.rect.y = cross_pos
            else:
                child.rect.x = cross_pos
                child.rect.y = main_pos

    @staticmethod
    def _place_start(sizes, gap) -> list[int]:
        pos, result = 0, []
        for s in sizes:
            result.append(pos)
            pos += s + gap
        return result

    @staticmethod
    def _place_between(sizes, total) -> list[int]:
        n = len(sizes)
        if n <= 1:
            return [0]
        total_size = sum(sizes)
        space = max(0, total - total_size) // (n - 1)
        pos, result = 0, []
        for s in sizes:
            result.append(pos)
            pos += s + space
        return result

    @staticmethod
    def _place_around(sizes, total) -> list[int]:
        n = len(sizes)
        total_size = sum(sizes)
        space = max(0, total - total_size) // (n + 1) if n else 0
        pos = space
        result = []
        for s in sizes:
            result.append(pos)
            pos += s + space
        return result


# ──────────────────────────────────────────────────────────────────────────────
# GridFrame
# ──────────────────────────────────────────────────────────────────────────────

class GridFrame(Frame):
    """
    Grid layout with fixed columns and uniform or auto-height rows.

    Parameters
    ----------
    columns    : int   number of columns
    col_gap    : int   horizontal gap (px)
    row_gap    : int   vertical gap (px)
    col_widths : list[int] | None   explicit column widths; None = equal split
    """

    def __init__(
        self,
        father=None,
        columns:    int = 2,
        col_gap:    int = 4,
        row_gap:    int = 4,
        col_widths: list[int] | None = None,
        **kwargs,
    ):
        super().__init__(father, **kwargs)
        self.columns    = max(1, columns)
        self.col_gap    = col_gap
        self.row_gap    = row_gap
        self.col_widths = col_widths

    def _layout_children(self) -> None:
        s  = self.style
        children = [c for c in self.get_childrens()
                    if c.visible and c.page == self.page]
        if not children:
            return

        avail_w = max(1, self.rect.width - s.pad_left - s.pad_right)
        cols    = self.columns

        if self.col_widths and len(self.col_widths) >= cols:
            widths = self.col_widths[:cols]
        else:
            cell_w = max(1, (avail_w - self.col_gap * (cols - 1)) // cols)
            widths = [cell_w] * cols

        col_x = [s.pad_left + sum(widths[:i]) + self.col_gap * i for i in range(cols)]
        y     = s.pad_top
        row_h = 0

        for i, child in enumerate(children):
            col = i % cols
            if col == 0 and i > 0:
                y     += row_h + self.row_gap
                row_h  = 0
            child.rect.x = col_x[col]
            child.rect.y = y
            if self.col_widths is None:
                child.resize_to(widths[col], child.height)
            row_h = max(row_h, child.height)


# ──────────────────────────────────────────────────────────────────────────────
# FlowFrame
# ──────────────────────────────────────────────────────────────────────────────

class FlowFrame(Frame):
    """
    Flow (wrapping) layout — items wrap to next line when they exceed width.

    Parameters
    ----------
    gap_x : int   horizontal gap between items
    gap_y : int   vertical gap between rows
    align : 'left' | 'center' | 'right'
    """

    def __init__(
        self,
        father=None,
        gap_x:  int = 4,
        gap_y:  int = 4,
        align:  Literal["left","center","right"] = "left",
        **kwargs,
    ):
        super().__init__(father, **kwargs)
        self.gap_x = gap_x
        self.gap_y = gap_y
        self.align = align

    def _layout_children(self) -> None:
        s  = self.style
        avail_w = max(1, self.rect.width - s.pad_left - s.pad_right)
        children = [c for c in self.get_childrens()
                    if c.visible and c.page == self.page]
        if not children:
            return

        # group into rows
        rows: list[list[Base]] = []
        row:  list[Base]       = []
        row_w = 0

        for child in children:
            cw = child.width + self.gap_x
            if row and row_w + child.width > avail_w:
                rows.append(row)
                row   = [child]
                row_w = cw
            else:
                row.append(child)
                row_w += cw
        if row:
            rows.append(row)

        y = s.pad_top
        for line in rows:
            line_w = sum(c.width for c in line) + self.gap_x * max(0, len(line) - 1)
            row_h  = max((c.height for c in line), default=0)

            if self.align == "left":
                x = s.pad_left
            elif self.align == "center":
                x = s.pad_left + (avail_w - line_w) // 2
            else:   # right
                x = s.pad_left + avail_w - line_w

            for child in line:
                child.rect.x = x
                child.rect.y = y
                x += child.width + self.gap_x

            y += row_h + self.gap_y


# ──────────────────────────────────────────────────────────────────────────────
# FreeFrame
# ──────────────────────────────────────────────────────────────────────────────

class FreeFrame(Frame):
    """
    Free / absolute positioning layout — children keep their own x, y.
    This is identical to the base Frame but semantically explicit.
    """
    pass
