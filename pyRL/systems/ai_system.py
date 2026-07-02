from __future__ import annotations
import random
from typing import TYPE_CHECKING
from components import Position, AI, Name
from systems.pathing import move_toward
import color

if TYPE_CHECKING:
    from world import World
    from game_map import GameMap
    from game_clock import GameClock
    from message_log import MessageLog


def act_one(
    world: World, game_map: GameMap, player: int | None, clock: GameClock, message_log: MessageLog, eid: int,
) -> None:
    """Take one action for a single hostile/confused AI entity (called by the turn scheduler).

    `player` is None when this entity's floor is active (within the dungeon
    depth window) but isn't the floor the player is actually standing on — the
    player entity only ever exists in the current floor's World (see
    Engine._enter_floor), so there's nothing to chase or attack. Confused
    entities still wander in that case; hostiles just stay put and wait.

    `clock` is accepted (but unused here) purely to give every act_one() in
    the game the same signature, so Engine's scheduler can dispatch to
    whichever system an entity belongs to without a special case per kind —
    see Engine._ACT_ONE_BY_TAG.
    """
    from systems.combat_system import attack

    pos = world.get(eid, Position)
    ai = world.get(eid, AI)
    if pos is None or ai is None:
        return

    if ai.behavior == "confused":
        _act_confused(world, game_map, player, message_log, eid, pos, ai, attack)
    elif ai.behavior == "hostile":
        player_pos = world.get(player, Position) if player is not None else None
        if player_pos is not None and game_map.visible[pos.y, pos.x]:
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
    move_toward(world, game_map, eid, pos, (player_pos.x, player_pos.y), exclude=(player,))
