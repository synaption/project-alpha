from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

_REGISTRY_PATH = Path(__file__).resolve().parent / "data" / "tilesets" / "tilesets.json"
DEFAULT_TEXT_SCALE_MIN = 75
DEFAULT_TEXT_SCALE_MAX = 225
DEFAULT_TILE_SCALE_MIN = 75
DEFAULT_TILE_SCALE_MAX = 200


def _glyph_supported(glyph: str) -> bool:
    try:
        glyph.encode("cp437")
        return True
    except UnicodeEncodeError:
        return False


@lru_cache(maxsize=1)
def _load_registry() -> dict:
    try:
        with _REGISTRY_PATH.open("r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError as exc:
        raise RuntimeError(f"Tileset registry file not found: {_REGISTRY_PATH}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Tileset registry JSON is invalid: {_REGISTRY_PATH}") from exc


def tileset_names() -> list[str]:
    return list(_load_registry()["tilesets"].keys())


def fallback_preset_names() -> list[str]:
    return list(_load_registry().get("fallback_presets", {}).keys())


def normalize_tileset_name(name: str) -> str:
    aliases = _load_registry().get("aliases", {})
    return aliases.get(name, name)


def resolve_tileset_chain(active_tileset: str, fallback_preset: str = "registry_default") -> list[str]:
    registry = _load_registry()
    tilesets = registry["tilesets"]
    active = normalize_tileset_name(active_tileset)
    if active not in tilesets:
        active = registry.get("default_tileset", "ascii")

    chain: list[str] = [active]
    preset = registry.get("fallback_presets", {}).get(fallback_preset, [])
    if preset:
        for name in preset:
            normalized = normalize_tileset_name(name)
            if normalized in tilesets and normalized not in chain:
                chain.append(normalized)
    else:
        for name in tilesets[active].get("fallback_order", []):
            normalized = normalize_tileset_name(name)
            if normalized in tilesets and normalized not in chain:
                chain.append(normalized)

    if "ascii" not in chain and "ascii" in tilesets:
        chain.append("ascii")
    return chain


def resolve_tile_glyph(
    tile_id: str | None,
    ascii_char: str,
    active_tileset: str,
    fallback_preset: str,
) -> str:
    if not tile_id:
        return ascii_char
    registry = _load_registry()
    tilesets = registry["tilesets"]
    for tileset_name in resolve_tileset_chain(active_tileset, fallback_preset):
        mapping = tilesets.get(tileset_name, {}).get("tile_map", {}).get(tile_id)
        glyph = mapping.get("glyph") if mapping else None
        if glyph and _glyph_supported(glyph):
            return glyph
    return ascii_char


def scale_bounds(active_tileset: str) -> tuple[int, int, int, int]:
    registry = _load_registry()
    tilesets = registry["tilesets"]
    active = normalize_tileset_name(active_tileset)
    if active not in tilesets:
        active = registry.get("default_tileset", "ascii")
    rules = tilesets.get(active, {}).get("scale_rules", {})
    text_min = int(rules.get("text_scale_min", DEFAULT_TEXT_SCALE_MIN))
    text_max = int(rules.get("text_scale_max", DEFAULT_TEXT_SCALE_MAX))
    tile_min = int(rules.get("tile_scale_min", DEFAULT_TILE_SCALE_MIN))
    tile_max = int(rules.get("tile_scale_max", DEFAULT_TILE_SCALE_MAX))
    return text_min, text_max, tile_min, tile_max
