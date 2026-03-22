import threading
import atexit
from typing import Callable, Any
from PycePlus import __events__ as _EV
from PycePlus.CORE.timec import Time


class _Thread:
    _id_counter = 0

    def __init__(self, func: Callable[..., Any], name: str | None = None, desc: str | None = None):
        type(self)._id_counter += 1
        self.id = type(self)._id_counter
        self.func = func
        self.name = name or f"thread-{self.id}"
        self.desc = desc or ""
        self._thread = threading.Thread(target=self._wrap, daemon=True)

    def _wrap(self):
        _EV.emit('thread.start', Time.current_ticks, self.id, self.name)
        try:
            self.func()
            _EV.emit('thread.end', Time.current_ticks, self.id, self.name)
        except Exception as e:
            _EV.emit('thread.error', Time.current_ticks, self.id, self.name, e)
        finally:
            Threads._registry.pop(self.id, None)

    def start(self):
        self._thread.start()
        return self

    def wait(self):
        self._thread.join()

    def kill(self):
        Threads._registry.pop(self.id, None)


class Threads:
    _registry: dict[int, _Thread] = {}

    @classmethod
    def new(cls, func: Callable[..., Any], name: str | None = None, desc: str | None = None):
        t = _Thread(func, name, desc)
        cls._registry[t.id] = t
        _EV.emit('thread.create', Time.current_ticks, t.id, t.name)
        return t

    @classmethod
    def run(cls, func: Callable[..., Any], name: str | None = None, desc: str | None = None):
        return cls.new(func, name, desc).start()

    @classmethod
    def shutdown_all(cls):
        cls._registry.clear()


atexit.register(Threads.shutdown_all)