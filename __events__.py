"""
PycePlus.__events__
Thread-safe global event bus for system and application-level events.

New channels added:
  • system.window.resized / moved / minimized / maximized / restored / close
  • file.drop / text.drop
  • widget.focus / widget.blur  (fired by render layer)
  • app.page.change
"""
from __future__ import annotations

import threading
from itertools import count
from typing import Any, Callable, Literal

# ──────────────────────────────────────────────────────────────────────────────
# Event registry
# ──────────────────────────────────────────────────────────────────────────────

BLOCKS: dict[int, dict[str, Any]] = {
    # ── system ──────────────────────────────────────────────────────────────
    0:  {"name": "system.start",              "calls": {}, "lock": threading.Lock()},
    1:  {"name": "system.shutdown",           "calls": {}, "lock": threading.Lock()},
    2:  {"name": "system.suspend",            "calls": {}, "lock": threading.Lock()},
    3:  {"name": "system.resume",             "calls": {}, "lock": threading.Lock()},
    4:  {"name": "system.error",              "calls": {}, "lock": threading.Lock()},
    5:  {"name": "system.idle",               "calls": {}, "lock": threading.Lock()},
    # ── network ─────────────────────────────────────────────────────────────
    6:  {"name": "network.error",             "calls": {}, "lock": threading.Lock()},
    7:  {"name": "network.connect",           "calls": {}, "lock": threading.Lock()},
    8:  {"name": "network.disconnect",        "calls": {}, "lock": threading.Lock()},
    9:  {"name": "network.receive",           "calls": {}, "lock": threading.Lock()},
    10: {"name": "network.send",              "calls": {}, "lock": threading.Lock()},
    11: {"name": "network.failed",            "calls": {}, "lock": threading.Lock()},
    12: {"name": "network.connectionError",   "calls": {}, "lock": threading.Lock()},
    # ── database ────────────────────────────────────────────────────────────
    13: {"name": "database.error",            "calls": {}, "lock": threading.Lock()},
    14: {"name": "database.connect",          "calls": {}, "lock": threading.Lock()},
    15: {"name": "database.disconnect",       "calls": {}, "lock": threading.Lock()},
    16: {"name": "database.receive",          "calls": {}, "lock": threading.Lock()},
    17: {"name": "database.send",             "calls": {}, "lock": threading.Lock()},
    18: {"name": "database.failed",           "calls": {}, "lock": threading.Lock()},
    # ── file system ─────────────────────────────────────────────────────────
    19: {"name": "file.opened",               "calls": {}, "lock": threading.Lock()},
    20: {"name": "file.closed",               "calls": {}, "lock": threading.Lock()},
    21: {"name": "file.modified",             "calls": {}, "lock": threading.Lock()},
    22: {"name": "file.created",              "calls": {}, "lock": threading.Lock()},
    23: {"name": "file.deleted",              "calls": {}, "lock": threading.Lock()},
    # ── gui ─────────────────────────────────────────────────────────────────
    24: {"name": "system.gui.fatigue",        "calls": {}, "lock": threading.Lock()},
    # ── memory ──────────────────────────────────────────────────────────────
    25: {"name": "memory.system.change",      "calls": {}, "lock": threading.Lock()},
    26: {"name": "memory.process.change",     "calls": {}, "lock": threading.Lock()},
    27: {"name": "memory.low",                "calls": {}, "lock": threading.Lock()},
    # ── disk ────────────────────────────────────────────────────────────────
    28: {"name": "disk.system.change",        "calls": {}, "lock": threading.Lock()},
    29: {"name": "disk.process.change",       "calls": {}, "lock": threading.Lock()},
    30: {"name": "disk.low",                  "calls": {}, "lock": threading.Lock()},
    # ── threads ─────────────────────────────────────────────────────────────
    31: {"name": "thread.create",             "calls": {}, "lock": threading.Lock()},
    32: {"name": "thread.start",              "calls": {}, "lock": threading.Lock()},
    33: {"name": "thread.end",               "calls": {}, "lock": threading.Lock()},
    34: {"name": "thread.error",              "calls": {}, "lock": threading.Lock()},
    # ── network client ──────────────────────────────────────────────────────
    35: {"name": "network.client.start",      "calls": {}, "lock": threading.Lock()},
    36: {"name": "network.client.progress",   "calls": {}, "lock": threading.Lock()},
    37: {"name": "network.client.end",        "calls": {}, "lock": threading.Lock()},
    38: {"name": "network.client.paused",     "calls": {}, "lock": threading.Lock()},
    39: {"name": "network.client.resume",     "calls": {}, "lock": threading.Lock()},
    40: {"name": "network.client.canceled",   "calls": {}, "lock": threading.Lock()},
    41: {"name": "network.reconnect",         "calls": {}, "lock": threading.Lock()},
    # ── window ──────────────────────────────────────────────────────────────
    42: {"name": "system.window.lost",        "calls": {}, "lock": threading.Lock()},
    43: {"name": "system.window.gained",      "calls": {}, "lock": threading.Lock()},
    44: {"name": "system.window.resized",     "calls": {}, "lock": threading.Lock()},
    45: {"name": "system.window.moved",       "calls": {}, "lock": threading.Lock()},
    46: {"name": "system.window.minimized",   "calls": {}, "lock": threading.Lock()},
    47: {"name": "system.window.maximized",   "calls": {}, "lock": threading.Lock()},
    48: {"name": "system.window.restored",    "calls": {}, "lock": threading.Lock()},
    49: {"name": "system.window.close",       "calls": {}, "lock": threading.Lock()},
    # ── drag & drop ─────────────────────────────────────────────────────────
    50: {"name": "file.drop",                 "calls": {}, "lock": threading.Lock()},
    51: {"name": "text.drop",                 "calls": {}, "lock": threading.Lock()},
    # ── widget ──────────────────────────────────────────────────────────────
    52: {"name": "widget.focus",              "calls": {}, "lock": threading.Lock()},
    53: {"name": "widget.blur",               "calls": {}, "lock": threading.Lock()},
    54: {"name": "widget.created",            "calls": {}, "lock": threading.Lock()},
    55: {"name": "widget.destroyed",          "calls": {}, "lock": threading.Lock()},
    # ── app ─────────────────────────────────────────────────────────────────
    56: {"name": "app.page.change",           "calls": {}, "lock": threading.Lock()},
    57: {"name": "app.ready",                 "calls": {}, "lock": threading.Lock()},
}

CORE_EVENTS = Literal[
    "system.start", "system.shutdown", "system.suspend", "system.resume",
    "system.error", "system.idle",
    "network.error", "network.connect", "network.disconnect",
    "network.receive", "network.send", "network.failed", "network.connectionError",
    "database.error", "database.connect", "database.disconnect",
    "database.receive", "database.send", "database.failed",
    "file.opened", "file.closed", "file.modified", "file.created", "file.deleted",
    "system.gui.fatigue",
    "memory.system.change", "memory.process.change", "memory.low",
    "disk.system.change", "disk.process.change", "disk.low",
    "thread.create", "thread.start", "thread.end", "thread.error",
    "network.client.start", "network.client.progress", "network.client.end",
    "network.client.paused", "network.client.resume", "network.client.canceled",
    "network.reconnect",
    "system.window.lost", "system.window.gained",
    "system.window.resized", "system.window.moved",
    "system.window.minimized", "system.window.maximized",
    "system.window.restored", "system.window.close",
    "file.drop", "text.drop",
    "widget.focus", "widget.blur", "widget.created", "widget.destroyed",
    "app.page.change", "app.ready",
]

_NAME_TO_ID: dict[str, int] = {v["name"]: k for k, v in BLOCKS.items()}
_id_gen = count()

# ──────────────────────────────────────────────────────────────────────────────
# API
# ──────────────────────────────────────────────────────────────────────────────

def _get_id(event: str | int) -> int:
    if isinstance(event, int):
        return event
    if event not in _NAME_TO_ID:
        raise KeyError(f"Unknown event: {event!r}")
    return _NAME_TO_ID[event]


def emit(event: CORE_EVENTS | int | str, *args: Any, **kwargs: Any) -> None:
    eid   = _get_id(event)
    block = BLOCKS[eid]
    with block["lock"]:
        calls = tuple(block["calls"].values())
    for fn in calls:
        try:
            fn(*args, **kwargs)
        except Exception as e:
            if eid != _NAME_TO_ID.get("system.error", -1):
                try:
                    emit("system.error", e)
                except Exception:
                    pass


def register_event(event: CORE_EVENTS | int | str,
                   on_event: Callable[..., None]) -> int:
    eid   = _get_id(event)
    block = BLOCKS[eid]
    cid   = next(_id_gen)
    with block["lock"]:
        block["calls"][cid] = on_event
    return cid


def unregister_event(event: CORE_EVENTS | int | str,
                     on_event: Callable[..., None]) -> None:
    eid   = _get_id(event)
    block = BLOCKS[eid]
    with block["lock"]:
        calls = block["calls"]
        for k, v in list(calls.items()):
            if v is on_event:
                del calls[k]
                break


def unregister_by_index(event: CORE_EVENTS | int | str, index: int) -> None:
    eid   = _get_id(event)
    block = BLOCKS[eid]
    with block["lock"]:
        block["calls"].pop(index, None)


def clear_block(event: CORE_EVENTS | int | str) -> None:
    eid   = _get_id(event)
    block = BLOCKS[eid]
    with block["lock"]:
        block["calls"].clear()


def has_listeners(event: CORE_EVENTS | int | str) -> bool:
    eid   = _get_id(event)
    block = BLOCKS[eid]
    with block["lock"]:
        return bool(block["calls"])
