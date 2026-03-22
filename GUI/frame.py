from plyer import orientation
import pygame

from PycePlus.GUI.base import Base, Window, Literal, Cursors
from PycePlus.UI.tools.color import Color, colorType

class Scroll:
    def __init__(
        self,
        track_size: int = 0,
        scroll_gross: int = 0,
        orientation: Literal['horizontal', 'vertical'] = 'horizontal',
        scroll_color: colorType = (0, 0, 0),
        scroll_background_color: colorType = (255, 255, 255),
        scroll_radius: int = 0,
        track: bool = True,
        track_color: colorType | Literal['auto'] = 'auto',
        track_padding: int = 0,
        track_border_color: colorType = (0, 0, 0),
        track_border_width: int = 0,
    ):

        self.scroll_color = Color.makefrom(scroll_color)
        self.scroll_background_color = Color.makefrom(scroll_background_color)
        self.scroll_radius = scroll_radius
        self.track = track
        self.track_color = track_color
        self.track_padding = track_padding
        self.track_border_color = Color.makefrom(track_border_color)
        self.track_border_width = track_border_width
        self.orientation = orientation
        
        self.x = 0
        self.y = 0
        self.scroll_size = 0
        self.scroll_gross = scroll_gross
        self.track_size = track_size
        self.position = 0
        
    def set(self, x: int | None = None, y: int | None = None):
        self.x = x or self.x
        self.y = y or self.y
        
    def reset(self):
        self.x = 0
        self.y = 0
        
    def end(self):
        if self.orientation == 'horizontal':
            self.x = self.track_size - self.scroll_size
        else:
            self.y = self.track_size - self.scroll_size
        self.position = 1.0
        
    def render(self):
        # use pygame
        if self.orientation == 'vertical':
            track_width = self.scroll_gross + self.track_padding * 2
            track_height = self.track_size
            scroll_width = self.scroll_size
            scroll_height = self.scroll_gross
            scroll_x = self.x
            scroll_y = self.y
            
            track = pygame.Surface((track_width, track_height), pygame.SRCALPHA)
            track.fill(self.track_color)
            pygame.draw.rect(track, self.scroll_background_color, (scroll_x, scroll_y, track_width, track_height), 0, self.scroll_radius)
            pygame.draw.rect(track, self.scroll_color, (scroll_x, scroll_y, scroll_width, scroll_height), 1, self.scroll_radius)
            return track
        else:
            track_width = self.track_size
            track_height = self.scroll_gross + self.track_padding * 2
            scroll_width = self.scroll_gross
            scroll_height = self.scroll_size
            scroll_x = self.x
            scroll_y = self.y
            
            track = pygame.Surface((track_width, track_height), pygame.SRCALPHA)
            track.fill(self.track_color)
            pygame.draw.rect(track, self.scroll_background_color, (scroll_x, scroll_y, track_width, track_height), 0, self.scroll_radius)
            pygame.draw.rect(track, self.scroll_color, (scroll_x, scroll_y, scroll_width, scroll_height), 1, self.scroll_radius)
            return track


class Frame(Base):
    def __init__(
        self,
        father: 'Window | Frame | None' = None,
        
        width: int = 200,
        height: int = 200,
        background_color: colorType = (0, 0, 0),
        
        border_width: int = 0,
        border_color: colorType = (0, 0, 0),
        border_radius: int = 0,
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
        
        
        scrollable: bool = False,
        orientation: Literal['auto', 'vertical', 'horizontal', 'horizontal_and_vertical'] = 'auto',
        
        
        
        x: int = 0,
        y: int = 0,
        
        cursor: int | Cursors = 'arrow',
        name: str | None = None,
        page: str | None = None,
        visible: bool = True,
        
    ):

        super().__init__(father, name, page)
        
        self.texture = pygame.Surface((width, height), pygame.SRCALPHA)
        self.rect = pygame.Rect(x, y, width, height)
        
        self.outline.border_bottom_left_radius = border_bottom_left_radius
        self.outline.border_bottom_right_radius = border_bottom_right_radius
        self.outline.border_top_left_radius = border_top_left_radius
        self.outline.border_top_right_radius = border_top_right_radius
        
        self.background_color.update(background_color)
        self.padding.set_pad(padding_left, padding_right, padding_top, padding_bottom)
        
        self.scrollable = scrollable
        self.orientation = orientation
        
 
        
        
        self.childrens: list['Base'] = []
        
    def is_children(self, widget: 'Base'):
        if widget in self.childrens and widget.father == self:
            return True
        
    def parent(self, widget: 'Base'):
        if self.is_children(widget): return
        if widget.father == self:
            self.childrens.append(widget)
        elif widget in self.childrens:
            if widget.is_father_widget():
                widget.unlink()
                widget.father = self
        else:
            self.childrens.append(widget)
            widget.father = self
            
    def unparent(self, widget: 'Base'):
        if self.is_children(widget):
            self.childrens.remove(widget)
            widget.father = Window
        else:
            raise Exception(f'{widget.name} is not children of {self.name}')
        
            
    def get_childrens(self):
        return self.childrens
    
    def is_container(self):
        return True
    
    
    def render(self, renderable: list[Base]):
        self.texture.fill(self.background_color)
        
        for child in self.childrens:
            if not child.visible: continue
            if child.page != self.page: continue
            
            self.texture.blit(child.texture, child.rect.topleft)
            renderable.append(child)
            

     