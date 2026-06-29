from __future__ import annotations
import tcod.map
from typing import TYPE_CHECKING
from components import Position

if TYPE_CHECKING:
    from world import World
    from game_map import GameMap


def update_fov(world: World, game_map: GameMap, player: int) -> None:
    pos = world.get(player, Position)
    if pos is None:
        return
    # tcod compute_fov takes (row, col) = (y, x) for C-order arrays
    game_map.visible[:] = tcod.map.compute_fov(
        game_map.tiles["transparent"],
        (pos.y, pos.x),
        radius=8,
    )
    game_map.explored |= game_map.visible
