import os
from pathlib import Path
from tempfile import NamedTemporaryFile, gettempdir
import warnings
import zipfile
import tcod
import tcod.event
import tcod.console
import tcod.context
import tcod.tileset
import constants as C
from engine import Engine
import visual_registry

_HEXANY_TILESET_ZIP = "hexanys_roguelike_tiles_0.3.0.zip"
_HEXANY_TILESET_MEMBER = "hexanys_roguelike_tiles_0.3.0/Tilesheets/Transparent/general_transparent.png"
_HEXANY_TILESET_PNG = "general_transparent.png"


def _load_truetype_tileset(active_tileset: str, text_scale_setting: int):
    text_min, text_max, _, _ = visual_registry.scale_bounds(active_tileset)
    text_scale = max(text_min, min(text_max, int(text_scale_setting)))
    tile_px = max(8, int(C.TILE_SIZE * text_scale / 100))
    return tcod.tileset.load_truetype_font(C.FONT_PATH, tile_px, tile_px)


def _load_hexany_tileset_from_zip():
    zip_path = Path(__file__).resolve().parent / "data" / "tilesets" / _HEXANY_TILESET_ZIP
    extracted = Path(gettempdir()) / "pyrl-tilesets" / Path(_HEXANY_TILESET_ZIP).stem / _HEXANY_TILESET_PNG
    extracted.parent.mkdir(parents=True, exist_ok=True)
    if not extracted.exists():
        with zipfile.ZipFile(zip_path) as archive:
            with archive.open(_HEXANY_TILESET_MEMBER) as src:
                tile_data = src.read()
        with NamedTemporaryFile("wb", dir=extracted.parent, delete=False) as tmp_file:
            tmp_file.write(tile_data)
            temp_path = Path(tmp_file.name)
        os.replace(temp_path, extracted)
    return tcod.tileset.load_tilesheet(str(extracted), 32, 8, tcod.tileset.CHARMAP_CP437)


def main() -> None:
    if os.path.exists(C.SAVE_PATH):
        engine = Engine.load_game(C.SAVE_PATH)
    else:
        engine = Engine()
    active_tileset = str(engine.settings.get("active_tileset", "ascii"))
    if active_tileset == "hexany_visual":
        try:
            tileset = _load_hexany_tileset_from_zip()
        except (FileNotFoundError, KeyError, OSError, zipfile.BadZipFile) as exc:
            warnings.warn(f"Hexany tileset load failed, falling back to font tileset: {exc}", RuntimeWarning)
            tileset = _load_truetype_tileset(active_tileset, engine.settings.get("text_scale", 100))
    else:
        tileset = _load_truetype_tileset(active_tileset, engine.settings.get("text_scale", 100))

    with tcod.context.new(
        columns=C.SCREEN_WIDTH,
        rows=C.SCREEN_HEIGHT,
        tileset=tileset,
        title="pyRL  —  a true roguelike",
        vsync=True,
    ) as context:
        console = tcod.console.Console(C.SCREEN_WIDTH, C.SCREEN_HEIGHT, order="C")
        while True:
            events = list(tcod.event.get())
            engine.handle_events(events)
            engine.render(console)
            context.present(console)


if __name__ == "__main__":
    main()
