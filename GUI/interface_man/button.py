from typing import Callable

from PycePlus.GUI.frame import Frame, Base, Window
class Button(Base):
    def __init__(
        self,
        father: 'Frame | Window | None' = None,
        text: str = 'Button',
        command: Callable[..., None] | None = None,
        double_click: Callable[..., None] | None = None,
        
        name: str | None = None,
        page: str | None = None,
    ):
        pass