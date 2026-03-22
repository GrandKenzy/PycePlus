# watch.py

import os
import sys
import hashlib
import __main__
from queue import Queue, Empty
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from PycePlus.CORE.timec import Time
from PycePlus import __events__ as _EV


MAX_HASH_SIZE = 5_000_000  


def _get_base_path():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)

    if hasattr(__main__, "__file__"):
        return os.path.dirname(os.path.abspath(__main__.__file__))

    return os.getcwd()


def _normalize_paths(base, paths, include_base):
    result = []

    if include_base:
        result.append(base)

    for p in paths:
        if not p:
            continue

        if not os.path.isabs(p):
            p = os.path.join(base, p)

        result.append(os.path.abspath(p))

    seen = set()
    unique = []
    for p in result:
        if p not in seen:
            seen.add(p)
            unique.append(p)

    return [p for p in unique if os.path.exists(p)]


def _fast_hash(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


class _EventHandler(FileSystemEventHandler):
    def __init__(self, queue):
        self.queue = queue
        self._cache = {}

    def _emit(self, name, data):
        try:
            self.queue.put_nowait(data)
        except:
            pass
        _EV.emit(name, data)

    def on_created(self, event):
        d = {
            "type": "created",
            "src": event.src_path,
            "is_dir": event.is_directory,
            "tick": Time.current_ticks
        }
        self._emit("file.created", d)

    def on_deleted(self, event):
        self._cache.pop(event.src_path, None)

        d = {
            "type": "deleted",
            "src": event.src_path,
            "is_dir": event.is_directory,
            "tick": Time.current_ticks
        }
        self._emit("file.deleted", d)

    def on_moved(self, event):
        self._cache.pop(event.src_path, None)

        d = {
            "type": "moved",
            "src": event.src_path,
            "dst": event.dest_path,
            "is_dir": event.is_directory,
            "tick": Time.current_ticks
        }
        self._emit("file.moved", d)

    def on_modified(self, event):
        if event.is_directory:
            return

        path = event.src_path

        try:
            stat = os.stat(path)
        except:
            return

        size = stat.st_size
        mtime = stat.st_mtime
        cached = self._cache.get(path)

        if cached and cached[0] == size and cached[1] == mtime:
            return

        # archivo grande → sin hash
        if size > MAX_HASH_SIZE:
            self._cache[path] = (size, mtime, None)

            d = {
                "type": "modified",
                "src": path,
                "is_dir": False,
                "size": size,
                "hash": None,
                "tick": Time.current_ticks
            }
            self._emit("file.modified", d)
            return

        try:
            h = _fast_hash(path)
        except:
            return

        if cached and cached[2] == h:
            return

        self._cache[path] = (size, mtime, h)

        d = {
            "type": "modified",
            "src": path,
            "is_dir": False,
            "size": size,
            "hash": h,
            "tick": Time.current_ticks
        }
        self._emit("file.modified", d)


class Watcher:
    def __init__(self, paths):
        self._queue = Queue(maxsize=10000)
        self._observer = Observer()
        self._handler = _EventHandler(self._queue)

        for path in paths:
            self._observer.schedule(self._handler, path, recursive=True)

        self._observer.start()

    def poll(self):
        events = []
        while True:
            try:
                events.append(self._queue.get_nowait())
            except Empty:
                break
        return events

    def stop(self):
        self._observer.stop()
        self._observer.join()


def init(flag="--main", *paths):
    if flag not in ("--main", "--nomain"):
        raise ValueError(f"Flag inválido: {flag}")

    base = _get_base_path()
    include_base = (flag == "--main")

    final_paths = _normalize_paths(base, paths, include_base)

    if not final_paths:
        final_paths = [base]

    return Watcher(final_paths)