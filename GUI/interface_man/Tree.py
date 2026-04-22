"""
PycePlus.GUI.interface_man.Tree
Thread-safe widget tree with page routing.
"""
from __future__ import annotations

import threading
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PycePlus.GUI.base import Base

_lock   = threading.RLock()
widgets: list["Base"] = []
Page    = "__main__"
Pages:  list[str] = ["__main__"]


def current_page() -> str:
    return Page


def set_page(page: str) -> None:
    global Page
    with _lock:
        Page = page
        if page not in Pages:
            Pages.append(page)


def page_exists(page: str) -> bool:
    return page in Pages


def next_page() -> None:
    with _lock:
        idx = Pages.index(Page)
        set_page(Pages[(idx + 1) % len(Pages)])


def previous_page() -> None:
    with _lock:
        idx = Pages.index(Page)
        set_page(Pages[(idx - 1) % len(Pages)])


def get_pages() -> list[str]:
    return list(Pages)


def put(widget: "Base") -> None:
    """Register a root-level widget."""
    with _lock:
        if widget not in widgets:
            widgets.append(widget)


def remove(widget: "Base") -> None:
    """Remove a widget from the tree entirely."""
    with _lock:
        if widget in widgets:
            widgets.remove(widget)


def nav(root: str) -> "Base | None":
    """Navigate the widget tree by slash-delimited path. E.g. 'frame/button'."""
    with _lock:
        parts = root.split("/")
        pool  = list(widgets)

        for part in parts:
            found = None
            for w in pool:
                if w.name == part:
                    found = w
                    pool  = w.get_childrens() if w.is_container() else []
                    break
            if found is None:
                return None
        return found


def get_all_flat() -> list["Base"]:
    """Return every widget in the tree (depth-first) as a flat list."""
    result: list["Base"] = []
    with _lock:
        stack = list(widgets)
    while stack:
        w = stack.pop()
        result.append(w)
        if w.is_container():
            stack.extend(w.get_childrens())
    return result
