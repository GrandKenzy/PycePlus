"""
PycePlus.CORE.events
Extends the original events module with:
  • Window resize, move, minimize, maximize, restore, close
  • File-drop events
  • Scroll events exposed to widget system
  • IME / text input support
  • Key repeat configurable
"""
from __future__ import annotations

from typing import Callable

import pygame
from PycePlus.UI import exit
from PycePlus.CORE.timec import Time
from PycePlus import __events__ as _EV

# ──────────────────────────────────────────────────────────────────────────────
# Lookup aliases for speed
# ──────────────────────────────────────────────────────────────────────────────

_event_get  = pygame.event.get
_mouse_pos  = pygame.mouse.get_pos
_get_pressed= pygame.key.get_pressed

# ──────────────────────────────────────────────────────────────────────────────
# Registries
# ──────────────────────────────────────────────────────────────────────────────

KEYS_EVENT_REGISTER:    dict[int, list] = {}   # key → [on_press, on_release, on_repeat, flag]
BUTTONS_EVENT_REGISTER: dict[int, list] = {}   # button → [on_press, on_release, on_repeat, dbl, flag, t]
CUSTOM_EVENT_REGISTER:  dict[int, Callable | None] = {}

# ──────────────────────────────────────────────────────────────────────────────
# State  (read by render.exam and widgets)
# ──────────────────────────────────────────────────────────────────────────────

class Info:
    num = 0

current_events:      list = []

X = Y = 0
MOVED_X = MOVED_Y = 0
SCROLL_X = SCROLL_Y = 0
DEFAULT_BUTTONS = [0, 0, 0]

mouse_moved              = False
mouse_motion_checked     = False
mouse_wheel_checked      = False
key_buttons_pressed      = False
mouse_buttons_pressed    = False
window_is_focus          = True
keyboard_is_active       = False
keyboard_input           = False
keys_pressed: list       = []
_mouse_ready             = False

# window state
window_width:  int = 0
window_height: int = 0
window_x:      int = 0
window_y:      int = 0

# drop
dropped_file: str | None = None
dropped_text: str | None = None

# ──────────────────────────────────────────────────────────────────────────────
# Registration helpers
# ──────────────────────────────────────────────────────────────────────────────

def register_key(
    key: int,
    on_press:   Callable | None = None,
    on_release: Callable | None = None,
    on_repeat:  Callable | None = None,
) -> None:
    KEYS_EVENT_REGISTER[key] = [on_press, on_release, on_repeat, False]


def register_button(
    button:      int,
    on_press:    Callable | None = None,
    on_release:  Callable | None = None,
    on_repeat:   Callable | None = None,
    double_click:Callable | None = None,
) -> None:
    BUTTONS_EVENT_REGISTER[button] = [on_press, on_release, on_repeat,
                                       double_click, False, 0]


def register_custom_event(event: int, on_event: Callable | None = None) -> None:
    CUSTOM_EVENT_REGISTER[event] = on_event

# ──────────────────────────────────────────────────────────────────────────────
# Main poll loop — called once per frame from CORE.main
# ──────────────────────────────────────────────────────────────────────────────

def exam() -> None:
    global current_events
    global mouse_moved, mouse_motion_checked, mouse_wheel_checked
    global key_buttons_pressed, mouse_buttons_pressed
    global X, Y, MOVED_X, MOVED_Y, SCROLL_X, SCROLL_Y
    global keyboard_is_active, keyboard_input
    global window_is_focus, _mouse_ready
    global dropped_file, dropped_text
    global window_width, window_height, window_x, window_y

    current_events  = _event_get()
    mouse_moved     = False
    keyboard_input  = False
    dropped_file    = None
    dropped_text    = None
    SCROLL_X        = 0
    SCROLL_Y        = 0

    keys_pressed_raw = _get_pressed()
    keyboard_is_active = any(keys_pressed_raw)

    # ── repeating actions ────────────────────────────────────────────────────
    for k, (_, _, on_repeat, flag) in KEYS_EVENT_REGISTER.items():
        if flag:
            if on_repeat:
                on_repeat()
            if not key_buttons_pressed:
                Info.num += 1
            key_buttons_pressed = True

    for b, rec in BUTTONS_EVENT_REGISTER.items():
        if rec[4]:   # pressed flag
            if rec[2]:   # on_repeat
                rec[2]()
            if not mouse_buttons_pressed:
                Info.num += 1
            mouse_buttons_pressed = True
        DEFAULT_BUTTONS[b - 1] = 2 if DEFAULT_BUTTONS[b - 1] == 2 else DEFAULT_BUTTONS[b - 1]

    # ── process raw events ───────────────────────────────────────────────────
    for event in current_events:
        et = event.type

        # ── quit ────────────────────────────────────────────────────────────
        if et == pygame.QUIT:
            exit()

        # ── mouse motion ────────────────────────────────────────────────────
        elif et == pygame.MOUSEMOTION:
            _mouse_ready = True
            MOVED_X, MOVED_Y = event.rel
            X, Y = _mouse_pos()
            mouse_moved = True
            if MOVED_X != 0 or MOVED_Y != 0:
                if not mouse_motion_checked:
                    Info.num += 1
                mouse_motion_checked = True

        # ── scroll ──────────────────────────────────────────────────────────
        elif et == pygame.MOUSEWHEEL:
            SCROLL_X, SCROLL_Y = event.x, event.y
            if SCROLL_X != 0 or SCROLL_Y != 0:
                if not mouse_wheel_checked:
                    Info.num += 1
                mouse_wheel_checked = True

        # ── key down ────────────────────────────────────────────────────────
        elif et == pygame.KEYDOWN:
            k = event.key
            if k in KEYS_EVENT_REGISTER:
                KEYS_EVENT_REGISTER[k][3] = True
                cb = KEYS_EVENT_REGISTER[k][0]
                if cb:
                    cb()
            Info.num      += 1
            keyboard_input = True

        # ── key up ──────────────────────────────────────────────────────────
        elif et == pygame.KEYUP:
            k = event.key
            if k in KEYS_EVENT_REGISTER:
                KEYS_EVENT_REGISTER[k][3] = False
                cb = KEYS_EVENT_REGISTER[k][1]
                if cb:
                    cb()

        # ── mouse button down ────────────────────────────────────────────────
        elif et == pygame.MOUSEBUTTONDOWN:
            b = event.button
            if b in BUTTONS_EVENT_REGISTER:
                rec = BUTTONS_EVENT_REGISTER[b]
                rec[4] = True
                delta  = rec[5]
                if Time.current_ticks - delta < 0.4:
                    if rec[3]:
                        rec[3]()
                else:
                    rec[5] = Time.current_ticks
                    if rec[0]:
                        rec[0]()
            if 1 <= b <= 3:
                DEFAULT_BUTTONS[b - 1] = 1
            Info.num += 1

        # ── mouse button up ──────────────────────────────────────────────────
        elif et == pygame.MOUSEBUTTONUP:
            b = event.button
            if b in BUTTONS_EVENT_REGISTER:
                rec = BUTTONS_EVENT_REGISTER[b]
                rec[4] = False
                if rec[1]:
                    rec[1]()
            if 1 <= b <= 3:
                DEFAULT_BUTTONS[b - 1] = 0
            Info.num += 1

        # ── window events ────────────────────────────────────────────────────
        elif et == pygame.WINDOWFOCUSGAINED:
            window_is_focus = True
            _EV.emit("system.window.gained", Time.current_ticks)

        elif et == pygame.WINDOWFOCUSLOST:
            window_is_focus = False
            _EV.emit("system.window.lost", Time.current_ticks)

        elif et == pygame.WINDOWRESIZED:
            window_width  = event.x
            window_height = event.y
            Info.num += 1
            _EV.emit("system.window.resized", Time.current_ticks,
                     event.x, event.y)

        elif et == pygame.WINDOWMOVED:
            window_x = event.x
            window_y = event.y
            _EV.emit("system.window.moved", Time.current_ticks,
                     event.x, event.y)

        elif et == pygame.WINDOWMINIMIZED:
            _EV.emit("system.window.minimized", Time.current_ticks)

        elif et == pygame.WINDOWMAXIMIZED:
            _EV.emit("system.window.maximized", Time.current_ticks)

        elif et == pygame.WINDOWRESTORED:
            _EV.emit("system.window.restored", Time.current_ticks)

        elif et == pygame.WINDOWCLOSE:
            _EV.emit("system.window.close", Time.current_ticks)

        # ── file / text drop ─────────────────────────────────────────────────
        elif et == pygame.DROPFILE:
            dropped_file = event.file
            Info.num    += 1
            _EV.emit("file.drop", Time.current_ticks, event.file)

        elif et == pygame.DROPTEXT:
            dropped_text = event.text
            Info.num    += 1
            _EV.emit("text.drop", Time.current_ticks, event.text)

        # ── custom events ────────────────────────────────────────────────────
        elif et in CUSTOM_EVENT_REGISTER:
            cb = CUSTOM_EVENT_REGISTER[et]
            if cb:
                cb(event)
            Info.num += 1
