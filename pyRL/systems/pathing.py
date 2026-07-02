"""
Shared A* single-step pathing toward a target tile.

Used by ai_system (hostiles chasing the player), villager_system (villagers
walking to home/social spot/farm plots), and faction_system (faction agents
traveling between towns) — all three want the same "one step toward a target,
other blockers cost extra rather than being impassable" behavior.
"""
from __future__ import annotations
import numpy as np
import tcod.path
from typing import TYPE_CHECKING
from components import Position, BlocksMovement

if TYPE_CHECKING:
    from world import World
    from game_map import GameMap


def move_toward(
    world: World,
    game_map: GameMap,
    eid: int,
    pos: Position,
    target: tuple[int, int],
    exclude: tuple[int, ...] = (),
) -> None:
    """Step eid one tile closer to target via A*.

    Other BlocksMovement entities inflate a tile's cost rather than making it
    impassable, so a crowd doesn't fully block pathing. `exclude` lets a caller
    keep specific entities (e.g. the player, for a hostile that wants to path
    right up to them) from being costed at all.
    """
    tx, ty = target
    if (pos.x, pos.y) == (tx, ty):
        return

    cost = np.array(game_map.tiles["walkable"], dtype=np.int8)
    skip = set(exclude)
    skip.add(eid)
    for bid, (bpos, _) in world.query(Position, BlocksMovement):
        if bid not in skip:
            cost[bpos.y, bpos.x] += 10

    graph = tcod.path.SimpleGraph(cost=cost, cardinal=2, diagonal=3)
    pathfinder = tcod.path.Pathfinder(graph)
    pathfinder.add_root((pos.y, pos.x))
    path = pathfinder.path_to((ty, tx)).tolist()

    if len(path) > 1:
        next_y, next_x = path[1]
        if game_map.get_blocking_entity(next_x, next_y) is None:
            pos.x, pos.y = next_x, next_y
