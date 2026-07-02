from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import color

_PALETTE_PATH = Path(__file__).resolve().parent / "data" / "palettes" / "palettes.json"
_BASE_COLORS = {
    name: value
    for name, value in vars(color).items()
    if name.isupper() and isinstance(value, tuple) and len(value) == 3
}
_ACTIVE_RGB_MAP: dict[tuple[int, int, int], tuple[int, int, int]] = {}


@lru_cache(maxsize=1)
def _load_palettes() -> dict:
    try:
        with _PALETTE_PATH.open("r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError as exc:
        raise RuntimeError(f"Palette file not found: {_PALETTE_PATH}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Palette JSON is invalid: {_PALETTE_PATH}") from exc


def palette_names() -> list[str]:
    palettes = _load_palettes().get("palettes", {})
    return list(palettes.keys()) or ["classic"]


def apply_palette(name: str) -> str:
    palettes = _load_palettes().get("palettes", {})
    if name not in palettes:
        name = _load_palettes().get("default_palette", "classic")
    overrides = palettes.get(name, {})

    for const_name, base_value in _BASE_COLORS.items():
        override = overrides.get(const_name)
        if override is not None:
            setattr(color, const_name, tuple(int(c) for c in override))
        else:
            setattr(color, const_name, base_value)

    global _ACTIVE_RGB_MAP
    _ACTIVE_RGB_MAP = {}
    for const_name, base_value in _BASE_COLORS.items():
        target_value = getattr(color, const_name, base_value)
        if target_value != base_value:
            _ACTIVE_RGB_MAP[base_value] = target_value
    return name


def transform_rgb(rgb: tuple[int, int, int]) -> tuple[int, int, int]:
    return _ACTIVE_RGB_MAP.get(rgb, rgb)


def transform_rgb_array(arr) -> None:
    if not _ACTIVE_RGB_MAP:
        return
    for src, dst in _ACTIVE_RGB_MAP.items():
        mask = (arr[:, :, 0] == src[0]) & (arr[:, :, 1] == src[1]) & (arr[:, :, 2] == src[2])
        arr[mask] = dst
