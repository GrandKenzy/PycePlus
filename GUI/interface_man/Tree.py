from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from PycePlus.UI.window import Window
    from PycePlus.GUI.base import Base


widgets: list[Base] = []
Page: str = '__main__'
Pages: list[str] = []


def current_page():
    global Page
    return Page

def set_page(page: str):
    global Pages, Page
    Page = page
    if not page in Pages:
        Pages.append(page)
        
def page_exists(page: str) -> bool:
    global Pages
    return page in Pages

def next_page(page: str):
    global Pages
    index = Pages.index(page)
    if index + 1 < len(Pages):
        return set_page(Pages[index + 1])
    else:
        return set_page(Pages[0])
    
    
def previous_page(page: str):
    global Pages
    index = Pages.index(page)
    if index - 1 >= 0:
        return set_page(Pages[index - 1])
    else:
        return set_page(Pages[-1])

def get_pages():
    global Pages
    return Pages


# tree widgets management
def put(widget: Base):
    global widgets
    if widget.is_father_widget(): raise ValueError("Widget already has a father widget") 
    widgets.append(widget)
    
def nav(root: str):
    global widgets
    
    parts = root.split('/')
    
    first_part = parts[0]
    parts = parts[1:]
    
    def recursive_search(childrens: list[Base], first_part: str, parts: list[str]) -> 'Base | None':
        for child in childrens:
            if child.name == first_part:
                if parts and not child.is_container():
                    raise Exception(f'{child.name} is not a container')
                    
                return recursive_search(child.get_childrens(), parts[0], parts[1:])
        return None
    
    for widget in widgets:
        if widget.name == first_part:    
            if parts and not widget.is_container():
                raise Exception(f'{widget.name} is not a container')
            return recursive_search(widget.get_childrens(), parts[0], parts[1:])
        
    return None

    
    
    