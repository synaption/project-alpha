import os
import tcod
import tcod.event
import tcod.console
import tcod.context
import tcod.tileset
import constants as C
from engine import Engine
import visual_registry

def _load_truetype_tileset(active_tileset: str, text_scale_setting: int):
    text_min, text_max, _, _ = visual_registry.scale_bounds(active_tileset)
    text_scale = max(text_min, min(text_max, int(text_scale_setting)))
    tile_px = max(8, int(C.TILE_SIZE * text_scale / 100))
    return tcod.tileset.load_truetype_font(C.FONT_PATH, tile_px, tile_px)


def main() -> None:
    if os.path.exists(C.SAVE_PATH):
        engine = Engine.load_game(C.SAVE_PATH)
    else:
        engine = Engine()
    active_tileset = str(engine.settings.get("active_tileset", "ascii"))
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
