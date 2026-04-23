from __future__ import annotations

import atexit
import os
import queue
import threading
import time
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any, Callable, Iterable

from PycePlus import __events__ as _EV
from PycePlus.CORE.timec import Time

_MAIN_THREAD_ID = threading.get_ident()


def _safe_call(func: Callable[..., Any] | None, *args: Any, **kwargs: Any) -> Any:
    if not callable(func):
        return None
    return func(*args, **kwargs)


@dataclass(slots=True)
class TaskPacket:
    func: Callable[..., Any]
    args: tuple[Any, ...]
    kwargs: dict[str, Any]
    callback: Callable[[Any], Any] | None = None
    error: Callable[[BaseException], Any] | None = None
    finalizer: Callable[[], Any] | None = None


class Tasker:
    """Optimized task runner for background work with a main-thread pump."""

    def __init__(self, workers: int | None = None, queue_size: int = 0):
        self.workers = max(1, workers or (os.cpu_count() or 4))
        self._executor = ThreadPoolExecutor(max_workers=self.workers, thread_name_prefix="PycePlus")
        self._queue: "queue.Queue[Callable[[], Any]]" = queue.Queue(maxsize=queue_size or 0)
        self._alive = True
        self._lock = threading.RLock()
        self._timers: set[threading.Thread] = set()

    @property
    def is_main_thread(self) -> bool:
        return threading.get_ident() == _MAIN_THREAD_ID

    def submit(
        self,
        func: Callable[..., Any],
        *args: Any,
        callback: Callable[[Any], Any] | None = None,
        error: Callable[[BaseException], Any] | None = None,
        finalizer: Callable[[], Any] | None = None,
        **kwargs: Any,
    ) -> Future[Any]:
        if not callable(func):
            raise TypeError("func must be callable")

        packet = TaskPacket(func, args, kwargs, callback, error, finalizer)
        _EV.emit("thread.create", Time.current_ticks, id(packet), getattr(func, "__name__", "task"))

        def _runner() -> Any:
            _EV.emit("thread.start", Time.current_ticks, id(packet), getattr(func, "__name__", "task"))
            try:
                result = packet.func(*packet.args, **packet.kwargs)
            except BaseException as exc:
                if packet.error:
                    self.call_soon(packet.error, exc)
                _EV.emit("thread.error", Time.current_ticks, id(packet), getattr(func, "__name__", "task"), exc)
                raise
            else:
                if packet.callback:
                    self.call_soon(packet.callback, result)
                _EV.emit("thread.end", Time.current_ticks, id(packet), getattr(func, "__name__", "task"))
                return result
            finally:
                if packet.finalizer:
                    self.call_soon(packet.finalizer)

        return self._executor.submit(_runner)

    def call_soon(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> None:
        if not callable(func):
            return

        def _invoke() -> Any:
            return func(*args, **kwargs)

        try:
            self._queue.put_nowait(_invoke)
        except queue.Full:
            if self.is_main_thread:
                _invoke()
            else:
                self._queue.put(_invoke)

    def repeat(
        self,
        interval: float,
        func: Callable[..., Any],
        *args: Any,
        daemon: bool = True,
        immediate: bool = False,
        **kwargs: Any,
    ) -> threading.Thread:
        if interval < 0:
            raise ValueError("interval must be >= 0")
        if not callable(func):
            raise TypeError("func must be callable")

        def _loop() -> None:
            if immediate:
                self.call_soon(func, *args, **kwargs)
            while self._alive:
                time.sleep(interval)
                if not self._alive:
                    break
                try:
                    self.submit(func, *args, **kwargs)
                except Exception:
                    pass

        thread = threading.Thread(target=_loop, daemon=daemon, name=f"PycePlusRepeat-{len(self._timers)+1}")
        with self._lock:
            self._timers.add(thread)
        thread.start()
        return thread

    def pump(self, limit: int | None = None) -> int:
        processed = 0
        while self._alive:
            if limit is not None and processed >= limit:
                break
            try:
                func = self._queue.get_nowait()
            except queue.Empty:
                break
            try:
                func()
            except Exception:
                import traceback
                traceback.print_exc()
            processed += 1
        return processed

    def shutdown(self, wait: bool = True) -> None:
        self._alive = False
        try:
            self._executor.shutdown(wait=wait, cancel_futures=not wait)
        except TypeError:
            self._executor.shutdown(wait=wait)

    def map(self, func: Callable[..., Any], iterable: Iterable[Any]) -> list[Future[Any]]:
        return [self.submit(func, item) for item in iterable]

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.shutdown(wait=False)


GLOBAL_TASKER = Tasker()
tasker = GLOBAL_TASKER


def submit(func: Callable[..., Any], *args: Any, **kwargs: Any) -> Future[Any]:
    return GLOBAL_TASKER.submit(func, *args, **kwargs)


def call_soon(func: Callable[..., Any], *args: Any, **kwargs: Any) -> None:
    GLOBAL_TASKER.call_soon(func, *args, **kwargs)


def pump(limit: int | None = None) -> int:
    return GLOBAL_TASKER.pump(limit=limit)


atexit.register(GLOBAL_TASKER.shutdown)
