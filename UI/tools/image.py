import io
import pygame
from PycePlus.CORE.tools.network import download
from PycePlus.CORE.tools.cache import IMG_Cache


IMAGE_CACHE = IMG_Cache(maxsize=200)
def load(source,
        size: tuple[int | None, int | None] | None = None,
        flips: tuple[bool, bool] = (False, False),
        convert: bool = True) -> pygame.Surface:

    if isinstance(source, str) and source.startswith(("http://", "https://")):
        result = download(source, asynchronous_mode=True).get(wait=True)
        source = result.data 

    return IMAGE_CACHE.load(
        source=source,
        size=size,
        flips=flips,
        convert=convert,
    )