import sys

import pygame

from PycePlus.UI import window

class Application:
    state = 'busy'
    files: list[dict[str, str]] = []
    MEMORY_LOW_FACTOR = 0.2
    DISK_LOW_FACTOR = 0.1
    is_online = False
    connection_lost = False
    FPS: int = 60
    REFRESH: bool = True
    root = ''
    
def exit():
    pygame.quit()
    sys.exit()
    
    