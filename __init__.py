"""
PycePlus — Pygame-based UI framework with dirty rendering, CSS styles,
optimized tasks, networking helpers, and OpenGL-capable widgets.
"""
from __future__ import annotations

import os

import pygame

pygame.init()

from PycePlus.CORE.main import mainloop
from PycePlus.UI import Application
Application.root = os.path.dirname(os.path.abspath(__file__))

from PycePlus.UI import *
from PycePlus.UI.tools.color import Color
from PycePlus.UI.tools.font  import Font

from PycePlus.GUI import (
    Base, Padding, Outline,
    Frame, FlexFrame, GridFrame, FlowFrame, FreeFrame,
    Button, Label, Checkbox, Image,
    TextInput, TextBox, VideoPlayer, OpenGLCanvas,
    Tree,
)
from PycePlus.GUI.interface_man.style import compile_style, CompiledStyle, StyleCache

from PycePlus.CORE.events import (
    register_button, register_custom_event, register_key,
)
from PycePlus import __events__ as events
from PycePlus.__events__ import (
    emit, register_event, unregister_event, clear_block,
)
from PycePlus.CORE.timec import Time
from PycePlus.CORE.tasker import tasker, pump, submit, call_soon, GLOBAL_TASKER, Tasker
Application.tasker = tasker
from PycePlus.CORE.host import HostClient, HostServer
from PycePlus.CORE.tools import asynchronous
from PycePlus.CORE.tools import network
from PycePlus.GUI.widgets.extras import *

__version__ = "3.0.0"

__all__ = [
    "Color", "Font",
    "Frame", "FlexFrame", "GridFrame", "FlowFrame", "FreeFrame",
    "Base", "Button", "Label", "Checkbox", "Image",
    "TextInput", "TextBox", "VideoPlayer", "OpenGLCanvas",
    "emit", "register_event", "unregister_event", "clear_block",
    "register_key", "register_button", "register_custom_event",
    "events", "Time",
    "compile_style", "CompiledStyle", "StyleCache",
    "Tree", "mainloop",
    "tasker", "pump", "submit", "call_soon", "GLOBAL_TASKER", "Tasker",
    "HostClient", "HostServer",
]
