from typing import Callable

import pygame
from PycePlus.UI import exit
from PycePlus.CORE.timec import Time
from PycePlus import __events__ as _EV

class Info:
    num = 0
    
    
    
# LOOKUPS
_event_get = pygame.event.get
_mouse_pos = pygame.mouse.get_pos
_get_pressed = pygame.key.get_pressed

# CALL DATA
KEYS_EVENT_REGISTER = {}
BUTTONS_EVENT_REGISTER = {}
COMBO_EVENT_REGISTER = {}
CUSTOM_EVENT_REGISTER = {}

# CHECK DATA
current_events = []

mouse_motion_checked = False
mouse_wheel_checked = False
key_buttons_pressed = False
mouse_buttons_pressed = False
window_is_focus = False


# EVENTS DATA
X = 0
Y = 0
MOVED_X = 0
MOVED_Y = 0
SCROLL_X = 0
SCROLL_Y = 0
DEFAULT_BUTTONS = [0, 0, 0]
mouse_moved = False
keyboard_is_active = False
keyboard_input = False
keys_pressed = []
_mouse_ready = False


def register_key(key: int, on_press: Callable[..., None] | None = None, on_release: Callable[..., None] | None = None, on_repeat: Callable[..., None] | None = None):
    KEYS_EVENT_REGISTER[key] = [on_press, on_release, on_repeat, False]
    
def register_button(button: int, on_press: Callable[..., None] | None = None, on_release: Callable[..., None] | None = None, on_repeat: Callable[..., None] | None = None, double_click: Callable[..., None] | None = None):
    BUTTONS_EVENT_REGISTER[button] = [on_press, on_release, on_repeat, double_click, False, 0]
    
def register_custom_event(event: int, on_event: Callable[..., None] | None = None):
    CUSTOM_EVENT_REGISTER[event] = on_event




def exam():
    global current_events, mouse_motion_checked, key_buttons_pressed, mouse_buttons_pressed, mouse_moved, mouse_wheel_checked
    global X, Y, MOVED_X, MOVED_Y, SCROLL_X, SCROLL_Y
    global keyboard_is_active, keyboard_input
    global window_is_focus, _mouse_ready
    
    current_events = _event_get()

    # reset

    mouse_moved = False
    
    keys_pressed = _get_pressed()
    keyboard_is_active = keys_pressed.count(True) > 0
    
      
    for k, (_, _, on_repeat, flag) in KEYS_EVENT_REGISTER.items():
        if flag: # pressed
            if on_repeat:
                on_repeat()
            if not key_buttons_pressed:
                Info.num += 1
            key_buttons_pressed = True
    
    for b, (_, _, on_repeat, _, flag, _) in BUTTONS_EVENT_REGISTER.items():
        if flag: # pressed
            if on_repeat:
                on_repeat()
            if not mouse_buttons_pressed:
                Info.num += 1
            mouse_buttons_pressed = True
        DEFAULT_BUTTONS[b - 1] = 2
    
    for event in current_events:
        if event.type == pygame.QUIT:
            exit()
        
        
        # mouse
        e_type = event.type
        if e_type == pygame.MOUSEMOTION:
            _mouse_ready = True
            MOVED_X, MOVED_Y = event.rel
            if MOVED_X != 0 or MOVED_Y != 0:
                if not mouse_motion_checked:
                    Info.num += 1
                mouse_motion_checked = True
                
            X, Y = _mouse_pos()
            mouse_moved = True
            

            
        elif e_type == pygame.MOUSEWHEEL:
            SCROLL_X, SCROLL_Y = event.x, event.y
            if SCROLL_X != 0 or SCROLL_Y != 0:
                if not mouse_wheel_checked:
                    Info.num += 1
                mouse_wheel_checked = True
        
            
        elif e_type == pygame.KEYDOWN:
            u = event.unicode
            k = event.key
            
            if k in KEYS_EVENT_REGISTER:
                KEYS_EVENT_REGISTER[k][3] = True
                command = KEYS_EVENT_REGISTER[k][0]
                if command:
                    command()
            Info.num += 1
            keyboard_input = True
            
        elif e_type == pygame.KEYUP:
            k = event.key
            if k in KEYS_EVENT_REGISTER:
                KEYS_EVENT_REGISTER[k][3] = False
                command = KEYS_EVENT_REGISTER[k][1]
                if command:
                    command()
            
        elif e_type == pygame.MOUSEBUTTONDOWN:
            b = event.button
            if b in BUTTONS_EVENT_REGISTER:
                BUTTONS_EVENT_REGISTER[b][4] = True
                delta = BUTTONS_EVENT_REGISTER[b][5]
                if Time.current_ticks - delta < 0.6:
                    # double click
                    command = BUTTONS_EVENT_REGISTER[b][3]
                    if command:
                        command()
                else:
                    BUTTONS_EVENT_REGISTER[b][5] = Time.current_ticks
                    command = BUTTONS_EVENT_REGISTER[b][0]
                    if command:
                        command()
            DEFAULT_BUTTONS[b - 1] = 1
            Info.num += 1
                
        elif e_type == pygame.MOUSEBUTTONUP:
            b = event.button
            if b in BUTTONS_EVENT_REGISTER:
                BUTTONS_EVENT_REGISTER[b][4] = False
                command = BUTTONS_EVENT_REGISTER[b][1]
                if command:
                    command()
            Info.num += 1
            DEFAULT_BUTTONS[b - 1] = 0
            
        
        elif e_type in CUSTOM_EVENT_REGISTER:
            command = CUSTOM_EVENT_REGISTER[e_type]
            if command:
                command()
            Info.num += 1
            
        elif e_type == pygame.WINDOWFOCUSGAINED:
            window_is_focus = True
            _EV.emit('system.window.gained', Time.current_ticks)
            
        elif e_type == pygame.WINDOWFOCUSLOST:
            window_is_focus = False
            _EV.emit('system.window.lost', Time.current_ticks)