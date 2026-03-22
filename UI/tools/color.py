import random
from typing import Any
from matplotlib.colors import to_rgba, CSS4_COLORS, to_hex
import pygame

def random_color(count: int, alpha: int = 255) -> list[tuple[int, int, int, int]]:
    return [(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255), alpha) for _ in range(count)]

class Color(pygame.Color):
    def __init__(self, r: int = 0, g: int = 0, b: int = 0, a: int = 255):
        super().__init__(r, g, b, a)

    def __repr__(self) -> str:
        return f"Color({self.r}, {self.g}, {self.b}, {self.a})"
    
    def update(self, color: Any):
        if isinstance(color, (tuple, list)):
            if len(color) == 3:
                self.r, self.g, self.b = color
                self.a = 255
            elif len(color) == 4:
                self.r, self.g, self.b, self.a = color
        elif isinstance(color, str):
            if color.startswith('#') or color in CSS4_COLORS:
                r, g, b, a = to_rgba(color)
                self.r, self.g, self.b, self.a = int(r*255), int(g*255), int(b*255), int(a*255)
            elif color == 'random':
                self.r, self.g, self.b, self.a = random_color(1, 255)[0]
            elif color == 'transparent':
                self.r, self.g, self.b, self.a = 0, 0, 0, 0
            else:
                raise ValueError(f"Unknown color string: {color}")
        elif isinstance(color, Color):
            self.r, self.g, self.b, self.a = color.r, color.g, color.b, color.a
        else:
            raise ValueError(f"Invalid color type: {type(color)}")
        
    def invert(self):
        self.r = 255 - self.r
        self.g = 255 - self.g
        self.b = 255 - self.b
        
    def grayscale(self) -> "Color":
        gray = (self.r + self.g + self.b) // 3
        return Color(gray, gray, gray, self.a)
        
    def to_hex(self) -> str:
        return to_hex((self.r/255, self.g/255, self.b/255, self.a/255))
    
    def to_tuple(self) -> tuple[int, int, int, int]:
        return (self.r, self.g, self.b, self.a)
    
    def tuple_RGB(self) -> tuple[int, int, int]:
        return (self.r, self.g, self.b)
    
    @staticmethod
    def makefrom(c: Any) -> "Color":
        if isinstance(c, Color):
            return c
        col = Color(0, 0, 0, 255)
        col.update(c)
        return col
    

    def tonality(self) -> int:
        return (self.r + self.g + self.b) // 3
    
    def is_nearby(self, color: Any, tolerance: int = 10) -> bool:
        color = Color.makefrom(color)
        return (abs(self.r - color.r) < tolerance and
                abs(self.g - color.g) < tolerance and
                abs(self.b - color.b) < tolerance)
    
    def is_light(self) -> bool:
        # Luminance check
        luminance = 0.2126 * self.r + 0.7152 * self.g + 0.0722 * self.b
        return luminance > 128
    
    def is_dark(self) -> bool:
        return not self.is_light()
    
    
    def adjust_brightness(self, factor: float, new: bool = False) -> "Color | None":
        r = min(max(int(self.r * factor), 0), 255)
        g = min(max(int(self.g * factor), 0), 255)
        b = min(max(int(self.b * factor), 0), 255)
        if new:
            return Color(r, g, b, self.a)
        else:
            self.r, self.g, self.b = r, g, b
            
    def lerp(self, target: Any, t: float = 0.5, new: bool = False) -> "Color | None":

        target = Color.makefrom(target)
        r = int(self.r + (target.r - self.r) * t)
        g = int(self.g + (target.g - self.g) * t)
        b = int(self.b + (target.b - self.b) * t)
        a = int(self.a + (target.a - self.a) * t)
        if new:
            return Color(r, g, b, a)
        else:
            self.r, self.g, self.b, self.a = r, g, b, a
            
            
from typing import TypeAlias
colorType: TypeAlias = Color | tuple[int, int, int, int] | tuple[int, int, int] | str