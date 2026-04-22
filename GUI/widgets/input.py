"""
PycePlus.GUI.widgets.input
Professional text input and multi-line textbox widgets.

TextInput  — single-line input (like an HTML <input type="text">)
TextBox    — multi-line editor styled like VS Code

Features
--------
  • Cursor blink, selection highlight
  • Ctrl+A (select all), Ctrl+C/V/X (clipboard)
  • Backspace, Delete, Home, End, arrow keys
  • Placeholder text
  • Password mode (mask characters)
  • Max-length limit
  • Auto-scroll cursor into view (TextBox)
  • Line numbers (TextBox)
  • Syntax hint colouring hooks (TextBox)
"""
from __future__ import annotations

import time
import threading
from typing import Callable, Literal

import pygame

from PycePlus.GUI.base import Base
from PycePlus.GUI.interface_man.style import compile_style
from PycePlus.UI.tools.color import Color, colorType
from PycePlus.UI.tools.font  import Font

# clipboard
try:
    import pyperclip as _clip
    def _clipboard_get()     -> str:  return _clip.paste()
    def _clipboard_set(s: str) -> None: _clip.copy(s)
except ImportError:
    def _clipboard_get()       -> str:  return ""
    def _clipboard_set(s: str) -> None: pass


# ──────────────────────────────────────────────────────────────────────────────
# TextInput  — single line
# ──────────────────────────────────────────────────────────────────────────────

class TextInput(Base):
    """
    Single-line professional text input.

    Parameters
    ----------
    value       : str    initial text
    placeholder : str    shown when empty
    max_length  : int    0 = unlimited
    password    : bool   show bullets instead of chars
    on_change   : Callable[[str], None] | None
    on_submit   : Callable[[str], None] | None   fired on Enter
    """

    _BLINK_RATE = 0.55   # seconds per blink half-cycle

    def __init__(
        self,
        father=None,
        value:       str  = "",
        placeholder: str  = "Type here…",
        max_length:  int  = 0,
        password:    bool = False,
        font:        Font | None = None,
        width:       int  = 200,
        height:      int  = 36,
        style:       dict | None = None,
        on_change:   Callable | None = None,
        on_submit:   Callable | None = None,
        x: int = 0,
        y: int = 0,
        name: str | None = None,
        page: str | None = None,
        visible: bool = True,
    ):
        _default = {
            "background_color": (30, 31, 35, 255),
            "color":            (212, 212, 212, 255),
            "border":           1,
            "border_color":     (60, 60, 70, 255),
            "border_radius":    5,
            "padding_left":     8,
            "padding_right":    8,
            "font_size":        14,
            "cursor":           "ibeam",
        }
        _style = {**_default, **(style or {})}
        super().__init__(father, name, page, style=_style)

        self._value:      list[str] = list(value)
        self.placeholder  = placeholder
        self.max_length   = max_length
        self.password     = password
        self._on_change   = on_change
        self._on_submit   = on_submit
        self.visible      = visible

        self._font = font or Font(None, self._style.font_size)

        # cursor
        self._cur:     int  = len(self._value)
        self._sel_start: int | None = None
        self._offset:  int  = 0          # horizontal scroll offset in chars
        self._blink_t: float = time.perf_counter()
        self._blink_on: bool = True

        # focused styles
        self._focus_style = compile_style({**_style,
            "border_color": (86, 156, 214, 255),
            "border": 1})

        self.rect    = pygame.Rect(x, y, width, height)
        self.texture = pygame.Surface((width, height), pygame.SRCALPHA)

        # bind events
        self.bind("mouse.button.left.click",   self._on_mouse_click)
        self.bind("key.down",                  self._on_key)
        self.bind("focus.gain",                lambda w: w.mark_dirty())
        self.bind("focus.lose",                lambda w: w.mark_dirty())
        self.mark_dirty()

    # ── value ─────────────────────────────────────────────────────────────────

    @property
    def value(self) -> str:
        return "".join(self._value)

    @value.setter
    def value(self, v: str) -> None:
        self._value = list(v)
        self._cur   = len(self._value)
        self._sel_start = None
        self.mark_dirty()

    def _display_text(self) -> str:
        if self.password:
            return "●" * len(self._value)
        return "".join(self._value)

    # ── selection helpers ─────────────────────────────────────────────────────

    def _sel_range(self) -> tuple[int, int] | None:
        if self._sel_start is None:
            return None
        lo = min(self._cur, self._sel_start)
        hi = max(self._cur, self._sel_start)
        return (lo, hi)

    def _delete_selection(self) -> None:
        r = self._sel_range()
        if r:
            self._value = self._value[:r[0]] + self._value[r[1]:]
            self._cur   = r[0]
            self._sel_start = None

    # ── mouse click → position cursor ────────────────────────────────────────

    def _on_mouse_click(self, widget, pos) -> None:
        px = pos[0] - self._style.pad_left
        text = self._display_text()
        best, best_x = 0, 0
        for i in range(len(text) + 1):
            w, _ = self._font.size(text[:i])
            if abs(w - self._offset - px) < abs(best_x - px):
                best   = i
                best_x = w - self._offset
        self._cur       = best
        self._sel_start = None
        self.mark_dirty()

    # ── keyboard handler ─────────────────────────────────────────────────────

    def _on_key(self, widget, event: pygame.event.Event) -> None:
        key  = event.key
        mod  = event.mod
        ctrl = mod & pygame.KMOD_CTRL
        shift= mod & pygame.KMOD_SHIFT

        # ── navigation ──────────────────────────────────────────────────────
        if key == pygame.K_LEFT:
            if shift and self._sel_start is None:
                self._sel_start = self._cur
            elif not shift:
                self._sel_start = None
            self._cur = max(0, self._cur - 1)

        elif key == pygame.K_RIGHT:
            if shift and self._sel_start is None:
                self._sel_start = self._cur
            elif not shift:
                self._sel_start = None
            self._cur = min(len(self._value), self._cur + 1)

        elif key == pygame.K_HOME:
            if shift and self._sel_start is None:
                self._sel_start = self._cur
            elif not shift:
                self._sel_start = None
            self._cur = 0

        elif key == pygame.K_END:
            if shift and self._sel_start is None:
                self._sel_start = self._cur
            elif not shift:
                self._sel_start = None
            self._cur = len(self._value)

        # ── delete ──────────────────────────────────────────────────────────
        elif key == pygame.K_BACKSPACE:
            if self._sel_range():
                self._delete_selection()
            elif self._cur > 0:
                if ctrl:
                    # delete word
                    i = self._cur - 1
                    while i > 0 and self._value[i-1] != " ":
                        i -= 1
                    self._value = self._value[:i] + self._value[self._cur:]
                    self._cur = i
                else:
                    self._value.pop(self._cur - 1)
                    self._cur -= 1

        elif key == pygame.K_DELETE:
            if self._sel_range():
                self._delete_selection()
            elif self._cur < len(self._value):
                self._value.pop(self._cur)

        # ── clipboard ───────────────────────────────────────────────────────
        elif ctrl and key == pygame.K_a:
            self._sel_start = 0
            self._cur       = len(self._value)

        elif ctrl and key == pygame.K_c:
            r = self._sel_range()
            if r:
                _clipboard_set("".join(self._value[r[0]:r[1]]))

        elif ctrl and key == pygame.K_x:
            r = self._sel_range()
            if r:
                _clipboard_set("".join(self._value[r[0]:r[1]]))
                self._delete_selection()

        elif ctrl and key == pygame.K_v:
            clip = _clipboard_get()
            self._delete_selection()
            for ch in clip:
                if self.max_length and len(self._value) >= self.max_length:
                    break
                self._value.insert(self._cur, ch)
                self._cur += 1

        # ── submit ──────────────────────────────────────────────────────────
        elif key == pygame.K_RETURN or key == pygame.K_KP_ENTER:
            if self._on_submit:
                self._on_submit(self.value)

        # ── printable char ───────────────────────────────────────────────────
        else:
            char = event.unicode
            if char and char.isprintable():
                if self.max_length and len(self._value) >= self.max_length:
                    pass
                else:
                    self._delete_selection()
                    self._value.insert(self._cur, char)
                    self._cur += 1
                    if self._on_change:
                        self._on_change(self.value)
                    self._fire(32)

        self.mark_dirty()

    # ── render ────────────────────────────────────────────────────────────────

    def render_self(self) -> None:
        if self.texture is None:
            return

        w, h  = self.rect.width, self.rect.height
        cs    = self._focus_style if self.is_focus else self._style

        cs.fill_surface(self.texture)

        pad_l = cs.pad_left
        pad_r = cs.pad_right
        inner_w = w - pad_l - pad_r

        text = self._display_text()
        empty = len(text) == 0

        # Adjust horizontal offset so cursor is visible
        cur_x, _ = self._font.size(text[:self._cur])
        if cur_x - self._offset > inner_w - 4:
            self._offset = cur_x - inner_w + 4
        elif cur_x - self._offset < 0:
            self._offset = max(0, cur_x - 4)

        # Selection background
        r = self._sel_range()
        if r and self.is_focus:
            sx, _ = self._font.size(text[:r[0]])
            ex, _ = self._font.size(text[:r[1]])
            sel_rect = pygame.Rect(
                pad_l + sx - self._offset,
                (h - self._font.size("A")[1]) // 2,
                ex - sx, self._font.size("A")[1])
            pygame.draw.rect(self.texture, (38, 79, 120, 200), sel_rect)

        # Text
        col = Color(120, 120, 130) if empty else cs.color
        display = self.placeholder if empty else text
        clip_surf = pygame.Surface((inner_w, h), pygame.SRCALPHA)
        txt_surf  = self._font.render(display, col)
        if txt_surf:
            ty = (h - txt_surf.get_height()) // 2
            clip_surf.blit(txt_surf, (-self._offset, ty))
        self.texture.blit(clip_surf, (pad_l, 0))

        # Cursor blink
        now = time.perf_counter()
        if now - self._blink_t >= self._BLINK_RATE:
            self._blink_on = not self._blink_on
            self._blink_t  = now

        if self.is_focus and self._blink_on:
            cx = pad_l + cur_x - self._offset
            cy1 = (h - self._font.size("A")[1]) // 2
            cy2 = cy1 + self._font.size("A")[1]
            pygame.draw.line(self.texture, (180, 180, 200, 255),
                             (cx, cy1), (cx, cy2), 1)

        cs.draw_border(self.texture)
        self.clear_dirty()


# ──────────────────────────────────────────────────────────────────────────────
# TextBox  — multi-line editor (VS Code style)
# ──────────────────────────────────────────────────────────────────────────────

class TextBox(Base):
    """
    Multi-line text editor styled like VS Code.

    Parameters
    ----------
    value         : str    initial content (newlines supported)
    line_numbers  : bool   show gutter with line numbers
    tab_width     : int    spaces per tab key press
    on_change     : Callable[[str], None] | None
    """

    _BLINK_RATE   = 0.55
    _LINE_HEIGHT  = 20    # pixels per line (approximate; updated from font)

    def __init__(
        self,
        father=None,
        value:       str  = "",
        line_numbers:bool  = True,
        tab_width:   int   = 4,
        font:        Font | None = None,
        width:       int   = 480,
        height:      int   = 300,
        style:       dict | None = None,
        on_change:   Callable | None = None,
        x: int = 0,
        y: int = 0,
        name: str | None = None,
        page: str | None = None,
        visible: bool = True,
    ):
        _default = {
            "background_color": (30, 30, 30, 255),
            "color":            (212, 212, 212, 255),
            "border":           1,
            "border_color":     (60, 60, 70, 255),
            "border_radius":    4,
            "font_size":        14,
            "cursor":           "ibeam",
        }
        _style = {**_default, **(style or {})}
        super().__init__(father, name, page, style=_style)

        self._lines: list[list[str]] = [list(l) for l in value.split("\n")]
        self.line_numbers  = line_numbers
        self.tab_width     = tab_width
        self._on_change    = on_change
        self.visible       = visible

        self._font = font or Font(None, self._style.font_size)

        # cursor (row, col)
        self._row:  int = 0
        self._col:  int = 0
        # selection anchor
        self._sel_r: int | None = None
        self._sel_c: int | None = None
        # scroll
        self._scroll_y: int = 0   # first visible line index
        self._scroll_x: int = 0   # horizontal pixel offset

        self._blink_t:  float = time.perf_counter()
        self._blink_on: bool  = True

        # sizing
        self._lh = max(16, self._font.size("A")[1] + 2)
        self._gutter_w = 48 if line_numbers else 0

        self.rect    = pygame.Rect(x, y, width, height)
        self.texture = pygame.Surface((width, height), pygame.SRCALPHA)

        self.bind("mouse.button.left.click",  self._on_click)
        self.bind("key.down",                 self._on_key)
        self.bind("mouse.scroll.up",          lambda w, v: self._do_scroll(-3))
        self.bind("mouse.scroll.down",        lambda w, v: self._do_scroll(3))
        self.bind("focus.gain",               lambda w: w.mark_dirty())
        self.bind("focus.lose",               lambda w: w.mark_dirty())
        self.mark_dirty()

    # ── value ─────────────────────────────────────────────────────────────────

    @property
    def value(self) -> str:
        return "\n".join("".join(ln) for ln in self._lines)

    @value.setter
    def value(self, v: str) -> None:
        self._lines  = [list(l) for l in v.split("\n")]
        self._row    = 0
        self._col    = 0
        self.mark_dirty()

    # ── scroll ────────────────────────────────────────────────────────────────

    def _do_scroll(self, delta: int) -> None:
        max_s = max(0, len(self._lines) - self._visible_lines())
        self._scroll_y = max(0, min(max_s, self._scroll_y + delta))
        self.mark_dirty()

    def _visible_lines(self) -> int:
        return max(1, (self.rect.height - 4) // self._lh)

    def _ensure_cursor_visible(self) -> None:
        vis = self._visible_lines()
        if self._row < self._scroll_y:
            self._scroll_y = self._row
        elif self._row >= self._scroll_y + vis:
            self._scroll_y = self._row - vis + 1

    # ── click → position cursor ───────────────────────────────────────────────

    def _on_click(self, widget, pos) -> None:
        px, py = pos
        row = self._scroll_y + max(0, (py - 2) // self._lh)
        row = min(row, len(self._lines) - 1)
        line_text = "".join(self._lines[row])
        col = 0
        best_d = abs(self._font.size("")[0] - (px - self._gutter_w + self._scroll_x))
        for i in range(len(line_text) + 1):
            w, _ = self._font.size(line_text[:i])
            d = abs(w - (px - self._gutter_w + self._scroll_x))
            if d < best_d:
                best_d = d
                col    = i
        self._row = row
        self._col = col
        self._sel_r = None
        self.mark_dirty()

    # ── keyboard ─────────────────────────────────────────────────────────────

    def _on_key(self, widget, event: pygame.event.Event) -> None:
        key  = event.key
        mod  = event.mod
        ctrl = mod & pygame.KMOD_CTRL
        shift= mod & pygame.KMOD_SHIFT
        row, col = self._row, self._col
        lines = self._lines

        def clamp_col():
            self._col = min(self._col, len(lines[self._row]))

        if key == pygame.K_UP:
            if shift and self._sel_r is None:
                self._sel_r, self._sel_c = row, col
            elif not shift:
                self._sel_r = None
            self._row = max(0, row - 1)
            clamp_col()

        elif key == pygame.K_DOWN:
            if shift and self._sel_r is None:
                self._sel_r, self._sel_c = row, col
            elif not shift:
                self._sel_r = None
            self._row = min(len(lines) - 1, row + 1)
            clamp_col()

        elif key == pygame.K_LEFT:
            if shift and self._sel_r is None:
                self._sel_r, self._sel_c = row, col
            elif not shift:
                self._sel_r = None
            if col > 0:
                self._col -= 1
            elif row > 0:
                self._row -= 1
                self._col  = len(lines[self._row])

        elif key == pygame.K_RIGHT:
            if shift and self._sel_r is None:
                self._sel_r, self._sel_c = row, col
            elif not shift:
                self._sel_r = None
            if col < len(lines[row]):
                self._col += 1
            elif row < len(lines) - 1:
                self._row += 1
                self._col  = 0

        elif key == pygame.K_HOME:
            self._col = 0
        elif key == pygame.K_END:
            self._col = len(lines[row])

        elif key == pygame.K_PAGEUP:
            self._row = max(0, row - self._visible_lines())
            clamp_col()
        elif key == pygame.K_PAGEDOWN:
            self._row = min(len(lines) - 1, row + self._visible_lines())
            clamp_col()

        elif key == pygame.K_RETURN or key == pygame.K_KP_ENTER:
            tail = lines[row][col:]
            lines[row] = lines[row][:col]
            lines.insert(row + 1, tail)
            self._row += 1
            self._col  = 0
            self._notify_change()

        elif key == pygame.K_BACKSPACE:
            if col > 0:
                lines[row].pop(col - 1)
                self._col -= 1
            elif row > 0:
                prev_len = len(lines[row - 1])
                lines[row - 1].extend(lines[row])
                lines.pop(row)
                self._row -= 1
                self._col  = prev_len
            self._notify_change()

        elif key == pygame.K_DELETE:
            if col < len(lines[row]):
                lines[row].pop(col)
            elif row < len(lines) - 1:
                lines[row].extend(lines[row + 1])
                lines.pop(row + 1)
            self._notify_change()

        elif key == pygame.K_TAB:
            spaces = " " * self.tab_width
            for ch in spaces:
                lines[row].insert(col, ch)
                self._col += 1
            self._notify_change()

        elif ctrl and key == pygame.K_a:
            self._sel_r, self._sel_c = 0, 0
            self._row = len(lines) - 1
            self._col = len(lines[-1])

        elif ctrl and key == pygame.K_c:
            self._copy_selection()

        elif ctrl and key == pygame.K_x:
            self._copy_selection()
            self._delete_selection()

        elif ctrl and key == pygame.K_v:
            clip = _clipboard_get()
            self._delete_selection()
            for ch in clip:
                if ch == "\n":
                    tail = lines[self._row][self._col:]
                    lines[self._row] = lines[self._row][:self._col]
                    lines.insert(self._row + 1, list(tail))
                    self._row += 1
                    self._col  = 0
                else:
                    lines[self._row].insert(self._col, ch)
                    self._col += 1
            self._notify_change()

        else:
            char = event.unicode
            if char and char.isprintable():
                self._delete_selection()
                lines[self._row].insert(self._col, char)
                self._col += 1
                self._notify_change()

        self._ensure_cursor_visible()
        self.mark_dirty()

    def _notify_change(self) -> None:
        if self._on_change:
            self._on_change(self.value)
        self._fire(32)

    def _copy_selection(self) -> None:
        text = self._get_selection_text()
        if text:
            _clipboard_set(text)

    def _get_selection_text(self) -> str:
        if self._sel_r is None:
            return ""
        r0, c0 = sorted([(self._sel_r, self._sel_c),
                          (self._row,  self._col)])[0]
        r1, c1 = sorted([(self._sel_r, self._sel_c),
                          (self._row,  self._col)])[1]
        if r0 == r1:
            return "".join(self._lines[r0][c0:c1])
        result = ["".join(self._lines[r0][c0:])]
        for r in range(r0 + 1, r1):
            result.append("".join(self._lines[r]))
        result.append("".join(self._lines[r1][:c1]))
        return "\n".join(result)

    def _delete_selection(self) -> None:
        if self._sel_r is None:
            return
        (r0, c0), (r1, c1) = sorted(
            [(self._sel_r, self._sel_c), (self._row, self._col)])
        if r0 == r1:
            self._lines[r0] = self._lines[r0][:c0] + self._lines[r0][c1:]
        else:
            head = self._lines[r0][:c0]
            tail = self._lines[r1][c1:]
            head.extend(tail)
            self._lines[r0] = head
            del self._lines[r0 + 1 : r1 + 1]
        self._row, self._col = r0, c0
        self._sel_r = None

    # ── render ────────────────────────────────────────────────────────────────

    def render_self(self) -> None:
        if self.texture is None:
            return

        w, h = self.rect.width, self.rect.height
        if self.texture.get_size() != (w, h):
            self.texture = pygame.Surface((w, h), pygame.SRCALPHA)

        self._style.fill_surface(self.texture)

        # gutter background
        if self.line_numbers and self._gutter_w:
            gutter_col = (37, 37, 38, 255)
            pygame.draw.rect(self.texture, gutter_col,
                             (0, 0, self._gutter_w, h))
            pygame.draw.line(self.texture, (60, 60, 65),
                             (self._gutter_w, 0), (self._gutter_w, h), 1)

        vis   = self._visible_lines()
        lh    = self._lh
        gw    = self._gutter_w

        # cursor blink
        now = time.perf_counter()
        if now - self._blink_t >= self._BLINK_RATE:
            self._blink_on = not self._blink_on
            self._blink_t  = now

        sel_color = (38, 79, 120, 180)

        for i in range(vis):
            li = self._scroll_y + i
            if li >= len(self._lines):
                break
            y_pos = 2 + i * lh

            # line number
            if self.line_numbers:
                is_cur = (li == self._row)
                ln_col = (180, 180, 180) if is_cur else (100, 100, 110)
                ln_surf = self._font.render(str(li + 1), ln_col)
                if ln_surf:
                    lnx = gw - ln_surf.get_width() - 6
                    self.texture.blit(ln_surf, (max(0, lnx), y_pos))

            line_str = "".join(self._lines[li])
            x_pos    = gw + 4 - self._scroll_x

            # selection highlight
            if self._sel_r is not None:
                (r0, c0), (r1, c1) = sorted(
                    [(self._sel_r, self._sel_c), (self._row, self._col)])
                if r0 <= li <= r1:
                    sc = c0 if li == r0 else 0
                    ec = c1 if li == r1 else len(line_str)
                    sx, _ = self._font.size(line_str[:sc])
                    ex, _ = self._font.size(line_str[:ec])
                    sel_r = pygame.Rect(gw + 4 + sx - self._scroll_x,
                                        y_pos, ex - sx, lh)
                    pygame.draw.rect(self.texture, sel_color, sel_r)

            # current line highlight
            if li == self._row:
                hl = pygame.Surface((w - gw, lh), pygame.SRCALPHA)
                hl.fill((255, 255, 255, 10))
                self.texture.blit(hl, (gw, y_pos))

            # text
            txt_surf = self._font.render(line_str, self._style.color)
            if txt_surf:
                self.texture.blit(txt_surf, (x_pos, y_pos))

        # cursor
        if self.is_focus and self._blink_on:
            row_vis = self._row - self._scroll_y
            if 0 <= row_vis < vis:
                line_str = "".join(self._lines[self._row])
                cx, _ = self._font.size(line_str[:self._col])
                cx = gw + 4 + cx - self._scroll_x
                cy = 2 + row_vis * lh
                pygame.draw.line(self.texture, (200, 200, 210),
                                 (cx, cy), (cx, cy + lh - 2), 1)

        self._style.draw_border(self.texture)
        self.clear_dirty()
