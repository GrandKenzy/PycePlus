"""
PycePlus.GUI.widgets.extras
===========================
Widgets adicionales modernos:

  - Slider       → barra deslizante (horizontal/vertical)
  - Tooltip      → globo de ayuda emergente
  - RadioGroup   → grupo de botones de opción mutuamente excluyentes
  - RadioButton  → botón de opción individual (usa RadioGroup)
  - DropFile     → zona de arrastrar-y-soltar archivos
  - GraphicsV1   → gráfica matplotlib renderizada en pygame

Todos soportan:
  - nombre (name=)
  - estilo CSS (style=)
  - eventos PycePlus
  - dirty-flag rendering

Dependencias opcionales:
  - matplotlib (GraphicsV1)
"""
from __future__ import annotations

import threading
import time
from typing import Callable, Literal, Sequence

import pygame

from PycePlus.GUI.base import Base
from PycePlus.GUI.interface_man.style import compile_style
from PycePlus.UI.tools.color import Color, colorType
from PycePlus.UI.tools.font import Font
 
__all__ = [
    "Slider",
    "Tooltip",
    "RadioGroup",
    "RadioButton",
    "DropFile",
    "GraphicsV1",
]

# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


# ══════════════════════════════════════════════════════════════════════════════
#  Slider
# ══════════════════════════════════════════════════════════════════════════════

class Slider(Base):
    """
    Barra deslizante moderna con soporte horizontal y vertical.

    Parameters
    ----------
    min_val     : valor mínimo
    max_val     : valor máximo
    value       : valor inicial
    step        : paso (0 = continuo)
    orientation : "horizontal" | "vertical"
    show_value  : mostrar valor junto al thumb
    on_change   : Callable[[float], None]
    """

    def __init__(
        self,
        father=None,
        min_val:     float = 0.0,
        max_val:     float = 100.0,
        value:       float = 50.0,
        step:        float = 0.0,
        orientation: Literal["horizontal", "vertical"] = "horizontal",
        width:       int = 200,
        height:      int = 28,
        style:       dict | None = None,
        track_color: colorType = (60, 60, 70, 255),
        fill_color:  colorType = (86, 156, 214, 255),
        thumb_color: colorType = (200, 200, 210, 255),
        show_value:  bool = True,
        font:        Font | None = None,
        on_change:   Callable | None = None,
        x: int = 0,
        y: int = 0,
        name: str | None = None,
        page: str | None = None,
        visible: bool = True,
    ):
        _default = {
            "background_color": (0, 0, 0, 0),
            "cursor": "hand",
        }
        _style = {**_default, **(style or {})}
        _style.setdefault("x", x)
        _style.setdefault("y", y)
        _style.setdefault("width", width)
        _style.setdefault("height", height)

        super().__init__(father, name, page, style=_style)

        self.min_val = float(min_val)
        self.max_val = float(max_val)
        self._value  = _clamp(float(value), self.min_val, self.max_val)
        self.step    = float(step)
        self.orientation = orientation
        self.show_value = show_value
        self.track_color  = Color.makefrom(track_color)
        self.fill_color   = Color.makefrom(fill_color)
        self.thumb_color  = Color.makefrom(thumb_color)
        self._on_change   = on_change
        self._font = font or Font(None, 11)
        self.visible = visible
        self._dragging_thumb = False

        self.rect = pygame.Rect(x, y, width, height)
        self.texture = pygame.Surface((width, height), pygame.SRCALPHA)

        self.bind("mouse.button.left.click",   self._on_click)
        self.bind("mouse.drag.start",          self._on_drag_start)
        self.bind("mouse.drag.move",           self._on_drag_move)
        self.bind("mouse.drag.end",            self._on_drag_end)
        self.bind("mouse.scroll.up",           lambda w, _: self._step_value(1))
        self.bind("mouse.scroll.down",         lambda w, _: self._step_value(-1))
        self.mark_dirty()

    # ── value ──────────────────────────────────────────────────────────────

    @property
    def value(self) -> float:
        return self._value

    @value.setter
    def value(self, v: float) -> None:
        new = self._snap(_clamp(float(v), self.min_val, self.max_val))
        if new != self._value:
            self._value = new
            if self._on_change:
                self._on_change(self._value)
            self._fire(32)
            self.mark_dirty()

    def _snap(self, v: float) -> float:
        if self.step > 0:
            steps = round((v - self.min_val) / self.step)
            return self.min_val + steps * self.step
        return v

    def _step_value(self, direction: int) -> None:
        s = self.step if self.step > 0 else (self.max_val - self.min_val) / 20
        self.value = self._value + direction * s

    def _value_from_pos(self, px_: int, py_: int) -> float:
        if self.orientation == "horizontal":
            t = 18  # thumb radius
            track_start = t
            track_end   = self.rect.width - t
            span = max(1, track_end - track_start)
            ratio = _clamp((px_ - track_start) / span, 0, 1)
        else:
            t = 18
            track_start = t
            track_end   = self.rect.height - t
            span = max(1, track_end - track_start)
            ratio = _clamp((py_ - track_start) / span, 0, 1)
            ratio = 1 - ratio  # invertir: arriba = max

        return self.min_val + ratio * (self.max_val - self.min_val)

    def _on_click(self, w, pos) -> None:
        self.value = self._value_from_pos(*pos)

    def _on_drag_start(self, w, pos) -> None:
        self._dragging_thumb = True

    def _on_drag_move(self, w, pos) -> None:
        if self._dragging_thumb:
            self.value = self._value_from_pos(*pos)

    def _on_drag_end(self, w, pos) -> None:
        self._dragging_thumb = False

    # ── render ────────────────────────────────────────────────────────────

    def render_self(self) -> None:
        if not self._dirty or self.texture is None:
            return

        w, h = self.rect.width, self.rect.height
        if self.texture.get_size() != (w, h):
            self.texture = pygame.Surface((w, h), pygame.SRCALPHA)

        self._style.fill_surface(self.texture)

        ratio = (_clamp(self._value, self.min_val, self.max_val) - self.min_val) / max(1e-9, self.max_val - self.min_val)

        if self.orientation == "horizontal":
            cy = h // 2
            track_h = 4
            ty = cy - track_h // 2
            thumb_r = min(h // 2 - 2, 9)
            t = thumb_r + 2
            track_w = w - t * 2
            track_x = t

            # track background
            pygame.draw.rect(self.texture, self.track_color,
                             (track_x, ty, track_w, track_h), border_radius=2)
            # track fill
            fill_w = int(track_w * ratio)
            if fill_w > 0:
                pygame.draw.rect(self.texture, self.fill_color,
                                 (track_x, ty, fill_w, track_h), border_radius=2)
            # thumb
            thumb_x = track_x + int(track_w * ratio)
            pygame.draw.circle(self.texture, self.thumb_color, (thumb_x, cy), thumb_r)
            pygame.draw.circle(self.texture, self.fill_color,  (thumb_x, cy), thumb_r, 2)

            # value label
            if self.show_value:
                label = f"{self._value:.1f}" if self.step == 0 else str(int(self._value))
                surf = self._font.render(label, self._style.color)
                if surf:
                    lx = thumb_x - surf.get_width() // 2
                    ly = 1
                    self.texture.blit(surf, (lx, ly))

        else:  # vertical
            cx = w // 2
            track_w = 4
            tx = cx - track_w // 2
            thumb_r = min(w // 2 - 2, 9)
            t = thumb_r + 2
            track_h = h - t * 2
            track_y = t

            pygame.draw.rect(self.texture, self.track_color,
                             (tx, track_y, track_w, track_h), border_radius=2)
            fill_h = int(track_h * ratio)
            if fill_h > 0:
                pygame.draw.rect(self.texture, self.fill_color,
                                 (tx, track_y + track_h - fill_h, track_w, fill_h), border_radius=2)
            thumb_y = track_y + int(track_h * (1 - ratio))
            pygame.draw.circle(self.texture, self.thumb_color, (cx, thumb_y), thumb_r)
            pygame.draw.circle(self.texture, self.fill_color,  (cx, thumb_y), thumb_r, 2)

        self.clear_dirty()


# ══════════════════════════════════════════════════════════════════════════════
#  Tooltip
# ══════════════════════════════════════════════════════════════════════════════

class Tooltip(Base):
    """
    Globo de ayuda emergente que se muestra al hacer hover sobre un widget.

    Uso:
        tip = Tooltip(win, text="Haz clic para guardar", target=btn_save)

    Parameters
    ----------
    text    : texto del tooltip
    target  : widget que lo activa (opcional)
    delay   : segundos de hover antes de mostrarse
    """

    def __init__(
        self,
        father=None,
        text:   str = "",
        target: Base | None = None,
        delay:  float = 0.6,
        style:  dict | None = None,
        font:   Font | None = None,
        x: int = 0,
        y: int = 0,
        name: str | None = None,
        page: str | None = None,
    ):
        _default = {
            "background_color": (42, 42, 52, 245),
            "color":            (220, 220, 220, 255),
            "border":           1,
            "border_color":     (80, 80, 100, 200),
            "border_radius":    5,
            "padding_left":     10,
            "padding_right":    10,
            "padding_top":      5,
            "padding_bottom":   5,
            "font_size":        12,
        }
        _style = {**_default, **(style or {})}
        _style.setdefault("x", x)
        _style.setdefault("y", y)
        _style.setdefault("width", 10)
        _style.setdefault("height", 10)

        super().__init__(father, name, page, style=_style)

        self._text  = str(text)
        self._delay = float(delay)
        self._font  = font or Font(None, self._style.font_size)
        self.visible = False
        self._hover_start: float | None = None
        self._mouse_pos: tuple[int, int] = (0, 0)

        self._measure_and_create()

        if target is not None:
            target.bind("mouse.hover",   self._on_target_hover)
            target.bind("mouse.hovering",self._on_target_hovering)
            target.bind("mouse.leave",   self._on_target_leave)

    def _measure_and_create(self) -> None:
        tw, th = self._font.size(self._text) if self._text else (0, 0)
        pl, pr = self._style.pad_left, self._style.pad_right
        pt, pb = self._style.pad_top,  self._style.pad_bottom
        w = max(1, tw + pl + pr)
        h = max(1, th + pt + pb)
        self.rect.width  = w
        self.rect.height = h
        self.texture = pygame.Surface((w, h), pygame.SRCALPHA)
        self.mark_dirty()

    @property
    def text(self) -> str:
        return self._text

    @text.setter
    def text(self, v: str) -> None:
        self._text = str(v)
        self._measure_and_create()

    def show_at(self, x: int, y: int) -> None:
        self.rect.x  = x
        self.rect.y  = y
        self.visible = True
        self.mark_dirty()

    def hide(self) -> None:
        self.visible = False
        self._hover_start = None

    def _on_target_hover(self, w, pos) -> None:
        self._hover_start = time.perf_counter()
        self._mouse_pos   = pos

    def _on_target_hovering(self, w, pos) -> None:
        self._mouse_pos = pos
        if self._hover_start and not self.visible:
            if time.perf_counter() - self._hover_start >= self._delay:
                mx, my = self._mouse_pos
                self.show_at(mx + 14, my - self.rect.height - 4)

    def _on_target_leave(self, w, pos=None) -> None:
        self.hide()

    def render_self(self) -> None:
        if not self._dirty or self.texture is None:
            return

        self._style.fill_surface(self.texture)
        txt_surf = self._font.render(self._text, self._style.color)
        if txt_surf:
            self.texture.blit(txt_surf, (self._style.pad_left, self._style.pad_top))
        self._style.draw_border(self.texture)
        self.clear_dirty()


# ══════════════════════════════════════════════════════════════════════════════
#  RadioGroup + RadioButton
# ══════════════════════════════════════════════════════════════════════════════

class RadioGroup:
    """
    Manejador de un grupo de RadioButtons mutuamente excluyentes.

    Uso:
        group = RadioGroup(on_change=lambda v: print(v))
        r1 = RadioButton(win, "Opción A", group=group, value="a")
        r2 = RadioButton(win, "Opción B", group=group, value="b")
        r3 = RadioButton(win, "Opción C", group=group, value="c", selected=True)
    """

    def __init__(self, on_change: Callable | None = None):
        self._buttons: list["RadioButton"] = []
        self._on_change = on_change
        self._selected: "RadioButton | None" = None

    def _register(self, btn: "RadioButton") -> None:
        self._buttons.append(btn)

    def _select(self, btn: "RadioButton") -> None:
        if self._selected is btn:
            return
        if self._selected:
            self._selected._set_selected(False)
        self._selected = btn
        btn._set_selected(True)
        if self._on_change:
            self._on_change(btn.value)

    @property
    def selected_value(self) -> object:
        return self._selected.value if self._selected else None

    @property
    def selected(self) -> "RadioButton | None":
        return self._selected


class RadioButton(Base):
    """
    Botón de opción circular. Usar dentro de un RadioGroup.

    Parameters
    ----------
    text     : etiqueta visible
    group    : RadioGroup al que pertenece
    value    : valor a devolver cuando se selecciona
    selected : True si debe estar seleccionado al inicio
    """

    def __init__(
        self,
        father=None,
        text:     str = "",
        group:    RadioGroup | None = None,
        value:    object = None,
        selected: bool = False,
        style:    dict | None = None,
        font:     Font | None = None,
        dot_color:  colorType = (86, 156, 214, 255),
        x: int = 0,
        y: int = 0,
        name: str | None = None,
        page: str | None = None,
        visible: bool = True,
    ):
        _default = {
            "background_color": (0, 0, 0, 0),
            "color":            (220, 220, 220, 255),
            "font_size":        14,
            "cursor":           "hand",
        }
        _style = {**_default, **(style or {})}
        _style.setdefault("x", x)
        _style.setdefault("y", y)

        super().__init__(father, name, page, style=_style)

        self._text      = str(text)
        self._group     = group
        self.value      = value if value is not None else text
        self._selected  = False
        self.dot_color  = Color.makefrom(dot_color)
        self._font      = font or Font(None, self._style.font_size)
        self.visible    = visible

        r = 10  # radio del círculo
        fw, fh = self._font.size(self._text) if self._text else (0, 0)
        w = r * 2 + 8 + fw + 4
        h = max(r * 2 + 4, fh + 4)
        self.rect.width  = max(1, w)
        self.rect.height = max(1, h)
        self.texture = pygame.Surface((self.rect.width, self.rect.height), pygame.SRCALPHA)

        if group:
            group._register(self)
            if selected:
                group._select(self)
        else:
            self._set_selected(selected)

        self.bind("mouse.button.left.click", self._on_click)
        self.mark_dirty()

    def _on_click(self, w, pos) -> None:
        if self._group:
            self._group._select(self)
        else:
            self._set_selected(True)

    def _set_selected(self, v: bool) -> None:
        self._selected = v
        self.mark_dirty()

    @property
    def is_selected(self) -> bool:
        return self._selected

    def render_self(self) -> None:
        if not self._dirty or self.texture is None:
            return

        w, h = self.rect.width, self.rect.height
        if self.texture.get_size() != (w, h):
            self.texture = pygame.Surface((w, h), pygame.SRCALPHA)

        self._style.fill_surface(self.texture)

        r  = 10
        cx = r + 2
        cy = h // 2

        # Outer circle
        ring_col = self.dot_color if self._selected else Color(100, 100, 120)
        pygame.draw.circle(self.texture, ring_col, (cx, cy), r, 2)

        # Inner dot when selected
        if self._selected:
            pygame.draw.circle(self.texture, self.dot_color, (cx, cy), r - 4)

        # Label
        if self._text:
            txt_surf = self._font.render(self._text, self._style.color)
            if txt_surf:
                tx = cx + r + 6
                ty = (h - txt_surf.get_height()) // 2
                self.texture.blit(txt_surf, (tx, ty))

        self._style.draw_border(self.texture)
        self.clear_dirty()


# ══════════════════════════════════════════════════════════════════════════════
#  DropFile
# ══════════════════════════════════════════════════════════════════════════════

class DropFile(Base):
    """
    Zona de arrastrar-y-soltar archivos.

    Cuando el usuario arrastra un archivo sobre la ventana y lo suelta
    sobre este widget, se dispara on_drop con la lista de rutas.

    Parameters
    ----------
    text         : texto mostrado en la zona (hint)
    accept       : lista de extensiones permitidas (".py", ".png")  []= todas
    multiple     : ¿aceptar múltiples archivos?
    on_drop      : Callable[[list[str]], None]
    on_drop_rejected : Callable[[list[str]], None]  — archivos rechazados
    """

    def __init__(
        self,
        father=None,
        text:    str = "Arrastra archivos aquí",
        accept:  list[str] | None = None,
        multiple: bool = True,
        width:   int = 300,
        height:  int = 140,
        style:   dict | None = None,
        font:    Font | None = None,
        on_drop: Callable | None = None,
        on_drop_rejected: Callable | None = None,
        x: int = 0,
        y: int = 0,
        name: str | None = None,
        page: str | None = None,
        visible: bool = True,
    ):
        _default = {
            "background_color": (28, 30, 38, 255),
            "color":            (150, 160, 180, 255),
            "border":           2,
            "border_color":     (70, 80, 100, 200),
            "border_radius":    12,
            "font_size":        14,
        }
        _style = {**_default, **(style or {})}
        _style.setdefault("x", x)
        _style.setdefault("y", y)
        _style.setdefault("width", width)
        _style.setdefault("height", height)

        super().__init__(father, name, page, style=_style)

        self._text            = str(text)
        self.accept           = [e.lower().lstrip(".") for e in (accept or [])]
        self.multiple         = multiple
        self._on_drop         = on_drop
        self._on_drop_rejected= on_drop_rejected
        self._font            = font or Font(None, self._style.font_size)
        self.visible          = visible
        self._highlight       = False   # activo durante drag-over
        self._last_files: list[str] = []

        self.rect    = pygame.Rect(x, y, width, height)
        self.texture = pygame.Surface((width, height), pygame.SRCALPHA)

        # El evento drop.file viene del sistema
        self.bind("drop.file", self._on_system_drop)
        self.mark_dirty()

    def _filter(self, paths: list[str]) -> tuple[list[str], list[str]]:
        if not self.accept:
            return paths, []
        import os
        ok, rejected = [], []
        for p in paths:
            ext = os.path.splitext(p)[1].lstrip(".").lower()
            (ok if ext in self.accept else rejected).append(p)
        return ok, rejected

    def _on_system_drop(self, w, data) -> None:
        # data puede ser str (un archivo) o list[str]
        import os
        if isinstance(data, str):
            paths = [data]
        elif isinstance(data, (list, tuple)):
            paths = list(data)
        else:
            return

        if not self.multiple:
            paths = paths[:1]

        ok, rejected = self._filter(paths)
        self._last_files = ok
        self._highlight  = False

        if ok and self._on_drop:
            self._on_drop(ok)
        if rejected and self._on_drop_rejected:
            self._on_drop_rejected(rejected)

        self.mark_dirty()

    def set_highlight(self, v: bool) -> None:
        self._highlight = v
        self.mark_dirty()

    def render_self(self) -> None:
        if not self._dirty or self.texture is None:
            return

        w, h = self.rect.width, self.rect.height
        if self.texture.get_size() != (w, h):
            self.texture = pygame.Surface((w, h), pygame.SRCALPHA)

        # Fondo resaltado durante hover de arrastre
        if self._highlight:
            hl_style = compile_style({
                **self._style.__class__.__dict__,
                "background_color": (40, 70, 110, 255),
                "border_color":     (86, 156, 214, 255),
            })
        else:
            hl_style = self._style

        self._style.fill_surface(self.texture)

        if self._highlight:
            # Overlay azulado
            ov = pygame.Surface((w, h), pygame.SRCALPHA)
            ov.fill((86, 156, 214, 30))
            pygame.draw.rect(ov, (86, 156, 214, 100), (0, 0, w, h),
                             width=2, border_radius=self._style.border_radius)
            self.texture.blit(ov, (0, 0))

        # Icono ↓ (flecha)
        icon_font = Font(None, 32)
        icon_surf = icon_font.render("⬇", (100, 130, 180))
        if icon_surf:
            ix = (w - icon_surf.get_width()) // 2
            iy = h // 2 - icon_surf.get_height() - 6
            self.texture.blit(icon_surf, (ix, iy))

        # Texto hint
        txt_surf = self._font.render(self._text, self._style.color)
        if txt_surf:
            tx = (w - txt_surf.get_width()) // 2
            ty = h // 2 + 4
            self.texture.blit(txt_surf, (tx, ty))

        # Archivos soltados
        if self._last_files:
            import os
            small = Font(None, 11)
            names = [os.path.basename(p) for p in self._last_files[:3]]
            if len(self._last_files) > 3:
                names.append(f"+{len(self._last_files)-3} más…")
            for i, fname in enumerate(names):
                fs = small.render(fname, (160, 200, 160))
                if fs:
                    fx = (w - fs.get_width()) // 2
                    fy = h - (len(names) - i) * 14 - 4
                    self.texture.blit(fs, (fx, fy))

        self._style.draw_border(self.texture)
        self.clear_dirty()


# ══════════════════════════════════════════════════════════════════════════════
#  GraphicsV1  —  matplotlib → pygame Surface
# ══════════════════════════════════════════════════════════════════════════════

class GraphicsV1(Base):
    """
    Widget que renderiza una figura de matplotlib directamente en pygame.

    Usa el backend "Agg" de matplotlib (sin ventana), convierte el buffer
    de píxeles a pygame.Surface y lo dibuja con dirty-rendering.

    Parameters
    ----------
    figure     : matplotlib.figure.Figure ya creada, o None para crear una.
    auto_fit   : re-renderizar si cambia el tamaño del widget
    on_setup   : Callable[[fig, ax], None]  — inicializa la figura
    on_update  : Callable[[fig, ax], None]  — puede actualizar datos

    Ejemplo:
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots()
        ax.plot([1,2,3], [4,2,6])

        g = GraphicsV1(window, figure=fig, width=480, height=320)

        # O usar callbacks:
        def setup(fig, ax):
            ax.bar(["A","B","C"], [3,7,2], color="#5699d4")
            ax.set_facecolor("#1e1e2e")
            fig.patch.set_facecolor("#1e1e2e")

        g = GraphicsV1(window, on_setup=setup, width=480, height=320)
    """

    def __init__(
        self,
        father=None,
        figure = None,
        width:  int = 480,
        height: int = 300,
        auto_fit: bool = True,
        style:    dict | None = None,
        on_setup:  Callable | None = None,
        on_update: Callable | None = None,
        x: int = 0,
        y: int = 0,
        name: str | None = None,
        page: str | None = None,
        visible: bool = True,
    ):
        _default = {
            "background_color": (20, 20, 28, 255),
            "border":           1,
            "border_color":     (60, 60, 80, 200),
            "border_radius":    6,
        }
        _style = {**_default, **(style or {})}
        _style.setdefault("x", x)
        _style.setdefault("y", y)
        _style.setdefault("width", width)
        _style.setdefault("height", height)

        super().__init__(father, name, page, style=_style)

        self.auto_fit  = auto_fit
        self._on_setup  = on_setup
        self._on_update = on_update
        self.visible   = visible
        self._plot_surf: pygame.Surface | None = None
        self._fig  = None
        self._ax   = None
        self._lock = threading.RLock()

        self.rect    = pygame.Rect(x, y, width, height)
        self.texture = pygame.Surface((width, height), pygame.SRCALPHA)

        self._init_matplotlib(figure, width, height)
        self.mark_dirty()

    def _init_matplotlib(self, figure, w: int, h: int) -> None:
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt

            dpi = 96
            fw  = w / dpi
            fh  = h / dpi

            if figure is not None:
                self._fig = figure
                axes = figure.get_axes()
                self._ax  = axes[0] if axes else figure.add_subplot(111)
            else:
                self._fig, self._ax = plt.subplots(figsize=(fw, fh), dpi=dpi)
                # Default dark theme
                self._fig.patch.set_facecolor("#1e1e1e")
                self._ax.set_facecolor("#252535")
                self._ax.tick_params(colors="#aaaaaa")
                for spine in self._ax.spines.values():
                    spine.set_edgecolor("#555555")

            if self._on_setup:
                self._on_setup(self._fig, self._ax)

            self._render_plot()
        except ImportError:
            self._plot_surf = self._make_placeholder("matplotlib no instalado")

    def _render_plot(self) -> None:
        """Renderiza la figura a una Surface de pygame (en hilo actual)."""
        try:
            import matplotlib.backends.backend_agg as backend_agg
            import numpy as np

            fig = self._fig
            w, h = self.rect.width, self.rect.height

            if self.auto_fit:
                dpi = fig.get_dpi()
                fig.set_size_inches(w / dpi, h / dpi)

            canvas = backend_agg.FigureCanvasAgg(fig)
            canvas.draw()
            buf = canvas.buffer_rgba()
            arr = np.frombuffer(buf, dtype=np.uint8)
            cw, ch = canvas.get_width_height()
            arr = arr.reshape((ch, cw, 4))
            # pygame usa (x, y, canal) pero surfarray espera (width, height, channels)
            arr_t = arr.swapaxes(0, 1)  # → (cw, ch, 4)
            surf  = pygame.Surface((cw, ch), pygame.SRCALPHA)
            pygame.surfarray.blit_array(surf, arr_t[:, :, :3])
            # Alpha
            alpha_arr = pygame.surfarray.pixels_alpha(surf)
            alpha_arr[:] = arr_t[:, :, 3]
            del alpha_arr

            with self._lock:
                if (cw, ch) != (w, h):
                    self._plot_surf = pygame.transform.smoothscale(surf, (w, h))
                else:
                    self._plot_surf = surf
        except Exception as exc:
            self._plot_surf = self._make_placeholder(f"Error: {exc}")

    def _make_placeholder(self, msg: str) -> pygame.Surface:
        w, h = self.rect.width, self.rect.height
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        surf.fill((25, 25, 35, 255))
        try:
            font = pygame.font.Font(None, 18)
            txt  = font.render(msg, True, (180, 80, 80))
            surf.blit(txt, ((w - txt.get_width()) // 2, (h - txt.get_height()) // 2))
        except Exception:
            pass
        return surf

    def update_plot(self) -> None:
        """
        Llama a on_update (si existe) y vuelve a renderizar la figura.
        Puede llamarse en cualquier hilo — usa lock interno.
        """
        if self._on_update and self._fig and self._ax:
            self._on_update(self._fig, self._ax)
        self._render_plot()
        self.mark_dirty()

    def set_figure(self, fig) -> None:
        """Reemplaza la figura completa."""
        self._fig = fig
        axes = fig.get_axes()
        self._ax = axes[0] if axes else None
        self._render_plot()
        self.mark_dirty()

    @property
    def figure(self):
        return self._fig

    @property
    def axes(self):
        return self._ax

    def render_self(self) -> None:
        if not self._dirty or self.texture is None:
            return

        w, h = self.rect.width, self.rect.height
        if self.texture.get_size() != (w, h):
            self.texture = pygame.Surface((w, h), pygame.SRCALPHA)
            if self.auto_fit:
                self._render_plot()

        self._style.fill_surface(self.texture)

        with self._lock:
            ps = self._plot_surf

        if ps:
            pw, ph = ps.get_size()
            bx = (w - pw) // 2
            by = (h - ph) // 2
            self.texture.blit(ps, (bx, by))

        self._style.draw_border(self.texture)
        self.clear_dirty()