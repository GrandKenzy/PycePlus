from pathlib import Path
from io import BytesIO
from zipfile import ZipFile, is_zipfile

from fontTools.ttLib import TTFont

import pygame
import pygame.freetype
import sys
import os

from PycePlus.CORE.tools import network
from PycePlus.UI import Application
from PycePlus.UI.tools.color import Color, colorType

VALID_EXT = ('.ttf', '.otf', '.ttc')


def _safe_filename(name: str) -> str:
    try:
        return "".join(c for c in name if c.isalnum() or c in ('_', '-')).strip() or "font"
    except Exception:
        return "font"


def _extract_font_name(data: bytes) -> str:
    try:
        font = TTFont(BytesIO(data))
    except Exception:
        return "unknown_font"

    name = None

    try:
        for record in font['name'].names:
            try:
                if record.nameID == 4:
                    try:
                        name = record.toUnicode()
                    except Exception:
                        try:
                            name = record.string.decode(errors='ignore')
                        except Exception:
                            name = None
                    if name:
                        break
            except Exception:
                continue
    except Exception:
        pass
    finally:
        try:
            font.close()
        except Exception:
            pass

    try:
        return _safe_filename(name) if name else "unknown_font"
    except Exception:
        return "unknown_font"


def _pick_font_from_zip(data: bytes) -> tuple[str, bytes] | None:
    try:
        with ZipFile(BytesIO(data)) as z:
            candidates = []

            try:
                for info in z.infolist():
                    try:
                        if info.is_dir():
                            continue
                        ext = Path(info.filename).suffix.lower()
                        if ext in VALID_EXT:
                            candidates.append(info)
                    except Exception:
                        continue
            except Exception:
                pass

            if not candidates:
                return None

            try:
                candidates.sort(key=lambda x: Path(x.filename).suffix.lower() == '.ttc')
            except Exception:
                pass

            try:
                chosen = candidates[0]
                return Path(chosen.filename).suffix.lower(), z.read(chosen.filename)
            except Exception:
                return None
    except Exception:
        return None


def _normalize(name: str) -> str:
    try:
        return name.lower().replace(' ', '').replace('-', '')
    except Exception:
        return ""


def _scan_fonts_dirs() -> list[Path]:
    paths = []

    try:
        local = Path(Application.root) / 'data' / 'fonts'
        local.mkdir(parents=True, exist_ok=True)
        paths.append(local)
    except Exception:
        pass

    try:
        if sys.platform == "win32":
            paths.append(Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts")
        elif sys.platform == "darwin":
            paths += [
                Path("/System/Library/Fonts"),
                Path("/Library/Fonts"),
                Path.home() / "Library/Fonts"
            ]
        else:
            paths += [
                Path("/usr/share/fonts"),
                Path("/usr/local/share/fonts"),
                Path.home() / ".fonts"
            ]
    except Exception:
        pass

    return paths


def _find_font_by_name(name: str) -> Path | None:
    try:
        target = _normalize(name)
        if not target:
            return None

        for base in _scan_fonts_dirs():
            try:
                if not base.exists():
                    continue
            except Exception:
                continue

            try:
                for path in base.rglob('*'):
                    try:
                        if path.suffix.lower() not in VALID_EXT:
                            continue

                        norm = _normalize(path.stem)
                        if target == norm or target in norm:
                            return path
                    except Exception:
                        continue
            except Exception:
                continue
    except Exception:
        return None

    return None


def get_font(path: str | Path | list[str]) -> Path:
    try:
        folder = Path(Application.root) / 'data' / 'fonts'
        folder.mkdir(parents=True, exist_ok=True)
    except Exception:
        folder = Path.cwd()

    try:
        if isinstance(path, (list, tuple)):
            last_error = None
            for p in path:
                try:
                    return get_font(p)
                except Exception as e:
                    last_error = e
            raise FileNotFoundError(f"No se encontró ninguna fuente en {path}") from last_error
    except Exception as e:
        raise e

    try:
        path = str(path).strip()
    except Exception:
        raise FileNotFoundError("Ruta de fuente inválida")

    try:
        if path.startswith(('http://', 'https://')):
            try:
                obj = network.download(path)
                res = obj.get(True)
            except Exception:
                raise RuntimeError("Error descargando fuente")

            try:
                data = res.data
            except Exception:
                raise RuntimeError("Respuesta inválida al descargar fuente")

            try:
                if is_zipfile(BytesIO(data)):
                    result = _pick_font_from_zip(data)
                    if not result:
                        raise ValueError("ZIP sin fuentes válidas")

                    ext, font_data = result
                    name = _extract_font_name(font_data)
                    file_path = folder / f"{name}{ext}"

                    try:
                        if not file_path.exists():
                            file_path.write_bytes(font_data)
                    except Exception:
                        pass

                    return file_path
            except Exception:
                pass

            try:
                ext = Path(path).suffix.lower() or '.ttf'
            except Exception:
                ext = '.ttf'

            try:
                name = _extract_font_name(data)
            except Exception:
                name = "unknown_font"

            file_path = folder / f"{name}{ext}"

            try:
                if not file_path.exists():
                    file_path.write_bytes(data)
            except Exception:
                pass

            return file_path
    except Exception:
        pass

    try:
        p = Path(path)
        if p.exists():
            return p
    except Exception:
        pass

    try:
        found = _find_font_by_name(path)
        if found:
            return found
    except Exception:
        pass

    raise FileNotFoundError(f"No se encontró la fuente: {path}")


class FontType1:
    def __init__(self, family: str, size: int, antialias: bool):
        self.family = family
        self.size = size
        self.antialias = antialias

        try:
            font_path = get_font(family)
            self._ofont = pygame.font.Font(str(font_path), size)
        except Exception:
            self._ofont = pygame.font.Font(None, size)

    @property
    def font(self):
        return self._ofont


class FontType2:
    def __init__(self, family: str, size: int, antialias: bool):
        self.family = family
        self.size = size
        self.antialias = antialias

        try:
            font_path = get_font(family)
            self._ofont = pygame.freetype.Font(str(font_path), size)
        except Exception:
            self._ofont = pygame.freetype.SysFont(None, size)

    @property
    def font(self):
        return self._ofont


class Font:
    def __init__(self, family, size: int = 16, antialias: bool = True, freetype: bool = True):
        self._family = family
        self._size = size
        self._antialias = antialias
        self._freetype = freetype

        self._bold = False
        self._italic = False
        self._underline = False

        self._font = None
        self._build()

    def _resolve_family(self, family):
        if isinstance(family, Font):
            return family.get_font_family()
        return family

    def _build(self):
        try:
            fam = self._resolve_family(self._family)

            if self._freetype:
                self._font = FontType2(fam, self._size, self._antialias).font
                try:
                    self._font.strong = self._bold
                    self._font.oblique = self._italic
                    self._font.underline = self._underline
                except Exception:
                    pass
            else:
                self._font = FontType1(fam, self._size, self._antialias).font
                try:
                    self._font.set_bold(self._bold)
                    self._font.set_italic(self._italic)
                    self._font.set_underline(self._underline)
                except Exception:
                    pass
        except Exception:
            try:
                if self._freetype:
                    self._font = pygame.freetype.SysFont(None, self._size)
                else:
                    self._font = pygame.font.Font(None, self._size)
            except Exception:
                self._font = None

    def set_bold(self, value: bool):
        self._bold = bool(value)
        try:
            if self._freetype:
                self._font.strong = self._bold
            else:
                self._font.set_bold(self._bold)
        except Exception:
            pass

    def set_italic(self, value: bool):
        self._italic = bool(value)
        try:
            if self._freetype:
                self._font.oblique = self._italic
            else:
                self._font.set_italic(self._italic)
        except Exception:
            pass

    def set_underline(self, value: bool):
        self._underline = bool(value)
        try:
            if self._freetype:
                self._font.underline = self._underline
            else:
                self._font.set_underline(self._underline)
        except Exception:
            pass

    def get_underline(self) -> bool:
        return self._underline

    def get_font_size(self) -> int:
        return self._size

    def get_font_family(self):
        return self._family

    def update(self, family=None, size=None, antialias=None):
        try:
            if family is not None:
                self._family = family
            if size is not None:
                self._size = int(size)
            if antialias is not None:
                self._antialias = bool(antialias)
            self._build()
        except Exception:
            pass

    def size(self, text):
        try:
            if isinstance(text, (list, tuple)):
                return [self.size(t) for t in text]

            text = str(text)

            if self._freetype:
                rect = self._font.get_rect(text)
                return rect.width, rect.height
            else:
                return self._font.size(text)
        except Exception:
            return (0, 0)

    def render(self, text: str, color: colorType):
            
        color = Color.makefrom(color)
        text = str(text)
        try:
            if self._freetype:
                surf, _ = self._font.render(text, fgcolor=color, antialias=self._antialias)
                return surf
            else:
                return self._font.render(
                    str(text),
                    self._antialias,
                    color
                )
        except Exception:
            try:
                return pygame.Surface((1, 1), pygame.SRCALPHA)
            except Exception:
                return None
            
            
from typing import TypeAlias

FontLike: TypeAlias = Font | str | tuple[str, ...] | list[str]