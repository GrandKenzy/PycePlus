from __future__ import annotations

import atexit
from typing import Any, Callable

from PycePlus import __events__ as _EV
from PycePlus.CORE.tasker import GLOBAL_TASKER as _TASKER
from PycePlus.CORE.timec import Time


class _Thread:
    _id_counter = 0

    def __init__(self, func: Callable[..., Any], name: str | None = None, desc: str | None = None):
        type(self)._id_counter += 1
        self.id = type(self)._id_counter
        self.func = func
        self.name = name or f"thread-{self.id}"
        self.desc = desc or ""
        self._future = None

    def start(self):
        self._future = _TASKER.submit(self._invoke)
        return self

    def _invoke(self):
        _EV.emit("thread.start", Time.current_ticks, self.id, self.name)
        try:
            result = self.func()
            _EV.emit("thread.end", Time.current_ticks, self.id, self.name)
            return result
        except BaseException as exc:
            _EV.emit("thread.error", Time.current_ticks, self.id, self.name, exc)
            raise

    def wait(self):
        if self._future:
            return self._future.result()

    def kill(self):
        return None


class Threads:
    _registry: dict[int, _Thread] = {}

    @classmethod
    def new(cls, func: Callable[..., Any], name: str | None = None, desc: str | None = None):
        t = _Thread(func, name, desc)
        cls._registry[t.id] = t
        _EV.emit("thread.create", Time.current_ticks, t.id, t.name)
        return t

    @classmethod
    def run(cls, func: Callable[..., Any], name: str | None = None, desc: str | None = None):
        return cls.new(func, name, desc).start()

    @classmethod
    def shutdown_all(cls):
        cls._registry.clear()


atexit.register(Threads.shutdown_all)
