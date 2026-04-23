from __future__ import annotations

import sys
from pathlib import Path

import pygame

from PycePlus.UI import window


class Application:
    state = "busy"
    files: list[dict[str, str]] = []
    MEMORY_LOW_FACTOR = 0.2
    DISK_LOW_FACTOR = 0.1
    is_online = False
    connection_lost = False
    FPS: int = 60
    REFRESH: bool = True
    root: str = str(Path(__file__).resolve().parent.parent)
    opengl_enabled: bool = False
    tasker = None
    server = None
    client = None


def exit():
    pygame.quit()
    raise SystemExit(0)
