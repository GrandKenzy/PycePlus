"""PycePlus.GUI.widgets — all widget classes."""
from .common import Button, Label, Checkbox, Image
from .input import TextInput, TextBox
from .video import VideoPlayer
from .opengl import OpenGLCanvas

__all__ = [
    "Button", "Label", "Checkbox", "Image",
    "TextInput", "TextBox",
    "VideoPlayer",
    "OpenGLCanvas",
]
