from __future__ import annotations

from typing import Callable

import pygame

from PycePlus.UI import Application
from PycePlus.UI import window
from PycePlus.CORE import events, tasker
from PycePlus.GUI.interface_man import render
from PycePlus.CORE.tools import watch, usage
from PycePlus import __events__ as _EV
from PycePlus.CORE.timec import Time

CLOCK = pygame.time.Clock()


def handle_usage_memory():
    old_disk_p = usage.Proc.flag_disk_p
    old_mem_p = usage.Proc.flag_mem_p
    usage.Proc.flag_disk_p = usage.get_process_disk_usage('b')
    usage.Proc.flag_mem_p = usage.get_process_memory_usage('b')

    if old_disk_p != usage.Proc.flag_disk_p:
        _EV.emit('disk.process.change', Time.current_ticks, usage.Proc.flag_disk_p)
    if old_mem_p != usage.Proc.flag_mem_p:
        _EV.emit('memory.process.change', Time.current_ticks, usage.Proc.flag_mem_p)

    if usage.memory_is_low(Application.MEMORY_LOW_FACTOR):
        _EV.emit('memory.low', Time.current_ticks, usage.Proc.flag_mem_p / usage.Proc.flag_mem if usage.Proc.flag_mem else 0)

    if usage.disk_is_low(Application.DISK_LOW_FACTOR):
        _EV.emit('disk.low', Time.current_ticks, usage.Proc.flag_disk_p / usage.Proc.flag_disk if usage.Proc.flag_disk else 0)


def handle_net():
    connected = False
    try:
        from PycePlus.CORE.tools.network import is_connected
        connected = bool(is_connected())
    except Exception:
        connected = False

    if connected and not Application.is_online:
        Application.is_online = True
        Application.connection_lost = False
        _EV.emit('network.reconnect', Time.current_ticks)
    elif not connected and Application.is_online:
        Application.is_online = False
        Application.connection_lost = True
        _EV.emit('network.disconnect', Time.current_ticks)
    elif connected and not Application.is_online and not Application.connection_lost:
        _EV.emit('network.connect', Time.current_ticks)


def mainloop(
    FPS: int = 60,
    CALL_PER_SECOND: Callable[..., None] | None = None,
    REVIEW_PATHS: list[str] | None = None,
    REVIEW_MAIN_DIR: bool = True,
    *,
    use_tasker: bool = True,
):
    Application.FPS = FPS
    get_ticks = pygame.time.get_ticks
    last = 0

    watcher = None
    REVIEW_PATHS = REVIEW_PATHS or []
    try:
        if REVIEW_PATHS or REVIEW_MAIN_DIR:
            watcher = watch.init('--main' if REVIEW_MAIN_DIR else '--nomain', *REVIEW_PATHS)
    except Exception:
        watcher = None

    usage.Proc.flag_disk = usage.get_disk_usage('b')
    usage.Proc.flag_mem = usage.get_memory_usage('b')
    usage.Proc.flag_disk_p = usage.get_process_disk_usage('b')
    usage.Proc.flag_mem_p = usage.get_process_memory_usage('b')

    while True:
        if watcher is not None:
            try:
                Application.files = watcher.poll()
            except Exception:
                Application.files = []

        events.exam()
        Time.current_ticks = now = get_ticks() / 1000.0

        if use_tasker:
            try:
                tasker.pump()
            except Exception:
                pass

        if events.Info.num > 15:
            _EV.emit('system.gui.fatigue', Time.current_ticks, events.Info.num)

        if now - last >= 1:
            last = now
            Time.seconds += 1
            if CALL_PER_SECOND:
                CALL_PER_SECOND()
            handle_net()
            handle_usage_memory()

        if Application.REFRESH:
            window.Window.clear()
            render.update()

        render.exam()

        if Application.REFRESH:
            pygame.display.flip()
            Application.REFRESH = False

        CLOCK.tick(Application.FPS)
