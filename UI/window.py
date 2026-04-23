from __future__ import annotations

from pathlib import Path
from typing import Any

import pygame

_WINDOW: pygame.Surface | None = None
_INITINF = pygame.display.Info()
_COLOR = (0, 0, 0)
_CONFIGURATION: dict[str, Any] = {
    "flags": 0,
    "vsync": False,
    "display": 0,
    "depth": 32,
    "opengl": False,
}
_ICON: pygame.Surface | None = None

CENTER = -1


def _resolve_center(value: int, fallback: int) -> int:
    return fallback if value == CENTER else value


def _load_icon(icon: pygame.Surface | str | Path) -> pygame.Surface:
    if isinstance(icon, pygame.Surface):
        return icon
    return pygame.image.load(str(icon)).convert_alpha()


def new(
    title: str,
    width: int = _INITINF.current_w - 200,
    height: int = _INITINF.current_h - 200,
    x: int = CENTER,
    y: int = CENTER,

    fulls_screen: bool = False,
    resizable: bool = False,
    noframe: bool = False,
    doublebuffer: bool = False,
    opengl: bool = False,

    icon: pygame.Surface | str | None = None,
    background_color: tuple[int, int, int] = (0, 0, 0),
    vsync: bool = False,
    display: int = 0,
    depth: int = 32,
):
    global _WINDOW, _COLOR, _ICON

    flags = 0
    if fulls_screen:
        flags |= pygame.FULLSCREEN
    if resizable:
        flags |= pygame.RESIZABLE
    if noframe:
        flags |= pygame.NOFRAME
    if doublebuffer:
        flags |= pygame.DOUBLEBUF
    if opengl:
        flags |= pygame.OPENGL
        if doublebuffer:
            flags |= pygame.DOUBLEBUF

    _WINDOW = pygame.display.set_mode((width, height), flags, depth, display, vsync)
    pygame.display.set_caption(title)

    if icon:
        try:
            _ICON = _load_icon(icon)
            pygame.display.set_icon(_ICON)
        except Exception:
            _ICON = None

    _COLOR = background_color

    try:
        cx, cy = pygame.display.get_window_position()
    except Exception:
        cx = cy = 0
    x = _resolve_center(x, cx)
    y = _resolve_center(y, cy)
    try:
        pygame.display.set_window_position((x, y))
    except Exception:
        pass

    _CONFIGURATION.update({
        "flags": flags,
        "vsync": vsync,
        "display": display,
        "depth": depth,
        "opengl": opengl,
    })
    try:
        from PycePlus.UI import Application
        Application.opengl_enabled = opengl
    except Exception:
        pass
    return Window()


class Window:
    abs_x = 0
    abs_y = 0
    abs_pos = (0, 0)

    @staticmethod
    def get_window():
        return _WINDOW

    @staticmethod
    def is_open():
        return _WINDOW is not None

    @staticmethod
    def is_opengl():
        return bool(_CONFIGURATION.get("opengl"))

    @staticmethod
    def blit(surface: pygame.Surface, pos: tuple[int, int] = (0, 0)):
        if _WINDOW is not None and not _CONFIGURATION.get("opengl"):
            _WINDOW.blit(surface, pos)

    @staticmethod
    def clear():
        if _WINDOW is not None and _COLOR is not None and not _CONFIGURATION.get("opengl"):
            _WINDOW.fill(_COLOR)

    @staticmethod
    def blits(sequence: list[tuple[pygame.Surface, tuple[int, int]]]):
        if _WINDOW is not None and not _CONFIGURATION.get("opengl"):
            _WINDOW.blits(sequence)

    @staticmethod
    def title(title: str | None):
        if title:
            pygame.display.set_caption(title)
        return pygame.display.get_caption()[0]

    @staticmethod
    def set_icon(icon: str | pygame.Surface):
        global _ICON
        _ICON = _load_icon(icon)
        pygame.display.set_icon(_ICON)

    @staticmethod
    def screensize():
        return _INITINF.current_w, _INITINF.current_h

    @staticmethod
    def window_size():
        return _WINDOW.get_size() if _WINDOW else (0, 0)

    @staticmethod
    def position(x: int | None = None, y: int | None = None):
        try:
            cx, cy = pygame.display.get_window_position()
            x = cx if x is None else x
            y = cy if y is None else y
            pygame.display.set_window_position((x, y))
        except Exception:
            pass

    @staticmethod
    def get_position():
        try:
            return pygame.display.get_window_position()
        except Exception:
            return (0, 0)

    @staticmethod
    def reopen(
        title: str | None = None,
        width: int | None = None,
        height: int | None = None,
        x: int | None = None,
        y: int | None = None,

        fulls_screen: bool | None = None,
        resizable: bool | None = None,
        noframe: bool | None = None,
        doublebuffer: bool | None = None,
        opengl: bool | None = None,

        icon: pygame.Surface | str | None = None,
        background_color: tuple[int, int, int] | None = None,
        vsync: bool | None = None,
        display: int | None = None,
        depth: int | None = None,
    ):
        title = title or pygame.display.get_caption()[0]
        if _WINDOW is None:
            w, h = (width or 1280, height or 720)
        else:
            w, h = (width or _WINDOW.get_width(), height or _WINDOW.get_height())
        cx, cy = (0, 0)
        try:
            cx, cy = pygame.display.get_window_position()
        except Exception:
            pass
        x = cx if x is None else x
        y = cy if y is None else y

        if fulls_screen is None:
            fulls_screen = bool(_CONFIGURATION["flags"] & pygame.FULLSCREEN)
        if resizable is None:
            resizable = bool(_CONFIGURATION["flags"] & pygame.RESIZABLE)
        if noframe is None:
            noframe = bool(_CONFIGURATION["flags"] & pygame.NOFRAME)
        if doublebuffer is None:
            doublebuffer = bool(_CONFIGURATION["flags"] & pygame.DOUBLEBUF)
        if opengl is None:
            opengl = bool(_CONFIGURATION.get("opengl"))
        if icon is None:
            icon = _ICON
        if background_color is None:
            background_color = _COLOR
        if vsync is None:
            vsync = bool(_CONFIGURATION["vsync"])
        if display is None:
            display = int(_CONFIGURATION["display"])
        if depth is None:
            depth = int(_CONFIGURATION["depth"])

        return new(
            title=title,
            width=w,
            height=h,
            x=x,
            y=y,
            fulls_screen=fulls_screen,
            resizable=resizable,
            noframe=noframe,
            doublebuffer=doublebuffer,
            opengl=opengl,
            icon=icon,
            background_color=background_color,
            vsync=vsync,
            display=display,
            depth=depth,
        )
