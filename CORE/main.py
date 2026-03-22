from typing import Callable

from networkx import is_connected
import pygame
from PycePlus.CORE.timec import Time
from PycePlus.CORE import events
from PycePlus import __events__ as _EV
from PycePlus.UI import Application, window
from PycePlus.CORE.tools import watch, usage
from PycePlus.CORE.tools import network as NET

from PycePlus.GUI.interface_man import render
CLOCK = pygame.time.Clock()



def handle_system_action_events():
    state = Application.state

    if state == 'busy':
        if events.Info.num == 0: 
            _EV.emit('system.idle', Time.current_ticks)
            Application.state = 'idle'
            return
    elif state == 'idle':
        if events.Info.num > 0:
            _EV.emit('system.resume', Time.current_ticks)
            Application.state = 'busy'
            return
        elif Time.wait('system.idle.timewait', 10, reset=True):
            _EV.emit('system.suspend', Time.current_ticks)
            Application.state = 'suspended'
            return
    elif state == 'suspended':
        if events.Info.num > 0:
            _EV.emit('system.resume', Time.current_ticks)
            Application.state = 'busy'
            return
        
        
    events.mouse_motion_checked = False
    events.key_buttons_pressed = False
    events.mouse_buttons_pressed = False
    events.mouse_wheel_checked = False
    events.Info.num = 0
    
             
def handle_usage_memory():
    old_disk = usage.Proc.flag_disk
    old_mem = usage.Proc.flag_mem
    old_disk_p = usage.Proc.flag_disk_p
    old_mem_p = usage.Proc.flag_mem_p
    
    usage.Proc.flag_disk = usage.get_disk_usage('b')
    usage.Proc.flag_mem = usage.get_memory_usage('b')
    usage.Proc.flag_disk_p = usage.get_process_disk_usage('b')
    usage.Proc.flag_mem_p = usage.get_process_memory_usage('b')
    
    if old_disk != usage.Proc.flag_disk:
        _EV.emit('disk.system.change', Time.current_ticks, usage.Proc.flag_disk)
    if old_mem != usage.Proc.flag_mem:
        _EV.emit('memory.system.change', Time.current_ticks, usage.Proc.flag_mem)
    if old_disk_p != usage.Proc.flag_disk_p:
        _EV.emit('disk.process.change', Time.current_ticks, usage.Proc.flag_disk_p)
    if old_mem_p != usage.Proc.flag_mem_p:
        _EV.emit('memory.process.change', Time.current_ticks, usage.Proc.flag_mem_p)
        
    if usage.memory_is_low(Application.MEMORY_LOW_FACTOR):
        _EV.emit(
            'memory.low',
            Time.current_ticks,
            usage.Proc.flag_mem_p / usage.Proc.flag_mem if usage.Proc.flag_mem else 0
        )

    if usage.disk_is_low(Application.DISK_LOW_FACTOR):
        _EV.emit(
            'disk.low',
            Time.current_ticks,
            usage.Proc.flag_disk_p / usage.Proc.flag_disk if usage.Proc.flag_disk else 0
        )
        
def handle_net():
    if NET.is_connected() and Application.is_online == False:
        Application.is_online = True
        Application.connection_lost = False
        _EV.emit('network.reconnect', Time.current_ticks)
    elif NET.is_connected() == False and Application.is_online == True:
        Application.is_online = False
        Application.connection_lost = True
        _EV.emit('network.disconnect', Time.current_ticks)
        
    elif NET.is_connected() and Application.is_online == False and Application.connection_lost == False:
        _EV.emit('network.connect', Time.current_ticks)
    
        
def mainloop(
    FPS: int = 60,   
    CALL_PER_SECOND: Callable[..., None] | None = None,
    REVIEW_PATHS: list[str] = [],
    REVIEW_MAIN_DIR: bool = True,
    ):
    
    Application.FPS = FPS
    get_ticks = pygame.time.get_ticks
    last = 0
    
    watcher = watch.init('--main' if REVIEW_MAIN_DIR else '--nomain', *REVIEW_PATHS)
    
    usage.Proc.flag_disk = usage.get_disk_usage('b')
    usage.Proc.flag_mem = usage.get_memory_usage('b')
    usage.Proc.flag_disk_p = usage.get_process_disk_usage('b')
    usage.Proc.flag_mem_p = usage.get_process_memory_usage('b')
    
    while True:

        
        # execute events
        Application.files = watcher.poll()
        events.exam()
         
        
        # update time
        Time.current_ticks = now = get_ticks() / 1000
        if events.Info.num > 15:
            _EV.emit('system.gui.fatigue', Time.current_ticks, events.Info.num)
        if now - last >= 1:
            last = now
            Time.seconds += 1
            if CALL_PER_SECOND:
                CALL_PER_SECOND()
                
            handle_net()
            handle_usage_memory()
            handle_system_action_events()
            last = now
            

        # resolve schedulers
        # pendiente.
        
        # update logic
        if Application.REFRESH:
            window._WINDOW.fill(window._COLOR)
            render.update()
            print('renderizando')
        
        # update graphics
        render.exam()
        
        
        if Application.REFRESH:
            pygame.display.flip()
            Application.REFRESH = False
            print('refrescando')
        
        
        CLOCK.tick(Application.FPS)
