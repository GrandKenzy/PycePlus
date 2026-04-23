from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pygame

from PycePlus.GUI.base import Base
from PycePlus.UI.window import Window


class OpenGLCanvas(Base):
    """A widget that reserves a region for OpenGL rendering callbacks."""

    def __init__(
        self,
        father=None,
        width: int = 300,
        height: int = 200,
        x: int = 0,
        y: int = 0,
        on_setup: Callable[["OpenGLCanvas"], Any] | None = None,
        on_draw: Callable[["OpenGLCanvas"], Any] | None = None,
        style: dict | None = None,
        name: str | None = None,
        page: str | None = None,
        visible: bool = True,
    ):
        _style = {
            "background_color": (12, 12, 14, 255),
            "border": 1,
            "border_color": (70, 70, 90, 255),
            "border_radius": 8,
            "cursor": "arrow",
            **(style or {}),
        }
        super().__init__(father, name, page, style=_style)
        self.rect = pygame.Rect(x, y, width, height)
        self.texture = pygame.Surface((width, height), pygame.SRCALPHA)
        self.visible = visible
        self.on_setup = on_setup
        self.on_draw = on_draw
        self._setup_done = False

    def set_callbacks(
        self,
        on_setup: Callable[["OpenGLCanvas"], Any] | None = None,
        on_draw: Callable[["OpenGLCanvas"], Any] | None = None,
    ) -> "OpenGLCanvas":
        self.on_setup = on_setup
        self.on_draw = on_draw
        self.mark_dirty()
        return self

    def render_self(self) -> None:
        if self.texture is None:
            self.texture = pygame.Surface((self.rect.width, self.rect.height), pygame.SRCALPHA)

        if Window.is_opengl():
            if not self._setup_done and callable(self.on_setup):
                try:
                    self.on_setup(self)
                finally:
                    self._setup_done = True
            if callable(self.on_draw):
                self.on_draw(self)
            else:
                self.style.fill_surface(self.texture)
                self.style.draw_border(self.texture)
        else:
            self.style.fill_surface(self.texture)
            label = pygame.font.Font(None, 16).render("OpenGL canvas requires OPENGL mode", True, (220, 220, 220))
            self.texture.blit(label, (12, 12))
            self.style.draw_border(self.texture)
        self.clear_dirty()
