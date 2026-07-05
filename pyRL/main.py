import os
import zipfile
from pathlib import Path
import tcod
import tcod.event
import tcod.console
import tcod.context
import tcod.tileset
import constants as C
from engine import Engine
import visual_registry

_PYRL_DIR = Path(__file__).resolve().parent
_HEXANY_ZIP_PATH = _PYRL_DIR / "data" / "tilesets" / "hexanys_roguelike_tiles_0.3.0.zip"
_HEXANY_DIRNAME = "hexanys_roguelike_tiles_0.3.0"
_HEXANY_CACHE_ROOT = Path.home() / ".cache" / "pyrl" / "hexany-tiles"
_HEXANY_SHEETS = {
    "general": ("Tilesheets/Transparent/general_transparent.png", 32, 8),
    "items": ("Tilesheets/Transparent/items_transparent.png", 24, 8),
    "creatures": ("Tilesheets/Transparent/creatures_transparent.png", 16, 20),
}
_HEXANY_GLYPH_OVERRIDES = {
    "•": ("general", 0, 1),     # floor
    "█": ("general", 1, 24),    # wall
    "·": ("general", 1, 0),     # grass/indoor/dirt/seed
    "◦": ("general", 1, 22),    # cobblestone
    "▪": ("general", 1, 21),    # wet dirt
    "╪": ("general", 0, 30),    # door
    "▾": ("general", 1, 15),    # down stairs
    "▴": ("general", 1, 14),    # up stairs
    "♠": ("general", 1, 2),     # forest
    "⌂": ("items", 4, 3),       # town entrance
    "∿": ("general", 0, 13),    # water
    "▲": ("general", 2, 4),     # mountain
    "☺": ("creatures", 0, 0),   # player
    "☻": ("creatures", 0, 1),   # villager
    "ɸ": ("creatures", 3, 0),   # orc
    "ϟ": ("creatures", 4, 0),   # troll
    "◉": ("general", 1, 13),    # well
    "♘": ("creatures", 2, 8),   # caravan
    "✚": ("items", 3, 10),      # health potion
    "⌁": ("items", 1, 12),      # scrolls
    "‚": ("general", 2, 1),     # crop sprout
    "❞": ("general", 1, 7),     # crop growing
    "✿": ("general", 1, 3),     # crop ripe
}


def _resolve_tile_px(active_tileset: str, text_scale_setting: int) -> int:
    text_min, text_max, _, _ = visual_registry.scale_bounds(active_tileset)
    text_scale = max(text_min, min(text_max, int(text_scale_setting)))
    return max(8, int(C.TILE_SIZE * text_scale / 100))


def _load_truetype_tileset(active_tileset: str, text_scale_setting: int):
    tile_px = _resolve_tile_px(active_tileset, text_scale_setting)
    return tcod.tileset.load_truetype_font(C.FONT_PATH, tile_px, tile_px)


def _resolve_hexany_asset_root() -> Path | None:
    extracted_root = _HEXANY_ZIP_PATH.parent / _HEXANY_DIRNAME
    if (extracted_root / "Tilesheets" / "Transparent" / "general_transparent.png").exists():
        return extracted_root
    if not _HEXANY_ZIP_PATH.exists():
        return None
    target_root = _HEXANY_CACHE_ROOT / _HEXANY_DIRNAME
    if (target_root / "Tilesheets" / "Transparent" / "general_transparent.png").exists():
        return target_root
    _HEXANY_CACHE_ROOT.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(_HEXANY_ZIP_PATH) as archive:
        archive.extractall(_HEXANY_CACHE_ROOT)
    if (target_root / "Tilesheets" / "Transparent" / "general_transparent.png").exists():
        return target_root
    return None


def _load_hexany_sheet(sheet_path: Path, columns: int, rows: int) -> tcod.tileset.Tileset:
    return tcod.tileset.load_tilesheet(
        sheet_path,
        columns=columns,
        rows=rows,
        charmap=tuple(range(columns * rows)),
    )


def _apply_hexany_bitmap_overrides(base_tileset: tcod.tileset.Tileset, assets_root: Path) -> None:
    loaded_sheets: dict[str, tuple[tcod.tileset.Tileset, int]] = {}
    for glyph, (sheet_name, row, col) in _HEXANY_GLYPH_OVERRIDES.items():
        if sheet_name not in loaded_sheets:
            rel_path, columns, rows = _HEXANY_SHEETS[sheet_name]
            sheet_tileset = _load_hexany_sheet(assets_root / rel_path, columns, rows)
            loaded_sheets[sheet_name] = (sheet_tileset, columns)
        sheet_tileset, columns = loaded_sheets[sheet_name]
        sheet_codepoint = row * columns + col
        base_tileset.set_tile(ord(glyph), sheet_tileset.get_tile(sheet_codepoint))


def _load_tileset(active_tileset: str, text_scale_setting: int) -> tcod.tileset.Tileset:
    tileset = _load_truetype_tileset(active_tileset, text_scale_setting)
    if visual_registry.normalize_tileset_name(active_tileset) != "hexany_visual":
        return tileset
    assets_root = _resolve_hexany_asset_root()
    if assets_root is None:
        return tileset
    try:
        _apply_hexany_bitmap_overrides(tileset, assets_root)
    except (FileNotFoundError, OSError, RuntimeError, ValueError):
        return tileset
    return tileset


def main() -> None:
    if os.path.exists(C.SAVE_PATH):
        engine = Engine.load_game(C.SAVE_PATH)
    else:
        engine = Engine()
    active_tileset = str(engine.settings.get("active_tileset", "ascii"))
    text_scale = int(engine.settings.get("text_scale", 100))
    tile_px = _resolve_tile_px(active_tileset, text_scale)
    render_scale = max(1, int(engine.settings.get("render_scale", 2)))
    tileset = _load_tileset(active_tileset, text_scale)

    with tcod.context.new(
        columns=C.SCREEN_WIDTH,
        rows=C.SCREEN_HEIGHT,
        tileset=tileset,
        width=C.SCREEN_WIDTH * tile_px * render_scale,
        height=C.SCREEN_HEIGHT * tile_px * render_scale,
        title="pyRL  —  a true roguelike",
        vsync=True,
    ) as context:
        console = tcod.console.Console(C.SCREEN_WIDTH, C.SCREEN_HEIGHT, order="C")
        while True:
            events = list(tcod.event.get())
            engine.handle_events(events)
            engine.render(console)
            context.present(console, keep_aspect=True, integer_scaling=True)


if __name__ == "__main__":
    main()
