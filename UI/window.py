import os

import pygame

_WINDOW: pygame.Surface = None
_INITINF = pygame.display.Info()
_COLOR = (0, 0, 0)
_CONFIGURATION: dict[str, int | bool] = {
    'flags': 0,
    'vsync': False,
    'display': 0,
    'depth': 32
}

CENTER = -1

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
    
    icon: pygame.Surface | str | None = None,
    background_color: tuple[int, int, int] = (0, 0, 0),
    vsync: bool = False,
    display: int = 0,
    depth: int = 32
):
    
    global _WINDOW, _COLOR

    flags = 0
    if fulls_screen:
        flags |= pygame.FULLSCREEN
    if resizable:
        flags |= pygame.RESIZABLE
    if noframe:
        flags |= pygame.NOFRAME
    if doublebuffer:
        flags |= pygame.DOUBLEBUF
    
    _WINDOW = pygame.display.set_mode((width, height), flags, depth, display, vsync)
    pygame.display.set_caption(title)
    if icon:
        pass
    
    _COLOR = background_color
    
    cx, cy = pygame.display.get_window_position()
    if x == CENTER:
        x = cx
    if y == CENTER:
        y = cy
    pygame.display.set_window_position((x, y))
    
    _CONFIGURATION['flags'] = flags
    _CONFIGURATION['vsync'] = vsync
    _CONFIGURATION['display'] = display
    _CONFIGURATION['depth'] = depth
    
    return Window()


class Window:
    abs_x = 0
    abs_y = 0
    abs_pos = (0, 0)
    @staticmethod  
    def blit(surface: pygame.Surface, pos: tuple[int, int] = (0, 0)):
        _WINDOW.blit(surface, pos)
        
        
    @staticmethod  
    def clear():
        if _COLOR:
            _WINDOW.fill(_COLOR)
            
            
    @staticmethod
    def blits(sequence: list[tuple[pygame.Surface, tuple[int, int]]]):
        _WINDOW.blits(sequence)
            
    @staticmethod  
    def title(title: str | None):
        if title:
            pygame.display.set_caption(title)
        return pygame.display.get_caption()[0]
    
    @staticmethod  
    def set_icon(icon: str | pygame.Surface):
        pass

    @staticmethod  
    def screensize():
        return _INITINF.current_w, _INITINF.current_h


    @staticmethod  
    def window_size():
        return _WINDOW.get_size()

    @staticmethod  
    def position(x: int | None = None, y: int | None = None):
        cx, cy = pygame.display.get_window_position()
        x = x or cx
        y = y or cy
        pygame.display.set_window_position((x, y))

    @staticmethod  
    def get_position():
        return pygame.display.get_window_position()


    @staticmethod  
    def get_window():
        return _WINDOW

    @staticmethod  
    def reopen(
        title: str | None =None, 
        width: int | None=None,
        height: int | None = None,
        x: int | None = None,
        y: int | None = None,
        
        fulls_screen: bool | None = None, 
        resizable: bool | None = None,
        noframe: bool | None = None,
        doublebuffer: bool | None = None,
        
        icon: pygame.Surface | str | None | None = None,
        background_color: tuple[int, int, int] | None = None,
        vsync: bool | None = None,
        display: int | None = None,
        depth: int | None = None
    ):
        global _WINDOW, _COLOR
        
        title = title or pygame.display.get_caption()[0]
        width = width or _WINDOW.get_width()
        height = height or _WINDOW.get_height()
        cx, cy = pygame.display.get_window_position()
        x = x or cx
        y = y or cy
        
        fulls_screen = fulls_screen or _CONFIGURATION['flags'] & pygame.FULLSCREEN
        resizable = resizable or _CONFIGURATION['flags'] & pygame.RESIZABLE
        noframe = noframe or _CONFIGURATION['flags'] & pygame.NOFRAME
        doublebuffer = doublebuffer or _CONFIGURATION['flags'] & pygame.DOUBLEBUF
        
        icon = icon or None
        background_color = background_color or _COLOR
        vsync = vsync or _CONFIGURATION['vsync']
        display = display or _CONFIGURATION['display']
        depth = depth or _CONFIGURATION['depth']
        
        flags = 0
        if fulls_screen:
            flags |= pygame.FULLSCREEN
        if resizable:
            flags |= pygame.RESIZABLE
        if noframe:
            flags |= pygame.NOFRAME
        if doublebuffer:
            flags |= pygame.DOUBLEBUF
        
        _WINDOW = pygame.display.set_mode((width, height), flags, depth, display, vsync)
        pygame.display.set_caption(title)
        if icon:
            pass
    

__all__ = ['title', 'set_icon', 'screensize', 'window_size', 'position', 'get_position', 'get_window', 'reopen']