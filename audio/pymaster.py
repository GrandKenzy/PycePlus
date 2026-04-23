"""
PycePlus.audio.pymaster
=======================
PyMaster — Mezclador de audio completo basado en pygame.mixer.

Características:
  - Múltiples canales con volumen y paneo independiente
  - Cola de reproducción (playlist)
  - Efectos: fade-in/out, loop, delay
  - Grupos de canales (bus)
  - Eventos al terminar una pista
  - Precarga de sonidos en caché
  - Control de volumen maestro
  - Monitoreo de picos (VU meter)

Uso:
    from PycePlus.audio.pymaster import PyMaster

    master = PyMaster(channels=16, frequency=44100, buffer=512)

    # Sonido simple
    sfx_id = master.load("explosion.wav", name="explosion")
    master.play("explosion")

    # Música con fade
    master.music_load("bgm.ogg")
    master.music_play(loops=-1, fadein_ms=2000)

    # Canal con volumen/paneo
    ch = master.channel(0)
    ch.set_volume(0.8)
    ch.set_panning(left=0.3, right=1.0)

    master.stop_all()
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import pygame
import pygame.mixer as _mixer

__all__ = ["PyMaster", "SoundChannel", "SoundBus"]


# ──────────────────────────────────────────────────────────────────────────────
# SoundChannel
# ──────────────────────────────────────────────────────────────────────────────

class SoundChannel:
    """
    Envuelve un pygame.mixer.Channel con controles extendidos.
    """

    def __init__(self, index: int, channel: pygame.mixer.Channel):
        self._index   = index
        self._ch      = channel
        self._volume  = 1.0
        self._panning = (1.0, 1.0)   # (left, right)
        self._bus: "SoundBus | None" = None
        self._on_end: Callable | None = None

    @property
    def index(self) -> int:
        return self._index

    @property
    def is_busy(self) -> bool:
        return self._ch.get_busy()

    # ── volume / panning ──────────────────────────────────────────────────

    def set_volume(self, volume: float) -> "SoundChannel":
        self._volume = max(0.0, min(1.0, volume))
        self._apply_volume()
        return self

    def set_panning(self, left: float = 1.0, right: float = 1.0) -> "SoundChannel":
        self._panning = (max(0.0, min(1.0, left)), max(0.0, min(1.0, right)))
        self._apply_volume()
        return self

    def _apply_volume(self) -> None:
        bus_vol = self._bus._volume if self._bus else 1.0
        l = self._panning[0] * self._volume * bus_vol
        r = self._panning[1] * self._volume * bus_vol
        self._ch.set_volume(max(0.0, min(1.0, l)), max(0.0, min(1.0, r)))

    # ── playback ──────────────────────────────────────────────────────────

    def play(
        self,
        sound: pygame.mixer.Sound,
        loops: int = 0,
        maxtime: int = 0,
        fade_ms: int = 0,
    ) -> "SoundChannel":
        self._ch.play(sound, loops=loops, maxtime=maxtime, fade_ms=fade_ms)
        self._apply_volume()
        return self

    def stop(self) -> "SoundChannel":
        self._ch.stop()
        return self

    def pause(self) -> "SoundChannel":
        self._ch.pause()
        return self

    def unpause(self) -> "SoundChannel":
        self._ch.unpause()
        return self

    def fadeout(self, ms: int) -> "SoundChannel":
        self._ch.fadeout(ms)
        return self

    def on_end(self, cb: Callable | None) -> "SoundChannel":
        self._on_end = cb
        if cb:
            self._ch.set_endevent(pygame.USEREVENT + self._index + 1)
        return self


# ──────────────────────────────────────────────────────────────────────────────
# SoundBus
# ──────────────────────────────────────────────────────────────────────────────

class SoundBus:
    """
    Grupo de canales con volumen compartido (bus de mezcla).
    """

    def __init__(self, name: str, channels: list[SoundChannel]):
        self.name     = name
        self._channels= channels
        self._volume  = 1.0
        for ch in channels:
            ch._bus = self

    def set_volume(self, volume: float) -> "SoundBus":
        self._volume = max(0.0, min(1.0, volume))
        for ch in self._channels:
            ch._apply_volume()
        return self

    @property
    def volume(self) -> float:
        return self._volume

    def stop_all(self) -> "SoundBus":
        for ch in self._channels:
            ch.stop()
        return self

    def pause_all(self) -> "SoundBus":
        for ch in self._channels:
            ch.pause()
        return self

    def unpause_all(self) -> "SoundBus":
        for ch in self._channels:
            ch.unpause()
        return self


# ──────────────────────────────────────────────────────────────────────────────
# PyMaster
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class _PlaylistEntry:
    path: str
    loops: int = 0
    fadein_ms: int = 0
    volume: float = 1.0


class PyMaster:
    """
    Mezclador de audio principal basado en pygame.mixer.

    Parameters
    ----------
    channels   : número total de canales de mezcla
    frequency  : frecuencia de muestreo (Hz)
    size       : tamaño de muestra en bits (−16 = 16-bit signed)
    stereo     : True = estéreo, False = mono
    buffer     : tamaño del buffer (samples)
    """

    def __init__(
        self,
        channels:  int   = 16,
        frequency: int   = 44100,
        size:      int   = -16,
        stereo:    bool  = True,
        buffer:    int   = 512,
    ):
        if not pygame.get_init():
            pygame.init()

        if not _mixer.get_init():
            try:
                _mixer.init(frequency=frequency, size=size,
                            channels=2 if stereo else 1, buffer=buffer)
            except pygame.error:
                _mixer.init()

        _mixer.set_num_channels(channels)

        self._num_channels = channels
        self._channels: list[SoundChannel] = []
        for i in range(channels):
            self._channels.append(SoundChannel(i, _mixer.Channel(i)))

        self._cache: dict[str, pygame.mixer.Sound] = {}   # name → Sound
        self._name_map: dict[str, str]             = {}   # name → path
        self._master_volume = 1.0

        # Playlist
        self._playlist: list[_PlaylistEntry] = []
        self._playlist_pos  = 0
        self._playlist_mode = False

        # Buses
        self._buses: dict[str, SoundBus] = {}

        # Background thread for VU metering
        self._peak: tuple[float, float] = (0.0, 0.0)
        self._peak_lock = threading.Lock()
        self._running = True
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()

        # Music events
        _mixer.music.set_endevent(pygame.USEREVENT)

    # ── Sound cache ────────────────────────────────────────────────────────

    def load(self, path: str | Path, name: str | None = None) -> str:
        """
        Carga un archivo de audio en la caché.

        Returns: name (clave para play())
        """
        path = str(path)
        key  = name or Path(path).stem
        if key not in self._cache:
            self._cache[key]   = _mixer.Sound(path)
            self._name_map[key] = path
        return key

    def unload(self, name: str) -> None:
        self._cache.pop(name, None)
        self._name_map.pop(name, None)

    def preload(self, paths: list[str | Path]) -> None:
        """Precarga una lista de archivos en background."""
        def _work():
            for p in paths:
                self.load(str(p))
        threading.Thread(target=_work, daemon=True).start()

    # ── Channel management ─────────────────────────────────────────────────

    def channel(self, index: int) -> SoundChannel:
        return self._channels[index % self._num_channels]

    def free_channel(self) -> SoundChannel | None:
        """Devuelve el primer canal libre."""
        for ch in self._channels:
            if not ch.is_busy:
                return ch
        return None

    def create_bus(self, name: str, channel_indices: list[int]) -> SoundBus:
        chans = [self._channels[i % self._num_channels] for i in channel_indices]
        bus   = SoundBus(name, chans)
        self._buses[name] = bus
        return bus

    def bus(self, name: str) -> SoundBus | None:
        return self._buses.get(name)

    # ── Playback ───────────────────────────────────────────────────────────

    def play(
        self,
        name:     str,
        loops:    int  = 0,
        channel:  int  = -1,
        volume:   float = 1.0,
        fade_ms:  int  = 0,
        panning:  tuple[float, float] = (1.0, 1.0),
    ) -> SoundChannel | None:
        """
        Reproduce un sonido cargado previamente con load().

        Parameters
        ----------
        name     : clave devuelta por load()
        loops    : 0 = una vez, -1 = infinito
        channel  : índice de canal (-1 = auto)
        volume   : 0.0–1.0
        fade_ms  : fade-in en ms
        panning  : (left, right) 0.0–1.0
        """
        sound = self._cache.get(name)
        if sound is None:
            return None

        if channel >= 0:
            ch = self._channels[channel % self._num_channels]
        else:
            ch = self.free_channel()
            if ch is None:
                ch = self._channels[0]  # steal first channel

        ch.set_volume(volume * self._master_volume)
        ch.set_panning(*panning)
        ch.play(sound, loops=loops, fade_ms=fade_ms)
        return ch

    def stop_all(self) -> None:
        for ch in self._channels:
            ch.stop()

    def pause_all(self) -> None:
        _mixer.pause()

    def unpause_all(self) -> None:
        _mixer.unpause()

    # ── Master volume ──────────────────────────────────────────────────────

    @property
    def master_volume(self) -> float:
        return self._master_volume

    @master_volume.setter
    def master_volume(self, v: float) -> None:
        self._master_volume = max(0.0, min(1.0, v))
        _mixer.music.set_volume(self._master_volume)

    def fade_master(self, target: float, duration_s: float) -> None:
        """Fade suave del volumen maestro en un hilo separado."""
        def _fade():
            steps  = max(1, int(duration_s * 60))
            delta  = (target - self._master_volume) / steps
            for _ in range(steps):
                self.master_volume = self._master_volume + delta
                time.sleep(duration_s / steps)
            self.master_volume = target
        threading.Thread(target=_fade, daemon=True).start()

    # ── Music (streaming) ──────────────────────────────────────────────────

    def music_load(self, path: str | Path) -> None:
        _mixer.music.load(str(path))

    def music_play(
        self,
        loops:    int  = 0,
        start:    float = 0.0,
        fadein_ms: int = 0,
    ) -> None:
        _mixer.music.play(loops=loops, start=start, fade_ms=fadein_ms)
        _mixer.music.set_volume(self._master_volume)

    def music_pause(self) -> None:
        _mixer.music.pause()

    def music_unpause(self) -> None:
        _mixer.music.unpause()

    def music_stop(self, fadeout_ms: int = 0) -> None:
        if fadeout_ms > 0:
            _mixer.music.fadeout(fadeout_ms)
        else:
            _mixer.music.stop()

    def music_position(self) -> float:
        return _mixer.music.get_pos() / 1000.0

    def music_set_position(self, seconds: float) -> None:
        _mixer.music.set_pos(seconds)

    def music_is_playing(self) -> bool:
        return _mixer.music.get_busy()

    def music_volume(self, v: float) -> None:
        _mixer.music.set_volume(max(0.0, min(1.0, v)))

    # ── Playlist ───────────────────────────────────────────────────────────

    def playlist_clear(self) -> None:
        self._playlist.clear()
        self._playlist_pos = 0

    def playlist_add(
        self,
        path:     str,
        loops:    int   = 0,
        fadein_ms:int   = 0,
        volume:   float = 1.0,
    ) -> None:
        self._playlist.append(_PlaylistEntry(path, loops, fadein_ms, volume))

    def playlist_play(self, index: int = 0) -> None:
        if not self._playlist:
            return
        self._playlist_pos  = index % len(self._playlist)
        self._playlist_mode = True
        self._play_playlist_entry(self._playlist_pos)

    def _play_playlist_entry(self, index: int) -> None:
        entry = self._playlist[index]
        self.music_load(entry.path)
        self.music_play(loops=entry.loops, fadein_ms=entry.fadein_ms)
        _mixer.music.set_volume(entry.volume * self._master_volume)

    def playlist_next(self) -> None:
        if not self._playlist:
            return
        self._playlist_pos = (self._playlist_pos + 1) % len(self._playlist)
        self._play_playlist_entry(self._playlist_pos)

    def playlist_prev(self) -> None:
        if not self._playlist:
            return
        self._playlist_pos = (self._playlist_pos - 1) % len(self._playlist)
        self._play_playlist_entry(self._playlist_pos)

    def handle_event(self, event: pygame.event.Event) -> None:
        """
        Pasar los eventos de pygame aquí para manejar fin de música, etc.
        Ejemplo: master.handle_event(event) en el loop principal.
        """
        if self._playlist_mode and event.type == pygame.USEREVENT:
            self.playlist_next()

    # ── VU Metering ────────────────────────────────────────────────────────

    def _monitor_loop(self) -> None:
        while self._running:
            try:
                arr = _mixer.get_array()
                if arr is not None and len(arr):
                    import numpy as np
                    a = np.frombuffer(arr, dtype=np.int16).astype(np.float32)
                    peak = float(np.max(np.abs(a))) / 32768.0
                    with self._peak_lock:
                        # Stereo: left / right (simplificado como mono)
                        self._peak = (peak, peak)
            except Exception:
                pass
            time.sleep(0.05)

    @property
    def peak_level(self) -> tuple[float, float]:
        """Nivel de pico (left, right) 0.0–1.0 para VU meter."""
        with self._peak_lock:
            return self._peak

    # ── Cleanup ────────────────────────────────────────────────────────────

    def quit(self) -> None:
        self._running = False
        _mixer.music.stop()
        _mixer.stop()

    def __del__(self):
        try:
            self.quit()
        except Exception:
            pass