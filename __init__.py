"""
PycePlus — Pygame-based UI framework with dirty rendering, CSS styles,
professional widgets, layout engines, and a thread-safe event bus.
"""
import pygame
import os

pygame.init()

from PycePlus.CORE.main import mainloop
from PycePlus.UI import Application, exit
Application.root = os.path.dirname(os.path.abspath(__file__))

# ── Window ───────────────────────────────────────────────────────────────────
from PycePlus.UI import *
from PycePlus.UI.tools.color import Color
from PycePlus.UI.tools.font  import Font

# ── GUI ──────────────────────────────────────────────────────────────────────
from PycePlus.GUI import (
    Base, Padding, Outline,
    Frame, FlexFrame, GridFrame, FlowFrame, FreeFrame,
    Button, Label, Checkbox, Image,
    TextInput, TextBox, VideoPlayer,
    Tree,
)
from PycePlus.GUI.interface_man.style import compile_style, CompiledStyle, StyleCache

# ── Events ───────────────────────────────────────────────────────────────────
from PycePlus.CORE.events import (
    register_button, register_custom_event, register_key,
)
from PycePlus import __events__ as events
from PycePlus.__events__ import (
    emit, register_event, unregister_event, clear_block,
)
from PycePlus.CORE.timec import Time
from PycePlus.CORE.tools import asynchronous
from PycePlus.CORE.tools import network

__version__ = "2.0.0"

__all__ = [
    # window
    "Color", "Font",
    # layout
    "Frame", "FlexFrame", "GridFrame", "FlowFrame", "FreeFrame",
    # widgets
    "Base", "Button", "Label", "Checkbox", "Image",
    "TextInput", "TextBox", "VideoPlayer",
    # events
    "emit", "register_event", "unregister_event", "clear_block",
    "register_key", "register_button", "register_custom_event",
    "events", "Time",
    # style
    "compile_style", "CompiledStyle", "StyleCache",
    # misc
    "Tree", "mainloop",
]
