"""
PycePlus.GUI.interface_man.render
Dirty-flag rendering — only re-renders widgets whose _dirty flag is set.
"""
from __future__ import annotations

import threading
from typing import TYPE_CHECKING

import pygame

if TYPE_CHECKING:
    from PycePlus.GUI.base import Base

from PycePlus.GUI.interface_man import Tree
from PycePlus.UI.window import Window
from PycePlus.CORE import events
from PycePlus.CORE.timec import Time

_blit_lock = threading.RLock()
renderable: list["Base"] = []
_current_cursor = None


def _render_widget(widget: "Base") -> None:
    if widget.is_dirty:
        widget.render_self()
    if widget.is_container():
        for child in widget.get_childrens():
            if not child.visible or child.page != widget.page:
                continue
            _render_widget(child)
        widget.composite_children()


def _collect(widget: "Base", into: list["Base"]) -> None:
    into.append(widget)
    if widget.is_container():
        for child in widget.get_childrens():
            if child.visible and child.page == Tree.current_page():
                _collect(child, into)


def update() -> None:
    global renderable, _current_cursor
    current_page = Tree.current_page()
    bliteable: list[tuple[pygame.Surface, tuple[int, int]]] = []
    flat: list["Base"] = []

    with _blit_lock:
        gl_mode = Window.is_opengl()

        for widget in Tree.widgets:
            if not widget.visible or widget.page != current_page:
                continue

            # Only root-level widgets are blitted directly; children are composited into their parent.
            if widget.is_father_widget():
                continue
            

            _render_widget(widget)
            _collect(widget, flat)

            if not gl_mode and widget.texture is not None:
                bliteable.append((widget.texture, (widget.abs_x, widget.abs_y)))

        if not gl_mode:
            Window.blits(bliteable)

        renderable = list(reversed(flat))


def _hit_test(widget: "Base", x: int, y: int) -> bool:
    return pygame.Rect(
        widget.abs_x,
        widget.abs_y,
        widget.rect.width,
        widget.rect.height,
    ).collidepoint(x, y)


def exam() -> None:
    global _current_cursor
    if not events.window_is_focus:
        return

    X, Y = events.X, events.Y
    LEFT, MIDDLE, RIGHT = events.DEFAULT_BUTTONS
    SCROLL_X, SCROLL_Y = events.SCROLL_X, events.SCROLL_Y

    hovered_any = False

    for widget in renderable:
        collided = _hit_test(widget, X, Y)
        local = (X - widget.abs_x, Y - widget.abs_y)

        if collided:
            hovered_any = True
            if widget.cursor != _current_cursor:
                try:
                    pygame.mouse.set_cursor(widget.cursor)
                    _current_cursor = widget.cursor
                except Exception:
                    pass

            if not widget.is_hover:
                widget.is_hover = True
                widget._fire(9, local)
            else:
                widget._fire(11, local)

            if SCROLL_Y > 0:
                widget._fire(15, SCROLL_Y)
            elif SCROLL_Y < 0:
                widget._fire(16, SCROLL_Y)

            if LEFT == 1 and not widget._dragging:
                widget._dragging = True
                widget._drag_origin = local
                widget._fire(17, local)
            elif LEFT == 2 and widget._dragging:
                widget._fire(18, local)
            elif LEFT == 0 and widget._dragging:
                widget._dragging = False
                widget._fire(19, local)

            if LEFT == 1 and widget._bflags[0] == 0:
                widget._fire(0, local)
                widget._bflags[0] = 1
                if Time.current_ticks - widget._timers[0] < 0.4:
                    widget._fire(12, local)
                widget._timers[0] = Time.current_ticks
            elif LEFT == 2:
                widget._fire(2, local)
            elif LEFT == 0 and widget._bflags[0] == 1:
                widget._fire(1, local)
                widget._bflags[0] = 0

            if MIDDLE == 1 and widget._bflags[1] == 0:
                widget._fire(3, local)
                widget._bflags[1] = 1
            elif MIDDLE == 2:
                widget._fire(5, local)
            elif MIDDLE == 0 and widget._bflags[1] == 1:
                widget._fire(4, local)
                widget._bflags[1] = 0

            if RIGHT == 1 and widget._bflags[2] == 0:
                widget._fire(6, local)
                widget._bflags[2] = 1
                if Time.current_ticks - widget._timers[2] < 0.4:
                    widget._fire(13, local)
                widget._timers[2] = Time.current_ticks
            elif RIGHT == 2:
                widget._fire(8, local)
            elif RIGHT == 0 and widget._bflags[2] == 1:
                widget._fire(7, local)
                widget._bflags[2] = 0

            if (LEFT == 1 or MIDDLE == 1 or RIGHT == 1) and not widget.is_focus:
                widget.is_focus = True
                widget._fire(23)
        else:
            if widget.is_hover:
                widget.is_hover = False
                widget._dragging = False
                widget._fire(10, local)
                widget.mark_dirty()

    if not hovered_any:
        _current_cursor = None

    if events.keyboard_input:
        for widget in renderable:
            if widget.is_focus:
                for ev in events.current_events:
                    if ev.type == pygame.KEYDOWN:
                        widget._fire(20, ev)
                    elif ev.type == pygame.KEYUP:
                        widget._fire(21, ev)
                break

    for ev in events.current_events:
        if ev.type == pygame.DROPFILE:
            mx, my = events.X, events.Y
            for widget in renderable:
                if _hit_test(widget, mx, my):
                    widget._fire(25, ev.file)
                    break
        elif ev.type == pygame.DROPTEXT:
            mx, my = events.X, events.Y
            for widget in renderable:
                if _hit_test(widget, mx, my):
                    widget._fire(26, ev.text)
                    break
