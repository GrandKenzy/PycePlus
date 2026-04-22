from collections.abc import Callable
from typing import Literal

from PycePlus.GUI.frame import Frame, Base, Window, Cursors
from PycePlus.UI.tools.color import Color, colorType
from PycePlus.UI.tools.font import Font, FontLike

class Button(Base):
    def __init__(
        self,
        father: 'Frame | Window | None' = None,
        text: str = 'Button',
        command: Callable[..., None] | None = None,
        double_click: Callable[..., None] | None = None,
        
        font_family: FontLike = ['Comic Sans MS', 'verdana', 'arial'],
        font_size: int = 20,
        font_type: Literal['freetype', 'pygame'] = 'freetype',
        antialias: bool = True,
        color: colorType = (0, 0, 0),
        background_color: colorType = (255, 255, 255),
        
        border_width: int = 1,
        border_color: colorType = (0, 0, 0),
        border_top_left_radius: int = 0,
        border_top_right_radius: int = 0,
        border_bottom_right_radius: int = 0,
        border_bottom_left_radius: int = 0,
        border_sides: tuple[int, int, int, int] = (1, 1, 1, 1),
        border_type: Literal['normal', 'double', 'gradient'] = 'normal',
        border_gradient_type: Literal['horizontal', 'vertical'] = 'horizontal',
        border_gradient_colors: list[colorType] = [],
        
        padding_left: int = 0,
        padding_right: int = 0,
        padding_top: int = 0,
        padding_bottom: int = 0,
        
        cursor: int | Cursors = 0,
        name: str | None = None,
        page: str | None = None,
        visible: bool = True
    ):
        
        super().__init__(father, name, page)
        
        self.text = text
        
        self.padding.set_pad(padding_left, padding_right, padding_top, padding_bottom)
        self.outline.border_bottom_left_radius = border_bottom_left_radius
        self.outline.border_bottom_right_radius = border_bottom_right_radius
        self.outline.border_top_left_radius = border_top_left_radius
        self.outline.border_top_right_radius = border_top_right_radius
        self.outline.width = border_width
        self.outline.color = Color.makefrom(border_color)
        self.outline.sides = border_sides
        self.outline.type = border_type
        self.outline.gradient_type = border_gradient_type
        self.outline.gradient_colors = border_gradient_colors
        
        self.visible = visible
        self.cursor = cursor
        
        self.font = Font(
            font_family,
            font_size, 
            antialias,
            freetype=(font_type == 'freetype')
        )
        
        
        if callable(command): self.bind('mouse.button.left.click', command)
        elif callable(double_click): self.bind('mouse.button.left.double-click', double_click)