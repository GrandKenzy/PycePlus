"""
PycePlus.GUI.interface_man.render
Dirty-flag rendering — only re-renders widgets whose _dirty flag is set.
"""
from __future__ import annotations

from typing import TYPE_CHECKING
import threading

import pygame

if TYPE_CHECKING:
    from PycePlus.GUI.base import Base

from PycePlus.GUI.interface_man import Tree
from PycePlus.UI.window import Window
from PycePlus.CORE import events
from PycePlus.CORE.timec import Time

_blit_lock = threading.RLock()

# Ordered list of root widgets that are visible on the current page,
# reversed for hit-testing (front-most first).
renderable: list["Base"] = []


# ──────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ──────────────────────────────────────────────────────────────────────────────

def _render_widget(widget: "Base") -> None:
    """Recursively render dirty widgets depth-first."""
    if widget.is_dirty:
        widget.render_self()

    if widget.is_container():
        for child in widget.get_childrens():
            if not child.visible:
                continue
            if child.page != widget.page:
                continue
            _render_widget(child)

        # After children render, re-composite if container was dirty
        widget.composite_children()   # only Frame / layout containers have this


def _collect(widget: "Base", into: list["Base"]) -> None:
    """Flatten visible, on-page widgets into *into* (depth-first)."""
    into.append(widget)
    if widget.is_container():
        for child in widget.get_childrens():
            if child.visible and child.page == Tree.current_page():
                _collect(child, into)


# ──────────────────────────────────────────────────────────────────────────────
# update() — called every frame when Application.REFRESH is True
# ──────────────────────────────────────────────────────────────────────────────

def update() -> None:
    global renderable
    current_page = Tree.current_page()
    bliteable: list[tuple[pygame.Surface, tuple[int, int]]] = []

    with _blit_lock:
        flat: list["Base"] = []

        for widget in Tree.widgets:
            if not widget.visible:
                continue
            if widget.is_father_widget():
                continue
            if widget.page != current_page:
                continue

            # render dirty chain
            _render_widget(widget)
            _collect(widget, flat)

            if widget.texture is not None:
                bliteable.append((widget.texture, widget.rect.topleft))

        Window.blits(bliteable)
        renderable = list(reversed(flat))   # front-most first for hit-testing


# ──────────────────────────────────────────────────────────────────────────────
# exam() — called every frame to process input against rendered widgets
# ──────────────────────────────────────────────────────────────────────────────

def exam() -> None:
    if not events.window_is_focus or not events._mouse_ready:
        return

    X, Y  = events.X, events.Y
    LEFT, MIDDLE, RIGHT = events.DEFAULT_BUTTONS
    SCROLL_X, SCROLL_Y  = events.SCROLL_X, events.SCROLL_Y

    focus: "Base | None" = None

    for widget in renderable:
        lx = X - widget.abs_x
        ly = Y - widget.abs_y
        COLLIDE = widget.rect.collidepoint(lx + widget.rect.x,
                                           ly + widget.rect.y)

        # ── pointer events ────────────────────────────────────────────────────
        if not focus and COLLIDE:
            focus = widget

            # cursor
            try:
                pygame.mouse.set_cursor(widget.cursor)
            except Exception:
                pass

            if widget.is_hover:
                widget._fire(11, (lx, ly))   # hovering
            else:
                widget._fire(9,  (lx, ly))   # hover enter
                widget.is_hover = True

            # scroll
            if SCROLL_Y > 0:  widget._fire(15, SCROLL_Y)
            if SCROLL_Y < 0:  widget._fire(16, SCROLL_Y)

            # drag
            if LEFT == 1 and not widget._dragging:
                widget._dragging    = True
                widget._drag_origin = (lx, ly)
                widget._fire(17, (lx, ly))   # drag.start
            elif LEFT == 2 and widget._dragging:
                widget._fire(18, (lx, ly))   # drag.move
            elif LEFT == 0 and widget._dragging:
                widget._dragging = False
                widget._fire(19, (lx, ly))   # drag.end

            # left button
            if LEFT == 1 and widget._bflags[0] == 0:
                widget._fire(0, (lx, ly))    # left.click
                widget._bflags[0] = 1
                from PycePlus.CORE.timec import Time as T
                if T.current_ticks - widget._timers[0] < 0.4:
                    widget._fire(12, (lx, ly))  # double-click
                widget._timers[0] = T.current_ticks
            elif LEFT == 2:
                widget._fire(2, (lx, ly))    # left.repeat
            elif LEFT == 0 and widget._bflags[0] == 1:
                widget._fire(1, (lx, ly))    # left.release
                widget._bflags[0] = 0

            # middle button
            if MIDDLE == 1 and widget._bflags[1] == 0:
                widget._fire(3, (lx, ly))
                widget._bflags[1] = 1
            elif MIDDLE == 2:
                widget._fire(5, (lx, ly))
            elif MIDDLE == 0 and widget._bflags[1] == 1:
                widget._fire(4, (lx, ly))
                widget._bflags[1] = 0

            # right button
            if RIGHT == 1 and widget._bflags[2] == 0:
                widget._fire(6, (lx, ly))
                widget._bflags[2] = 1
                from PycePlus.CORE.timec import Time as T
                if T.current_ticks - widget._timers[2] < 0.4:
                    widget._fire(13, (lx, ly))  # right double-click
                widget._timers[2] = T.current_ticks
            elif RIGHT == 2:
                widget._fire(8, (lx, ly))
            elif RIGHT == 0 and widget._bflags[2] == 1:
                widget._fire(7, (lx, ly))
                widget._bflags[2] = 0

            # focus
            if (LEFT == 1 or MIDDLE == 1 or RIGHT == 1) and not widget.is_focus:
                widget.is_focus = True
                widget._fire(23)   # focus.gain

        else:
            if not COLLIDE and widget.is_hover:
                widget._fire(10, (lx, ly))   # mouse.leave
                widget.is_hover = False
                widget._dragging = False

            # lose focus
            if widget.is_focus and (LEFT == 1 or MIDDLE == 1 or RIGHT == 1):
                widget.is_focus = False
                widget._fire(24)   # focus.lose

    # Keyboard events forwarded to focused widget
    if events.keyboard_input:
        for widget in renderable:
            if widget.is_focus:
                for ev in events.current_events:
                    if ev.type == pygame.KEYDOWN:
                        widget._fire(20, ev)
                    elif ev.type == pygame.KEYUP:
                        widget._fire(21, ev)
                break

    # File-drop events
    for ev in events.current_events:
        if ev.type == pygame.DROPFILE:
            mx, my = events.X, events.Y
            for widget in renderable:
                lx = mx - widget.abs_x
                ly = my - widget.abs_y
                if widget.rect.collidepoint(lx + widget.rect.x,
                                            ly + widget.rect.y):
                    widget._fire(25, ev.file)   # drop.file
                    break
        elif ev.type == pygame.DROPTEXT:
            mx, my = events.X, events.Y
            for widget in renderable:
                lx = mx - widget.abs_x
                ly = my - widget.abs_y
                if widget.rect.collidepoint(lx + widget.rect.x,
                                            ly + widget.rect.y):
                    widget._fire(26, ev.text)   # drop.text
                    break
