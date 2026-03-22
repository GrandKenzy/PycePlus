from __future__ import annotations
from typing import TYPE_CHECKING

import pygame
if TYPE_CHECKING:
    from PycePlus.GUI.base import Base

from PycePlus.GUI.interface_man import Tree
from PycePlus.UI.window import Window
from PycePlus.CORE import events


renderable: list[Base] = []
def update():
    global renderable
    renderable.clear()
    bliteable: list[tuple[pygame.Surface, tuple[int, int]]] = []
    
    current_page = Tree.current_page()
    for widget in Tree.widgets:
        if not widget.visible: continue
        if widget.is_father_widget(): continue
        if widget.page != current_page: continue
        
        
        if widget.is_container():
            widget.render(renderable)
    
        renderable.append(widget)
        bliteable.append((widget.texture, widget.rect.topleft))
    
    Window.blits(bliteable)
    renderable = list(reversed(renderable))
    
def exam():
    
    
    if not events.window_is_focus or not events._mouse_ready: return
    X, Y = events.X, events.Y
    LEFT, MIDDLE, RIGHT = events.DEFAULT_BUTTONS
    focus: 'Base' = None
    
    for widget in renderable:
        X = X - widget.abs_x
        Y = Y - widget.abs_y

        COLLIDE = widget.rect.collidepoint((X, Y))
        if not focus and COLLIDE:
            focus = widget    
            
            if widget.is_hover: # hovering
                if widget._ROM[11]: widget._ROM[11](widget, (X, Y))
            else:
                if widget._ROM[9]: widget._ROM[9](widget, (X, Y))
                widget.is_hover = True
                
            if LEFT == 1 and widget._bflags[0] == 0:
                if widget._ROM[0]: widget._ROM[0](widget, (X, Y))
                widget._bflags[0] = 1
            elif LEFT == 2:
                if widget._ROM[2]: widget._ROM[2](widget, (X, Y))
            elif LEFT == 0 and widget._bflags[0] == 1:
                if widget._ROM[1]: widget._ROM[1](widget, (X, Y))
                widget._bflags[0] = 0
                
            if MIDDLE == 1:
                if widget._ROM[3]: widget._ROM[3](widget, (X, Y))
                widget._bflags[1] = 1
            elif MIDDLE == 2:
                if widget._ROM[5]: widget._ROM[5](widget, (X, Y))
            elif MIDDLE == 0 and widget._bflags[1] == 1:
                if widget._ROM[4]: widget._ROM[4](widget, (X, Y))
                widget._bflags[1] = 0
                
            if RIGHT == 1:
                if widget._ROM[6]: widget._ROM[6](widget, (X, Y))
                widget._bflags[2] = 1
            elif RIGHT == 2:
                if widget._ROM[8]: widget._ROM[8](widget, (X, Y))
            elif RIGHT == 0 and widget._bflags[2] == 1:
                if widget._ROM[7]: widget._ROM[7](widget, (X, Y))
                widget._bflags[2] = 0
        else:
            if not COLLIDE:
                if widget.is_hover:
                    if widget._ROM[10]: widget._ROM[10](widget, (X, Y))
                    widget.is_hover = False