import os
import tcod
import tcod.event
import tcod.console
import tcod.context
import tcod.tileset
import constants as C
from engine import Engine


def main() -> None:
    tileset = tcod.tileset.load_truetype_font(C.FONT_PATH, C.TILE_SIZE, C.TILE_SIZE)
    if os.path.exists(C.SAVE_PATH):
        engine = Engine.load_game(C.SAVE_PATH)
    else:
        engine = Engine()

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
