from __future__ import annotations

from pathlib import Path
from typing import Any

import pygame
from pygame import freetype

try:
    from PycePlus.CORE.tools import network
except Exception:
    network = None

from PycePlus.UI.tools.color import Color, colorType

FontLike = str | Path | list[str] | None


class Font:
    """Thin font wrapper compatible with the original API."""

    def __init__(
        self,
        family: FontLike = None,
        size: int = 16,
        antialias: bool = True,
        freetype: bool = True,
    ):
        self.family = family
        self.size_px = int(size)
        self.antialias = antialias
        self.use_freetype = bool(freetype)
        self._font = self._load_font(family, self.size_px, self.use_freetype)

    def _load_font(self, family: FontLike, size: int, use_freetype: bool):
        path = None
        if isinstance(family, (str, Path)) and str(family):
            p = Path(str(family))
            if p.exists():
                path = str(p)
        elif isinstance(family, (list, tuple)) and family:
            for item in family:
                p = Path(str(item))
                if p.exists():
                    path = str(p)
                    break

        if use_freetype:
            try:
                if path:
                    return freetype.Font(path, size)
                if family and not isinstance(family, (list, tuple)):
                    return freetype.SysFont(str(family), size)
                return freetype.SysFont(None, size)
            except Exception:
                pass

        try:
            if path:
                return pygame.font.Font(path, size)
            if family and not isinstance(family, (list, tuple)):
                return pygame.font.SysFont(str(family), size)
            return pygame.font.SysFont(None, size)
        except Exception:
            return pygame.font.Font(None, size)

    def resize(self, size: int) -> "Font":
        self.size_px = int(size)
        self._font = self._load_font(self.family, self.size_px, self.use_freetype)
        return self

    def render(self, text: str, color: colorType = (255, 255, 255)) -> pygame.Surface | None:
        c = Color.makefrom(color).tuple_RGB()
        try:
            if isinstance(self._font, freetype.Font):
                surf, _ = self._font.render(text, fgcolor=c, bgcolor=None)
                return surf
            return self._font.render(text, self.antialias, c)
        except Exception:
            return None

    def size(self, text: str) -> tuple[int, int]:
        try:
            return self._font.get_rect(text).size if isinstance(self._font, freetype.Font) else self._font.size(text)
        except Exception:
            return (0, 0)

    def get_height(self) -> int:
        try:
            return self._font.get_sized_height() if isinstance(self._font, freetype.Font) else self._font.get_height()
        except Exception:
            return self.size_px

    def get_ascent(self) -> int:
        try:
            return self._font.get_sized_ascender() if isinstance(self._font, freetype.Font) else self._font.get_ascent()
        except Exception:
            return self.size_px

    def get_descent(self) -> int:
        try:
            return self._font.get_sized_descender() if isinstance(self._font, freetype.Font) else self._font.get_descent()
        except Exception:
            return 0


def get_font(path: str | Path | list[str]) -> Path:
    if isinstance(path, (list, tuple)):
        for item in path:
            try:
                return get_font(item)
            except Exception:
                continue
        raise FileNotFoundError("No font found in list")

    path = Path(str(path))
    if path.exists():
        return path

    if network and str(path).startswith(("http://", "https://")):
        result = network.download(str(path))
        if hasattr(result, "get"):
            result = result.get(True)
        data = getattr(result, "data", None)
        if data:
            folder = Path(__file__).resolve().parent.parent.parent / "data" / "fonts"
            folder.mkdir(parents=True, exist_ok=True)
            out = folder / (path.stem or "font.ttf")
            out.write_bytes(data)
            return out

    raise FileNotFoundError(str(path))
