"""
PycePlus.GUI.interface_man.css
==============================
Parser CSS → diccionarios de estilo PycePlus.

Uso:
    from PycePlus.GUI.interface_man.css import compileFrom, StyleSheet

    sheet = compileFrom("estilos.css")

    # Aplicar a un widget directamente:
    ppyce.Button(window, style=sheet["Button"])
    ppyce.Button(window, style=sheet[".primary"])
    ppyce.Button(window, style=sheet["#mi-boton"])

    # Selector con estado:
    ppyce.Button(
        window,
        style=sheet["Button"],
        hover_style=sheet["Button:hover"],
        active_style=sheet["Button:active"],
    )

Soporta:
    - Selectores de tipo:   Button { ... }
    - Clases:               .primary { ... }
    - IDs:                  #mi-widget { ... }
    - Pseudoclases:         Button:hover { ... }
    - Variables CSS:        --color-bg: #1e1e1e;  → var(--color-bg)
    - Propiedades comunes:  background-color, color, border-radius, ...
    - Shorthand padding/border
    - Comentarios /* */
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

__all__ = ["compileFrom", "StyleSheet", "parse_css_string"]

# ──────────────────────────────────────────────────────────────────────────────
# Propiedad CSS → clave PycePlus
# ──────────────────────────────────────────────────────────────────────────────

_PROP_MAP: dict[str, str] = {
    "background-color":          "background_color",
    "background":                "background_color",
    "color":                     "color",
    "border-radius":             "border_radius",
    "border-top-left-radius":    "border_top_left_radius",
    "border-top-right-radius":   "border_top_right_radius",
    "border-bottom-left-radius": "border_bottom_left_radius",
    "border-bottom-right-radius":"border_bottom_right_radius",
    "border-width":              "border",
    "border":                    "border",
    "border-color":              "border_color",
    "padding":                   "padding",
    "padding-left":              "padding_left",
    "padding-right":             "padding_right",
    "padding-top":               "padding_top",
    "padding-bottom":            "padding_bottom",
    "font-size":                 "font_size",
    "font-family":               "font_family",
    "font-weight":               "font_bold",
    "font-style":                "font_italic",
    "text-decoration":           "font_underline",
    "text-align":                "text_align",
    "width":                     "width",
    "height":                    "height",
    "left":                      "x",
    "top":                       "y",
    "opacity":                   "opacity",
    "cursor":                    "cursor",
    "box-shadow":                "effects.box_shadow",
    "text-shadow":               "effects.text_shadow",
    "align-items":               "align_items",
}

# ──────────────────────────────────────────────────────────────────────────────
# Conversores de valor
# ──────────────────────────────────────────────────────────────────────────────

_HEX3 = re.compile(r"^#([0-9a-fA-F])([0-9a-fA-F])([0-9a-fA-F])$")
_HEX6 = re.compile(r"^#([0-9a-fA-F]{2})([0-9a-fA-F]{2})([0-9a-fA-F]{2})$")
_HEX8 = re.compile(r"^#([0-9a-fA-F]{2})([0-9a-fA-F]{2})([0-9a-fA-F]{2})([0-9a-fA-F]{2})$")
_RGB  = re.compile(r"rgba?\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)(?:\s*,\s*([\d.]+))?\s*\)")
_PX   = re.compile(r"^([-\d.]+)px$")
_PCT  = re.compile(r"^([-\d.]+)%$")
_PT   = re.compile(r"^([-\d.]+)pt$")

_NAMED_COLORS: dict[str, tuple] = {
    "transparent": (0,0,0,0), "white": (255,255,255,255),
    "black": (0,0,0,255), "red": (255,0,0,255),
    "green": (0,128,0,255), "blue": (0,0,255,255),
    "gray": (128,128,128,255), "grey": (128,128,128,255),
    "silver": (192,192,192,255), "navy": (0,0,128,255),
    "teal": (0,128,128,255), "lime": (0,255,0,255),
    "yellow": (255,255,0,255), "orange": (255,165,0,255),
    "purple": (128,0,128,255), "pink": (255,192,203,255),
    "brown": (165,42,42,255), "cyan": (0,255,255,255),
    "magenta": (255,0,255,255),
}


def _parse_color(raw: str) -> tuple[int, int, int, int] | None:
    raw = raw.strip()

    named = _NAMED_COLORS.get(raw.lower())
    if named:
        return named

    m = _HEX8.match(raw)
    if m:
        return (int(m[1],16), int(m[2],16), int(m[3],16), int(m[4],16))

    m = _HEX6.match(raw)
    if m:
        return (int(m[1],16), int(m[2],16), int(m[3],16), 255)

    m = _HEX3.match(raw)
    if m:
        r,g,b = m[1]*2, m[2]*2, m[3]*2
        return (int(r,16), int(g,16), int(b,16), 255)

    m = _RGB.match(raw)
    if m:
        r,g,b = int(float(m[1])), int(float(m[2])), int(float(m[3]))
        a = int(float(m[4]) * 255) if m[4] else 255
        return (r, g, b, a)

    return None


def _parse_length(raw: str) -> int | float | None:
    raw = raw.strip()
    m = _PX.match(raw)
    if m:
        return int(float(m[1]))
    m = _PCT.match(raw)
    if m:
        return float(m[1])   # retorna float para que el caller sepa que es %
    m = _PT.match(raw)
    if m:
        return max(1, int(float(m[1]) * 96 / 72))  # pt → px a 96dpi
    try:
        return int(float(raw))
    except ValueError:
        return None


def _parse_border(raw: str) -> dict:
    """Parse 'border: 1px solid #ccc'"""
    parts = raw.strip().split()
    out: dict = {}
    for part in parts:
        color = _parse_color(part)
        if color:
            out["border_color"] = color
            continue
        length = _parse_length(part)
        if isinstance(length, int):
            out["border"] = length
            continue
    return out


def _parse_shadow(raw: str) -> dict | None:
    """Parse box-shadow/text-shadow: 2px 4px 8px rgba(0,0,0,0.5)"""
    tokens = re.split(r"\s+", raw.strip())
    nums: list[int] = []
    color = None
    for t in tokens:
        c = _parse_color(t)
        if c:
            color = c
            continue
        n = _parse_length(t)
        if isinstance(n, int):
            nums.append(n)
    if len(nums) < 2:
        return None
    result: dict = {"offset": (nums[0], nums[1])}
    if len(nums) >= 3:
        result["blur"] = nums[2]
    if len(nums) >= 4:
        result["spread"] = nums[3]
    if color:
        result["color"] = color
    return result


def _convert_value(prop: str, raw: str) -> Any:
    """Convierte el valor CSS raw al tipo esperado por PycePlus."""
    raw = raw.strip()

    # Colores
    if prop in ("background_color", "color", "border_color"):
        c = _parse_color(raw)
        return c if c else raw

    # Efectos de shadow
    if prop.startswith("effects."):
        return _parse_shadow(raw)

    # font_size
    if prop == "font_size":
        v = _parse_length(raw)
        return int(v) if isinstance(v, (int, float)) else 14

    # border (entero)
    if prop == "border":
        parts = raw.split()
        for p in parts:
            v = _parse_length(p)
            if isinstance(v, int):
                return v
        return 0

    # border_radius / paddings / x / y / width / height
    if prop in (
        "border_radius", "border_top_left_radius", "border_top_right_radius",
        "border_bottom_left_radius", "border_bottom_right_radius",
        "padding", "padding_left", "padding_right", "padding_top", "padding_bottom",
        "x", "y", "width", "height",
    ):
        v = _parse_length(raw)
        if isinstance(v, (int, float)):
            return int(v)
        return 0

    # opacity
    if prop == "opacity":
        try:
            return float(raw)
        except ValueError:
            return 1.0

    # font_bold
    if prop == "font_bold":
        return raw.lower() in ("bold", "700", "800", "900")

    # font_italic
    if prop == "font_italic":
        return raw.lower() == "italic"

    # font_underline
    if prop == "font_underline":
        return "underline" in raw.lower()

    # font_family
    if prop == "font_family":
        return raw.strip("'\"").split(",")[0].strip() or None

    # Strings directos
    return raw


def _handle_shorthand(prop: str, raw: str, out: dict) -> None:
    """Expande shorthands como padding: 4px 8px."""
    if prop in ("padding",):
        parts = raw.split()
        vals = []
        for p in parts:
            v = _parse_length(p)
            vals.append(int(v) if isinstance(v, (int, float)) else 0)
        if len(vals) == 1:
            out["padding"] = vals[0]
        elif len(vals) == 2:
            out["padding_top"] = vals[0]; out["padding_bottom"] = vals[0]
            out["padding_left"] = vals[1]; out["padding_right"] = vals[1]
        elif len(vals) == 4:
            out["padding_top"] = vals[0]; out["padding_right"] = vals[1]
            out["padding_bottom"] = vals[2]; out["padding_left"] = vals[3]
        return

    if prop == "border":
        bd = _parse_border(raw)
        out.update(bd)
        return

    # Normal
    pyc = _PROP_MAP.get(prop)
    if not pyc:
        return

    if pyc.startswith("effects."):
        effect_key = pyc.split(".", 1)[1]
        val = _parse_shadow(raw)
        if val is not None:
            effects = out.setdefault("effects", {})
            effects[effect_key] = val
    else:
        out[pyc] = _convert_value(pyc, raw)


# ──────────────────────────────────────────────────────────────────────────────
# Parser principal
# ──────────────────────────────────────────────────────────────────────────────

_VAR_DECL = re.compile(r"--([\w-]+)\s*:\s*(.+?)\s*(?:;|$)")
_VAR_USE   = re.compile(r"var\(--([\w-]+)\)")


def _strip_comments(text: str) -> str:
    return re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)


def _resolve_vars(text: str, variables: dict[str, str]) -> str:
    def replacer(m: re.Match) -> str:
        return variables.get(m.group(1), m.group(0))
    return _VAR_USE.sub(replacer, text)


class StyleSheet:
    """
    Colección de estilos compilados desde CSS.
    Accede por selector:  sheet["Button"]  sheet[".primary"]  sheet["#id"]
    """

    def __init__(self, rules: dict[str, dict]):
        self._rules = rules

    def __getitem__(self, selector: str) -> dict:
        return dict(self._rules.get(selector, {}))

    def get(self, selector: str, default: dict | None = None) -> dict:
        return dict(self._rules.get(selector, default or {}))

    def merge(self, *selectors: str) -> dict:
        """Fusiona varios selectores en un dict (el último gana)."""
        merged: dict = {}
        for sel in selectors:
            merged.update(self._rules.get(sel, {}))
        return merged

    def keys(self):
        return self._rules.keys()

    def __repr__(self) -> str:
        return f"<StyleSheet selectors={list(self._rules.keys())}>"


def parse_css_string(css_text: str) -> StyleSheet:
    """
    Parsea un string CSS y devuelve un StyleSheet.
    """
    text = _strip_comments(css_text)

    # Extraer variables CSS :root { --var: val; }
    variables: dict[str, str] = {}
    root_match = re.search(r":root\s*\{([^}]*)\}", text, re.DOTALL)
    if root_match:
        for m in _VAR_DECL.finditer(root_match.group(1)):
            variables[m.group(1)] = m.group(2).strip()

    # Resolver variables en el texto
    text = _resolve_vars(text, variables)

    # Extraer bloques: selector { props }
    rules: dict[str, dict] = {}
    block_re = re.compile(r"([^{]+)\{([^}]*)\}", re.DOTALL)

    for m in block_re.finditer(text):
        selectors_raw = m.group(1).strip()
        body = m.group(2).strip()

        # Múltiples selectores separados por coma
        for selector in selectors_raw.split(","):
            selector = selector.strip()
            if not selector or selector == ":root":
                continue

            style_dict: dict = {}

            for decl in body.split(";"):
                decl = decl.strip()
                if ":" not in decl:
                    continue
                prop, _, val = decl.partition(":")
                prop = prop.strip().lower()
                val  = val.strip()
                if not prop or not val:
                    continue
                _handle_shorthand(prop, val, style_dict)

            if style_dict:
                # Si el selector ya existe, fusionar
                if selector in rules:
                    rules[selector].update(style_dict)
                else:
                    rules[selector] = style_dict

    return StyleSheet(rules)


def compileFrom(path: str | Path) -> StyleSheet:
    """
    Carga y parsea un archivo CSS externo.

    Ejemplo:
        sheet = compileFrom("estilos.css")
        btn   = ppyce.Button(win, style=sheet["Button"])

    Args:
        path: ruta al archivo .css

    Returns:
        StyleSheet con todos los selectores.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"CSS file not found: {path}")
    return parse_css_string(p.read_text(encoding="utf-8"))