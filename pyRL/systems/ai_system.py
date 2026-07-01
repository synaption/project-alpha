from __future__ import annotations
import random
import numpy as np
import tcod.path
from typing import TYPE_CHECKING
from components import Position, AI, Fighter, BlocksMovement, Name
import color

if TYPE_CHECKING:
    from world import World
    from game_map import GameMap
    from message_log import MessageLog


def act_one(world: World, game_map: GameMap, player: int, message_log: MessageLog, eid: int) -> None:
    """Take one action for a single hostile/confused AI entity (called by the turn scheduler)."""
    from systems.combat_system import attack

    player_pos = world.get(player, Position)
    pos = world.get(eid, Position)
    ai = world.get(eid, AI)
    if player_pos is None or pos is None or ai is None:
        return

    if ai.behavior == "confused":
        _act_confused(world, game_map, player, message_log, eid, pos, ai, attack)
    elif ai.behavior == "hostile":
        if game_map.visible[pos.y, pos.x]:
            _act_hostile(world, game_map, player, player_pos, message_log, eid, pos, attack)


def is_active(game_map: GameMap, pos: Position, ai: AI) -> bool:
    """Whether this AI entity is currently eligible to be scheduled a turn.

    Hostile monsters outside the player's FOV are frozen — they neither act nor
    accumulate a backlog of owed turns while off-screen.
    """
    return ai.behavior != "hostile" or game_map.visible[pos.y, pos.x]


def _act_confused(world, game_map, player, message_log, eid, pos, ai, attack_fn) -> None:
    ai.turns_confused -= 1
    if ai.turns_confused <= 0:
        ai.behavior = "hostile"
        name = world.get(eid, Name)
        message_log.add(
            f"The {name.name if name else 'creature'} is no longer confused!", color.WHITE
        )
        return

    dx, dy = random.choice([(-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1),(0,0)])
    nx, ny = pos.x + dx, pos.y + dy
    if not game_map.in_bounds(nx, ny):
        return
    blocker = game_map.get_blocking_entity(nx, ny)
    if blocker is not None:
        if blocker == player:
            attack_fn(world, eid, player, player, message_log, is_player_attacker=False)
    elif game_map.is_walkable(nx, ny):
        pos.x, pos.y = nx, ny


def _act_hostile(world, game_map, player, player_pos, message_log, eid, pos, attack_fn) -> None:
    dist = abs(pos.x - player_pos.x) + abs(pos.y - player_pos.y)
    if dist <= 1:
        attack_fn(world, eid, player, player, message_log, is_player_attacker=False)
        return

    # Build cost array, inflating cells occupied by other blockers
    cost = np.array(game_map.tiles["walkable"], dtype=np.int8)
    for bid, (bpos, _) in world.query(Position, BlocksMovement):
        if bid != eid and bid != player:
            cost[bpos.y, bpos.x] += 10

    graph = tcod.path.SimpleGraph(cost=cost, cardinal=2, diagonal=3)
    pathfinder = tcod.path.Pathfinder(graph)
    pathfinder.add_root((pos.y, pos.x))
    path = pathfinder.path_to((player_pos.y, player_pos.x)).tolist()

    if len(path) > 1:
        next_y, next_x = path[1]
        if game_map.get_blocking_entity(next_x, next_y) is None:
            pos.x, pos.y = next_x, next_y
