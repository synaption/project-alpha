"""pyRL2 entry point.

Turn loop: block for an action, run the systems, repeat. The game logic never
touches curses -- swap TerminalRenderer for a tcod/pygame/raylib renderer and
nothing else changes.
"""
import esper

from components import Player, Position, Renderable
from game_map import GameMap
from renderer.terminal import TerminalRenderer
from systems import MovementProcessor, RenderProcessor

MAP_WIDTH = 40
MAP_HEIGHT = 20


def main() -> None:
    game_map = GameMap(MAP_WIDTH, MAP_HEIGHT)

    # Higher priority runs first: move before drawing.
    esper.add_processor(MovementProcessor(game_map), priority=1)

    esper.create_entity(
        Position(MAP_WIDTH // 2, MAP_HEIGHT // 2),
        Renderable("@"),
        Player(),
    )

    with TerminalRenderer() as renderer:
        esper.add_processor(RenderProcessor(renderer, game_map), priority=0)

        esper.process()  # initial frame
        while True:
            action = renderer.poll_action()
            if action == "quit":
                break
            esper.process(action)


if __name__ == "__main__":
    main()
