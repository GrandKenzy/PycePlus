from __future__ import annotations
from typing import Callable, Literal, TYPE_CHECKING
if TYPE_CHECKING:
    from PycePlus.GUI.frame import Frame

import pygame

from PycePlus.UI.window import Window
from PycePlus.UI.tools.color import Color
from PycePlus.UI import Application
from PycePlus.GUI.interface_man import Tree

wEvents = Literal[
    'mouse.button.left.click', 'mouse.button.left.release', 'mouse.button.left.repeat',
    'mouse.button.middle.click', 'mouse.button.middle.release', 'mouse.button.middle.repeat',
    'mouse.button.right.click', 'mouse.button.right.release', 'mouse.button.right.repeat',
    'mouse.hover', 'mouse.leave', 'mouse.hovering'
]

wEvents_Map = {
    'mouse.button.left.click': 0,
    'mouse.button.left.release': 1,
    'mouse.button.left.repeat': 2,

    'mouse.button.middle.click': 3,
    'mouse.button.middle.release': 4,
    'mouse.button.middle.repeat': 5,

    'mouse.button.right.click': 6,
    'mouse.button.right.release': 7,
    'mouse.button.right.repeat': 8,

    'mouse.hover': 9,
    'mouse.leave': 10,
    'mouse.hovering': 11
}

Cursors = Literal[ # cursores de pygame soporta, del 0 al 11
    'arrow', 'ibeam', 'wait', 'crosshair', 'waitarrow', 'sizenwse', 'sizenesw', 'sizewe', 'sizens', 'sizeall', 'no', 'hand'
]

Cursors_Map = {
    'arrow': 0,
    'ibeam': 1,
    'wait': 2,
    'crosshair': 3,
    'waitarrow': 4,
    'sizenwse': 5,
    'sizenesw': 6,
    'sizewe': 7,
    'sizens': 8,
    'sizeall': 9,
    'no': 10,
    'hand': 11
}



class Padding:
    def __init__(self, left: int, right: int, top: int, bottom: int):
        self.left = left
        self.right = right
        self.top = top
        self.bottom = bottom
        
    @property
    def all(self):
        return self.left, self.right, self.top, self.bottom
    
    def set_pad(self, left: int | None = None, right: int | None = None, top: int | None = None, bottom: int | None = None):
        self.left = left or self.left
        self.right = right or self.right
        self.top = top or self.top
        self.bottom = bottom or self.bottom


class Outline:
    def __init__(self, width: int, color: Color, border_radius: int, border_top_left_radius: int = 0, border_top_right_radius: int = 0, border_bottom_right_radius: int = 0, border_bottom_left_radius: int = 0, sides: tuple[int, int, int, int] = (1, 1, 1, 1)):
        self.width = width
        self.color = color
        self.border_radius = border_radius
        self.border_top_left_radius = border_top_left_radius
        self.border_top_right_radius = border_top_right_radius
        self.border_bottom_right_radius = border_bottom_right_radius
        self.border_bottom_left_radius = border_bottom_left_radius
        self.sides = sides
        self.gradient_colors: list[Color] = []
        self.type: Literal['normal', 'double', 'gradient'] = 'normal'
        self.gradient_type: Literal['horizontal', 'vertical'] = 'horizontal'

class Base:
    def __init__(self, father: 'Frame | None | Window' , name: str | None, page: str | None):
        
        self.father = father or Window
        self.name = name or f'{self.__class__.__name__}-{id(self)}'
        self.page = page or Tree.current_page()

        # coords
        self.rect: pygame.Rect = pygame.Rect(0, 0, 0, 0)
        self.padding = Padding(0, 0, 0, 0)
        self.outline = Outline(0, Color(0, 0, 0), 0)
        
        
        # gui
        self.texture: pygame.Surface = None
        self.background_color: Color = Color(0, 0, 0)
        self.color = Color(0, 0, 0)
        self.default_color = Color(0, 0, 0)
        self.cursor = 0
        self.visible = True
    
        # flags
        self.is_focus = False
        self.is_hover = False
        
        # private
        self._mask: pygame.Mask = None
        self._original_surface: pygame.Surface = None
        self._ROM: dict[int, Callable[..., None] | None] = {
            0: None, # mouse-left-click
            1: None, # mouse-left-release
            2: None, # mouse-left-repeat

            3: None, # mouse-middle-click
            4: None, # mouse-middle-release
            5: None, # mouse-middle-repeat

            6: None, # mouse-right-click
            7: None, # mouse-right-release
            8: None, # mouse-right-repeat
            
            9: None, # mouse-hover
            10: None, # mouse-leave
            11: None, # mouse-hovering
            
        }
        self._bflags = [0, 0, 0]
        
        if isinstance(self.father, Window):
            Tree.put(self)
        else:
            self.father.put(self)
    
    def bind(self, event: int | wEvents, callback: Callable[..., None] | None):
        if isinstance(event, int):
            self._ROM[event] = callback
        else:
            self._ROM[wEvents_Map[event]] = callback   
        return self
        
    def get_size(self):
        return self.rect.width, self.rect.height
    
    @property
    def width(self):
        return self.rect.width
    
    @property
    def height(self):
        return self.rect.height
    
    
    # relative
    @property
    def x(self):
        return self.rect.x
    
    @property
    def y(self):
        return self.rect.y
    
    @property
    def right(self):
        return self.rect.right
    
    @property
    def bottom(self):
        return self.rect.bottom
    
    @property
    def center(self):
        return self.rect.center
    
    @property
    def centerx(self):
        return self.rect.centerx
    
    @property
    def centery(self):
        return self.rect.centery
    
    # absolute
    @property
    def abs_x(self):
        return self.rect.x + self.father.abs_x
    
    @property
    def abs_y(self):
        return self.rect.y + self.father.abs_y
    
    @property
    def abs_right(self):
        return self.rect.right + self.father.abs_x
    
    @property
    def abs_bottom(self):
        return self.rect.bottom + self.father.abs_y
    
    @property
    def abs_center(self):
        return self.rect.center + self.father.abs_pos
     
    @property
    def abs_centerx(self):
        return self.rect.centerx + self.father.abs_x
    
    @property
    def abs_centery(self):
        return self.rect.centery + self.father.abs_y
    
    @property
    def abs_pos(self):
        return self.rect.topleft

    
    def is_father_widget(self):
        return isinstance(self.father, Base)
    
    def update(self):
        Application.REFRESH = True
        
    def unlink(self):
        if self.is_father_widget():
            self.father.unparent(self)
            self.father = Window
            
    def is_container(self) -> bool:
        return False