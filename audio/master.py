"""
PycePlus.audio.master
=====================
Master — Mezclador de audio completo basado en FFmpeg + PyAudio/sounddevice.

Usa ffmpeg para decodificar cualquier formato de audio y sounddevice
(o PyAudio como fallback) para reproducción de alta calidad.

Características:
  - Reproduce CUALQUIER formato que soporte ffmpeg (mp3, ogg, flac, aac…)
  - Crossfade entre pistas
  - Pitch shifting y time stretching via ffmpeg filters
  - Efectos de audio: reverb, echo, equalizer, compressor
  - Análisis de forma de onda (waveform) y espectro (FFT)
  - Grabación de audio
  - Exportación de segmentos
  - Hilo de reproducción dedicado con buffer circular

Uso:
    from PycePlus.audio.master import Master

    m = Master()
    m.play("cancion.mp3")
    m.set_volume(0.7)
    m.effect("equalizer", bass=+6, treble=-2)
    m.crossfade("siguiente.mp3", duration_s=3.0)

    waveform = m.get_waveform("audio.mp3")
    fft      = m.get_spectrum("audio.mp3")
"""
from __future__ import annotations

import io
import os
import queue
import shutil
import subprocess
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Literal

__all__ = ["Master", "MasterTrack", "AudioEffect"]


# ──────────────────────────────────────────────────────────────────────────────
# Detección de dependencias
# ──────────────────────────────────────────────────────────────────────────────

def _has_ffmpeg() -> bool:
    return shutil.which("ffmpeg") is not None

def _has_ffprobe() -> bool:
    return shutil.which("ffprobe") is not None

def _import_audio_backend():
    """Devuelve (module, backend_name) para el primer backend disponible."""
    try:
        import sounddevice as sd
        return sd, "sounddevice"
    except ImportError:
        pass
    try:
        import pyaudio
        return pyaudio, "pyaudio"
    except ImportError:
        pass
    return None, "none"


# ──────────────────────────────────────────────────────────────────────────────
# Decodificación FFmpeg
# ──────────────────────────────────────────────────────────────────────────────

_SAMPLE_RATE  = 44100
_CHANNELS     = 2
_SAMPLE_WIDTH = 2     # int16 = 2 bytes


def _ffmpeg_decode(
    path: str,
    rate:    int  = _SAMPLE_RATE,
    channels:int  = _CHANNELS,
    start_s: float = 0.0,
    duration_s: float | None = None,
    filters: str | None = None,
) -> bytes:
    """
    Decodifica audio a PCM crudo (int16 little-endian) usando ffmpeg.

    Args:
        path       : ruta al archivo
        rate       : frecuencia de muestreo deseada
        channels   : canales de salida (1=mono, 2=estéreo)
        start_s    : segundo de inicio
        duration_s : duración máxima en segundos
        filters    : cadena de filtros ffmpeg (-af ...) ej: "equalizer=f=100:width_type=o:width=2:g=6"

    Returns:
        bytes PCM int16 little-endian
    """
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "quiet"]

    if start_s > 0:
        cmd += ["-ss", str(start_s)]
    if duration_s is not None:
        cmd += ["-t", str(duration_s)]

    cmd += ["-i", path]

    if filters:
        cmd += ["-af", filters]

    cmd += [
        "-f",  "s16le",
        "-ac", str(channels),
        "-ar", str(rate),
        "pipe:1",
    ]

    result = subprocess.run(cmd, capture_output=True)
    return result.stdout


def _ffprobe_info(path: str) -> dict:
    """Extrae metadatos del archivo de audio con ffprobe."""
    if not _has_ffprobe():
        return {}
    cmd = [
        "ffprobe", "-v", "quiet",
        "-print_format", "json",
        "-show_streams", "-show_format",
        path
    ]
    try:
        import json
        out = subprocess.check_output(cmd, stderr=subprocess.DEVNULL, timeout=10)
        return json.loads(out)
    except Exception:
        return {}


def _get_duration(path: str) -> float:
    info = _ffprobe_info(path)
    try:
        return float(info["format"]["duration"])
    except (KeyError, TypeError, ValueError):
        return 0.0


# ──────────────────────────────────────────────────────────────────────────────
# AudioEffect
# ──────────────────────────────────────────────────────────────────────────────

class AudioEffect:
    """
    Generador de filtros ffmpeg para efectos de audio.

    Uso:
        fx = AudioEffect()
        fx.equalizer(bass=6, treble=-2, mid=1)
        fx.reverb(room_size=0.5, damping=0.3)
        fx.echo(delay_ms=250, decay=0.5)
        fx.compress(threshold=-20, ratio=4, attack=5, release=50)
        filter_string = fx.build()
    """

    def __init__(self):
        self._filters: list[str] = []

    def equalizer(
        self,
        bass:   float = 0,
        low_mid:float = 0,
        mid:    float = 0,
        high_mid:float= 0,
        treble: float = 0,
    ) -> "AudioEffect":
        """Simple 5-band EQ usando filtros shelving/peak."""
        parts = []
        if bass != 0:
            parts.append(f"equalizer=f=80:width_type=o:width=2:g={bass:.1f}")
        if low_mid != 0:
            parts.append(f"equalizer=f=250:width_type=o:width=2:g={low_mid:.1f}")
        if mid != 0:
            parts.append(f"equalizer=f=1000:width_type=o:width=2:g={mid:.1f}")
        if high_mid != 0:
            parts.append(f"equalizer=f=4000:width_type=o:width=2:g={high_mid:.1f}")
        if treble != 0:
            parts.append(f"equalizer=f=12000:width_type=o:width=2:g={treble:.1f}")
        if parts:
            self._filters.extend(parts)
        return self

    def reverb(
        self,
        room_size: float = 0.5,
        damping:   float = 0.5,
        wet:       float = 0.3,
    ) -> "AudioEffect":
        """Reverb simulado con aecho."""
        delays  = "60|70|80"
        decays  = f"{room_size:.2f}|{room_size*0.8:.2f}|{room_size*0.6:.2f}"
        in_gain = 0.8
        out_gain= max(0.1, 1.0 - wet)
        self._filters.append(
            f"aecho=in_gain={in_gain}:out_gain={out_gain:.2f}:"
            f"delays={delays}:decays={decays}"
        )
        return self

    def echo(self, delay_ms: float = 250, decay: float = 0.5) -> "AudioEffect":
        """Eco simple."""
        self._filters.append(
            f"aecho=in_gain=0.8:out_gain=0.88:"
            f"delays={int(delay_ms)}:decays={decay:.2f}"
        )
        return self

    def compress(
        self,
        threshold: float = -20,
        ratio:     float = 4,
        attack:    float = 5,
        release:   float = 50,
    ) -> "AudioEffect":
        """Compresor dinámico."""
        self._filters.append(
            f"acompressor=threshold={threshold}dB:ratio={ratio}:"
            f"attack={attack}:release={release}"
        )
        return self

    def pitch(self, semitones: float = 0) -> "AudioEffect":
        """Cambio de tono en semitonos."""
        if semitones != 0:
            ratio = 2 ** (semitones / 12.0)
            self._filters.append(f"asetrate={int(_SAMPLE_RATE * ratio)},aresample={_SAMPLE_RATE}")
        return self

    def speed(self, factor: float = 1.0) -> "AudioEffect":
        """Time stretching (velocidad sin cambiar tono)."""
        if factor != 1.0:
            self._filters.append(f"atempo={factor:.4f}")
        return self

    def normalize(self, target_lufs: float = -16) -> "AudioEffect":
        """Normalización loudnorm."""
        self._filters.append(f"loudnorm=I={target_lufs:.1f}:TP=-1.5:LRA=11")
        return self

    def lowpass(self, cutoff_hz: float = 3000) -> "AudioEffect":
        self._filters.append(f"lowpass=f={int(cutoff_hz)}")
        return self

    def highpass(self, cutoff_hz: float = 100) -> "AudioEffect":
        self._filters.append(f"highpass=f={int(cutoff_hz)}")
        return self

    def custom(self, filter_str: str) -> "AudioEffect":
        """Filtro ffmpeg personalizado."""
        self._filters.append(filter_str)
        return self

    def build(self) -> str | None:
        """Devuelve la cadena de filtros lista para ffmpeg -af."""
        if not self._filters:
            return None
        return ",".join(self._filters)

    def clear(self) -> "AudioEffect":
        self._filters.clear()
        return self


# ──────────────────────────────────────────────────────────────────────────────
# MasterTrack
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class MasterTrack:
    path:     str
    duration: float    = 0.0
    position: float    = 0.0
    volume:   float    = 1.0
    loops:    int      = 0


# ──────────────────────────────────────────────────────────────────────────────
# Master
# ──────────────────────────────────────────────────────────────────────────────

class Master:
    """
    Mezclador de audio de alta calidad usando FFmpeg.

    Soporta cualquier formato que ffmpeg pueda decodificar.
    """

    def __init__(
        self,
        sample_rate: int  = 44100,
        channels:    int  = 2,
        buffer_size: int  = 4096,
    ):
        self._rate   = sample_rate
        self._ch     = channels
        self._buf    = buffer_size
        self._volume = 1.0
        self._effect: AudioEffect | None = None

        self._track: MasterTrack | None = None
        self._pcm_data: bytes = b""
        self._play_pos:  int  = 0       # posición en bytes
        self._playing  = False
        self._paused   = False
        self._loop_count = 0

        self._lock  = threading.Lock()
        self._thread: threading.Thread | None = None
        self._stop_evt = threading.Event()

        self._on_end: Callable | None = None
        self._on_position: Callable | None = None   # Callable[[float], None]

        self._backend, self._backend_name = _import_audio_backend()

        if not _has_ffmpeg():
            import warnings
            warnings.warn(
                "ffmpeg no encontrado en PATH. Master no podrá decodificar audio.",
                RuntimeWarning, stacklevel=2
            )

    # ── Properties ────────────────────────────────────────────────────────

    @property
    def is_playing(self) -> bool:
        return self._playing and not self._paused

    @property
    def position(self) -> float:
        if not self._pcm_data:
            return 0.0
        bytes_per_sec = self._rate * self._ch * _SAMPLE_WIDTH
        return self._play_pos / max(1, bytes_per_sec)

    @property
    def duration(self) -> float:
        return self._track.duration if self._track else 0.0

    # ── Volume ────────────────────────────────────────────────────────────

    @property
    def volume(self) -> float:
        return self._volume

    @volume.setter
    def volume(self, v: float) -> None:
        self._volume = max(0.0, min(1.0, v))

    def set_volume(self, v: float) -> "Master":
        self.volume = v
        return self

    def fade_to(self, target: float, duration_s: float) -> "Master":
        """Fade suave del volumen."""
        def _fade():
            steps = max(1, int(duration_s * 30))
            delta = (target - self._volume) / steps
            for _ in range(steps):
                self.volume += delta
                time.sleep(duration_s / steps)
            self.volume = target
        threading.Thread(target=_fade, daemon=True).start()
        return self

    # ── Effects ───────────────────────────────────────────────────────────

    def set_effect(self, effect: AudioEffect | None) -> "Master":
        """Establece los efectos; se aplican en la próxima llamada a play()."""
        self._effect = effect
        return self

    def effect(self, **kwargs) -> AudioEffect:
        """Crea y aplica un AudioEffect en fluent API."""
        fx = AudioEffect()
        if "equalizer" in kwargs:
            fx.equalizer(**kwargs.get("equalizer_params", {}))
        if "reverb" in kwargs:
            fx.reverb()
        if "echo" in kwargs:
            d = kwargs.get("echo", {})
            fx.echo(**d if isinstance(d, dict) else {})
        self._effect = fx
        return fx

    # ── Load & Play ───────────────────────────────────────────────────────

    def load(self, path: str | Path) -> "Master":
        """Pre-carga el audio en memoria (sin reproducir)."""
        path = str(path)
        filters = self._effect.build() if self._effect else None
        self._pcm_data  = _ffmpeg_decode(path, self._rate, self._ch, filters=filters)
        dur = _get_duration(path) if _has_ffprobe() else len(self._pcm_data) / (self._rate * self._ch * _SAMPLE_WIDTH)
        self._track = MasterTrack(path=path, duration=dur)
        self._play_pos = 0
        return self

    def play(
        self,
        path:      str | Path | None = None,
        loops:     int   = 0,
        start_s:   float = 0.0,
        fadein_s:  float = 0.0,
    ) -> "Master":
        """
        Reproduce un archivo de audio.

        Args:
            path    : ruta al archivo (None = usa el último cargado)
            loops   : 0=una vez, -1=infinito, n=n repeticiones adicionales
            start_s : segundo de inicio
            fadein_s: duración del fade-in en segundos
        """
        self.stop()

        if path is not None:
            path = str(path)
            filters  = self._effect.build() if self._effect else None
            self._pcm_data = _ffmpeg_decode(
                path, self._rate, self._ch,
                start_s=start_s, filters=filters
            )
            dur = _get_duration(path) if _has_ffprobe() else (
                len(self._pcm_data) / (self._rate * self._ch * _SAMPLE_WIDTH)
            )
            self._track = MasterTrack(path=path, duration=dur, loops=loops)
        elif not self._pcm_data:
            return self

        self._play_pos   = int(start_s * self._rate * self._ch * _SAMPLE_WIDTH)
        self._play_pos  -= self._play_pos % (_SAMPLE_WIDTH * self._ch)  # align
        self._loop_count = loops
        self._playing    = True
        self._paused     = False
        self._stop_evt.clear()

        self._thread = threading.Thread(
            target=self._playback_loop,
            args=(fadein_s,),
            daemon=True,
        )
        self._thread.start()
        return self

    def stop(self) -> "Master":
        self._stop_evt.set()
        self._playing = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        self._thread = None
        return self

    def pause(self) -> "Master":
        self._paused = not self._paused
        return self

    def seek(self, seconds: float) -> "Master":
        bps = self._rate * self._ch * _SAMPLE_WIDTH
        pos = int(seconds * bps)
        pos -= pos % (_SAMPLE_WIDTH * self._ch)
        with self._lock:
            self._play_pos = max(0, min(pos, len(self._pcm_data)))
        return self

    # ── Crossfade ─────────────────────────────────────────────────────────

    def crossfade(self, path: str | Path, duration_s: float = 2.0) -> "Master":
        """
        Transición suave hacia un nuevo archivo.
        Hace fade-out del actual y fade-in del nuevo simultáneamente.
        """
        def _cross():
            self.fade_to(0.0, duration_s)
            time.sleep(duration_s * 0.5)
            self.play(str(path), fadein_s=duration_s)
        threading.Thread(target=_cross, daemon=True).start()
        return self

    # ── Callbacks ─────────────────────────────────────────────────────────

    def on_end(self, cb: Callable | None) -> "Master":
        self._on_end = cb
        return self

    def on_position(self, cb: Callable | None) -> "Master":
        """cb(position_seconds) llamado cada 100ms durante reproducción."""
        self._on_position = cb
        return self

    # ── Analysis ──────────────────────────────────────────────────────────

    def get_waveform(
        self,
        path: str | Path,
        samples: int = 1024,
    ) -> list[float]:
        """
        Extrae la forma de onda normalizada del archivo.

        Returns:
            Lista de `samples` valores flotantes en [-1.0, 1.0]
        """
        try:
            import numpy as np
            pcm = _ffmpeg_decode(str(path), rate=22050, channels=1)
            if not pcm:
                return []
            arr = np.frombuffer(pcm, dtype=np.int16).astype(np.float32) / 32768.0
            # Resample a `samples` puntos
            indices = np.linspace(0, len(arr) - 1, samples, dtype=int)
            return arr[indices].tolist()
        except Exception:
            return []

    def get_spectrum(
        self,
        path: str | Path,
        fft_size: int = 1024,
        at_second: float = 0.0,
    ) -> list[float]:
        """
        Calcula el espectro FFT en un momento dado del archivo.

        Returns:
            Lista de magnitudes normalizadas (fft_size//2 valores)
        """
        try:
            import numpy as np
            # Tomar 1 segundo de audio en at_second
            pcm = _ffmpeg_decode(str(path), rate=44100, channels=1,
                                 start_s=at_second, duration_s=1.0)
            if not pcm:
                return []
            arr = np.frombuffer(pcm, dtype=np.int16).astype(np.float32) / 32768.0
            window = np.hanning(fft_size)
            chunk  = arr[:fft_size]
            if len(chunk) < fft_size:
                chunk = np.pad(chunk, (0, fft_size - len(chunk)))
            spectrum = np.abs(np.fft.rfft(chunk * window))
            spectrum = spectrum / np.max(spectrum) if np.max(spectrum) > 0 else spectrum
            return spectrum.tolist()
        except Exception:
            return []

    def export_segment(
        self,
        source: str | Path,
        out:    str | Path,
        start_s: float,
        end_s:   float,
        format: str = "mp3",
    ) -> Path:
        """
        Exporta un segmento del audio a un archivo.

        Args:
            source  : archivo fuente
            out     : archivo de salida
            start_s : segundo de inicio
            end_s   : segundo de fin
            format  : "mp3" | "ogg" | "flac" | "wav" | ...
        """
        out = Path(out)
        dur = end_s - start_s
        cmd = [
            "ffmpeg", "-hide_banner", "-loglevel", "quiet",
            "-ss", str(start_s), "-t", str(dur),
            "-i", str(source),
            "-y", str(out)
        ]
        subprocess.run(cmd, check=True)
        return out

    def record(
        self,
        out: str | Path,
        duration_s: float,
        device: int | None = None,
    ) -> Path:
        """
        Graba audio del micrófono usando ffmpeg.

        Args:
            out        : archivo de salida (ej: "recording.wav")
            duration_s : duración en segundos
            device     : índice de dispositivo de entrada (None=default)
        """
        out = Path(out)
        # En Linux usamos pulse/alsa, en Win dshow, en Mac avfoundation
        import sys
        if sys.platform == "win32":
            fmt, inp = "dshow", "audio=Microphone"
        elif sys.platform == "darwin":
            fmt, inp = "avfoundation", ":default"
        else:
            fmt, inp = "pulse", "default"

        cmd = [
            "ffmpeg", "-hide_banner", "-loglevel", "quiet",
            "-f", fmt, "-i", inp,
            "-t", str(duration_s),
            "-y", str(out)
        ]
        proc = subprocess.Popen(cmd)
        proc.wait()
        return out

    # ── Internal playback ─────────────────────────────────────────────────

    def _playback_loop(self, fadein_s: float) -> None:
        if self._backend_name == "sounddevice":
            self._play_sounddevice(fadein_s)
        elif self._backend_name == "pyaudio":
            self._play_pyaudio(fadein_s)
        else:
            # Fallback silencioso — solo avanza el tiempo
            self._play_fake(fadein_s)

    def _apply_volume_to_chunk(self, chunk: bytes, fade_vol: float = 1.0) -> bytes:
        """Aplica volumen maestro al chunk PCM int16."""
        try:
            import numpy as np
            arr = np.frombuffer(chunk, dtype=np.int16).astype(np.float32)
            arr *= (self._volume * fade_vol)
            arr = np.clip(arr, -32768, 32767)
            return arr.astype(np.int16).tobytes()
        except Exception:
            return chunk

    def _play_sounddevice(self, fadein_s: float) -> None:
        import sounddevice as sd
        import numpy as np

        data = self._pcm_data
        total= len(data)
        bps  = self._rate * self._ch * _SAMPLE_WIDTH
        fade_samples = int(fadein_s * bps)
        t_last_pos = time.perf_counter()
        loops_done = 0

        try:
            stream = sd.RawOutputStream(
                samplerate=self._rate,
                channels=self._ch,
                dtype="int16",
                blocksize=self._buf,
            )
            stream.start()

            while not self._stop_evt.is_set():
                if self._paused:
                    time.sleep(0.05)
                    continue

                with self._lock:
                    pos = self._play_pos

                remaining = total - pos
                if remaining <= 0:
                    if self._loop_count == -1 or loops_done < self._loop_count:
                        with self._lock:
                            self._play_pos = 0
                        loops_done += 1
                        continue
                    else:
                        break

                chunk_size = min(self._buf * _SAMPLE_WIDTH * self._ch, remaining)
                chunk = data[pos:pos + chunk_size]

                # Fade-in
                fade_vol = 1.0
                if fadein_s > 0 and pos < fade_samples:
                    fade_vol = pos / max(1, fade_samples)

                chunk = self._apply_volume_to_chunk(chunk, fade_vol)
                stream.write(chunk)

                with self._lock:
                    self._play_pos += chunk_size

                # Callback de posición
                now = time.perf_counter()
                if self._on_position and now - t_last_pos >= 0.1:
                    self._on_position(self.position)
                    t_last_pos = now

            stream.stop()
            stream.close()
        except Exception:
            pass

        self._playing = False
        if self._on_end and not self._stop_evt.is_set():
            self._on_end()

    def _play_pyaudio(self, fadein_s: float) -> None:
        import pyaudio
        pa = pyaudio.PyAudio()
        stream = pa.open(
            format=pyaudio.paInt16,
            channels=self._ch,
            rate=self._rate,
            output=True,
            frames_per_buffer=self._buf,
        )

        data  = self._pcm_data
        total = len(data)
        bps   = self._rate * self._ch * _SAMPLE_WIDTH
        fade_bytes = int(fadein_s * bps)
        loops_done = 0

        try:
            while not self._stop_evt.is_set():
                if self._paused:
                    time.sleep(0.05)
                    continue

                with self._lock:
                    pos = self._play_pos

                if pos >= total:
                    if self._loop_count == -1 or loops_done < self._loop_count:
                        with self._lock:
                            self._play_pos = 0
                        loops_done += 1
                        continue
                    else:
                        break

                chunk_size = min(self._buf * _SAMPLE_WIDTH * self._ch, total - pos)
                chunk = data[pos:pos + chunk_size]
                fade_vol = min(1.0, pos / max(1, fade_bytes)) if fadein_s > 0 and pos < fade_bytes else 1.0
                chunk = self._apply_volume_to_chunk(chunk, fade_vol)
                stream.write(chunk)

                with self._lock:
                    self._play_pos += chunk_size
        finally:
            stream.stop_stream()
            stream.close()
            pa.terminate()

        self._playing = False
        if self._on_end and not self._stop_evt.is_set():
            self._on_end()

    def _play_fake(self, fadein_s: float) -> None:
        """Fallback sin backend de audio — sólo simula el tiempo."""
        if not self._track:
            return
        dur = self._track.duration or 1.0
        start = time.perf_counter()
        while not self._stop_evt.is_set():
            elapsed = time.perf_counter() - start
            if elapsed >= dur:
                break
            if self._on_position:
                self._on_position(elapsed)
            time.sleep(0.1)
        self._playing = False
        if self._on_end and not self._stop_evt.is_set():
            self._on_end()

    # ── Cleanup ───────────────────────────────────────────────────────────

    def quit(self) -> None:
        self.stop()

    def __del__(self):
        try:
            self.quit()
        except Exception:
            pass