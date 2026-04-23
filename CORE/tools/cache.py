from __future__ import annotations

import io
import threading
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Generic, TypeVar
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

import pygame

K = TypeVar("K")
V = TypeVar("V")


@dataclass(slots=True)
class CacheStats:
    maxsize: int
    size: int
    hits: int
    misses: int
    puts: int
    evictions: int


class LRUCache(Generic[K, V]):
    """
    Caché LRU genérica, thread-safe.

    Métodos principales:
      - get(key)
      - put(key, value)
      - get_or_set(key, factory)
      - invalidate(key)
      - clear()
      - resize(maxsize)
      - stats()
    """

    def __init__(self, maxsize: int = 128):
        if maxsize <= 0:
            raise ValueError("maxsize debe ser mayor que 0")

        self._maxsize = int(maxsize)
        self._store: OrderedDict[K, V] = OrderedDict()
        self._lock = threading.RLock()

        self._hits = 0
        self._misses = 0
        self._puts = 0
        self._evictions = 0

    @property
    def maxsize(self) -> int:
        return self._maxsize

    @property
    def size(self) -> int:
        with self._lock:
            return len(self._store)

    def __len__(self) -> int:
        return self.size

    def __contains__(self, key: K) -> bool:
        with self._lock:
            return key in self._store

    def keys(self):
        with self._lock:
            return list(self._store.keys())

    def values(self):
        with self._lock:
            return list(self._store.values())

    def items(self):
        with self._lock:
            return list(self._store.items())

    def peek(self, key: K, default: Any = None) -> V | Any:
        """
        Lee sin mover al final del LRU.
        """
        with self._lock:
            return self._store.get(key, default)

    def get(self, key: K, default: Any = None) -> V | Any:
        """
        Obtiene y marca como usado.
        """
        with self._lock:
            if key not in self._store:
                self._misses += 1
                return default

            self._hits += 1
            value = self._store.pop(key)
            self._store[key] = value
            return value

    def put(self, key: K, value: V) -> V:
        """
        Inserta o actualiza y marca como usado.
        """
        with self._lock:
            self._puts += 1

            if key in self._store:
                self._store.pop(key)

            self._store[key] = value
            self._evict_if_needed()
            return value

    def set(self, key: K, value: V) -> V:
        return self.put(key, value)

    def get_or_set(self, key: K, factory: Callable[[], V]) -> V:
        """
        Obtiene de caché o crea con factory si no existe.
        """
        with self._lock:
            if key in self._store:
                self._hits += 1
                value = self._store.pop(key)
                self._store[key] = value
                return value

            self._misses += 1

        value = factory()
        with self._lock:
            self._puts += 1
            self._store[key] = value
            self._evict_if_needed()
            return value

    def invalidate(self, key: K | None = None) -> None:
        with self._lock:
            if key is None:
                self._store.clear()
                return
            self._store.pop(key, None)

    def remove(self, key: K) -> V | None:
        with self._lock:
            return self._store.pop(key, None)

    def clear(self) -> None:
        self.invalidate(None)

    def resize(self, maxsize: int) -> None:
        if maxsize <= 0:
            raise ValueError("maxsize debe ser mayor que 0")

        with self._lock:
            self._maxsize = int(maxsize)
            self._evict_if_needed()

    def stats(self) -> CacheStats:
        with self._lock:
            return CacheStats(
                maxsize=self._maxsize,
                size=len(self._store),
                hits=self._hits,
                misses=self._misses,
                puts=self._puts,
                evictions=self._evictions,
            )

    def _evict_if_needed(self) -> None:
        while len(self._store) > self._maxsize:
            self._store.popitem(last=False)
            self._evictions += 1
            
            
class IMG_Cache(LRUCache[str, pygame.Surface]):
    """
    Caché LRU para imágenes de pygame-ce.

    Soporta:
      - path local
      - URL
      - pygame.Surface
      - bytes / bytearray / memoryview

    Métodos:
      - load(source, size=..., flips=..., convert=True)
      - invalidate(path)
      - clear()
      - stats()
    """

    def __init__(self, maxsize: int = 128):
        super().__init__(maxsize=maxsize)

    @staticmethod
    def _is_url(text: str) -> bool:
        return text.startswith(("http://", "https://"))

    @staticmethod
    def _url_key(url: str) -> str:
        return f"url:{url}"

    @staticmethod
    def _path_key(path: str | Path) -> str:
        return f"path:{Path(path).resolve().as_posix()}"

    @staticmethod
    def _surface_key(surface: pygame.Surface) -> str:
        return f"surf:{id(surface)}"

    @staticmethod
    def _bytes_key(data: bytes) -> str:
        return f"bytes:{hash(data)}"

    @staticmethod
    def _fetch_url(url: str, timeout: float = 15.0) -> bytes:
        req = Request(
            url,
            headers={
                "User-Agent": "PycePlus/3.0",
                "Accept": "*/*",
            },
        )
        with urlopen(req, timeout=timeout) as response:
            return response.read()

    def _load_surface_from_source(self, source: Any, timeout: float = 15.0) -> tuple[str, pygame.Surface]:
        """
        Devuelve (cache_key, surface_base).
        """
        if isinstance(source, pygame.Surface):
            key = self._surface_key(source)
            return key, source.copy()

        if isinstance(source, (bytes, bytearray, memoryview)):
            data = bytes(source)
            key = self._bytes_key(data)
            surf = pygame.image.load(io.BytesIO(data))
            return key, surf

        if isinstance(source, (str, Path)):
            text = str(source)

            if self._is_url(text):
                key = self._url_key(text)
                data = self._fetch_url(text, timeout=timeout)
                surf = pygame.image.load(io.BytesIO(data))
                return key, surf

            path = Path(text)
            key = self._path_key(path)
            surf = pygame.image.load(str(path))
            return key, surf

        raise TypeError(f"Tipo de source no soportado: {type(source)!r}")


    def load(
        self,
        source: Any,
        size: tuple[int | None, int | None] | None = None,
        flips: tuple[bool, bool] = (False, False),
        convert: bool = True,
        timeout: float = 15.0,
        use_cache: bool = True,
    ) -> pygame.Surface:

        base_key, base_surf = self._load_surface_from_source(source, timeout=timeout)

        final_size = size

        if size is not None and (size[0] is None or size[1] is None):
            orig_w, orig_h = base_surf.get_size()
            w, h = size

            if w is None and h is None:
                final_size = None

            elif w is None:
                ratio = h / orig_h
                final_size = (int(orig_w * ratio), h)

            elif h is None:
                ratio = w / orig_w
                final_size = (w, int(orig_h * ratio))

        final_key = f"{base_key}|size={final_size}|flip={flips}|convert={convert}"

        if use_cache:
            cached = self.get(final_key)
            if cached is not None:
                return cached

        surf = base_surf

        if convert:
            if surf.get_alpha() is not None:
                surf = surf.convert_alpha()
            else:
                surf = surf.convert()

        if final_size is not None:
            surf = pygame.transform.smoothscale(surf, final_size)

        if flips != (False, False):
            surf = pygame.transform.flip(surf, flips[0], flips[1])

        if use_cache:
            self.put(final_key, surf)

        return surf

    def preload(
        self,
        source: Any,
        size: tuple[int, int] | None = None,
        flips: tuple[bool, bool] = (False, False),
        convert: bool = True,
        timeout: float = 15.0,
    ) -> pygame.Surface:
        return self.load(
            source=source,
            size=size,
            flips=flips,
            convert=convert,
            timeout=timeout,
            use_cache=True,
        )

    def unload(self, source: Any, size: tuple[int, int] | None = None, flips: tuple[bool, bool] = (False, False), convert: bool = True) -> None:
        if isinstance(source, pygame.Surface):
            base_key = self._surface_key(source)
        elif isinstance(source, (bytes, bytearray, memoryview)):
            base_key = self._bytes_key(bytes(source))
        elif isinstance(source, (str, Path)):
            text = str(source)
            base_key = self._url_key(text) if self._is_url(text) else self._path_key(text)
        else:
            raise TypeError(f"Tipo de source no soportado: {type(source)!r}")

        final_key = f"{base_key}|size={size}|flip={flips}|convert={convert}"
        self.invalidate(final_key)

    def purge_source(self, source: Any) -> None:
        """
        Elimina todas las variantes derivadas de un mismo source.
        """
        if isinstance(source, pygame.Surface):
            base_key = self._surface_key(source)
        elif isinstance(source, (bytes, bytearray, memoryview)):
            base_key = self._bytes_key(bytes(source))
        elif isinstance(source, (str, Path)):
            text = str(source)
            base_key = self._url_key(text) if self._is_url(text) else self._path_key(text)
        else:
            raise TypeError(f"Tipo de source no soportado: {type(source)!r}")

        prefix = f"{base_key}|"
        with self._lock:
            for key in list(self._store.keys()):
                if key == base_key or key.startswith(prefix):
                    self._store.pop(key, None)