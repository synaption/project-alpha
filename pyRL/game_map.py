from __future__ import annotations
import numpy as np
from typing import TYPE_CHECKING
import tiles as tile_types
from components import Position, BlocksMovement, Item, Stairs

if TYPE_CHECKING:
    from world import World


class GameMap:
    def __init__(self, world: World, width: int, height: int) -> None:
        self.world = world
        self.width = width
        self.height = height
        self.tiles = np.full((height, width), fill_value=tile_types.WALL, dtype=tile_types.tile_dt)
        self.visible = np.full((height, width), fill_value=False, dtype=bool)
        self.explored = np.full((height, width), fill_value=False, dtype=bool)
        self.downstairs_location: tuple[int, int] = (0, 0)
        self.upstairs_location: tuple[int, int] = (0, 0)
        self.player_start: tuple[int, int] = (0, 0)   # where to place the player on a fresh visit

    def in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height

    def is_walkable(self, x: int, y: int) -> bool:
        return bool(self.tiles["walkable"][y, x])

    def get_blocking_entity(self, x: int, y: int) -> int | None:
        for eid, (pos, _) in self.world.query(Position, BlocksMovement):
            if pos.x == x and pos.y == y:
                return eid
        return None

    def get_items_at(self, x: int, y: int) -> list[int]:
        return [
            eid for eid, (pos, _) in self.world.query(Position, Item)
            if pos.x == x and pos.y == y
        ]

    def get_stairs_at(self, x: int, y: int) -> int | None:
        for eid, (pos, _) in self.world.query(Position, Stairs):
            if pos.x == x and pos.y == y:
                return eid
        return None
