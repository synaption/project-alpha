"""
Faction agents roam the surface, town to town, pursuing simple motivations.

Only the trading caravan exists so far — guard patrols, orc raiders, and any
raid consequences are explicitly deferred.

A caravan is an ordinary FactionAgent entity living in whichever surface zone's
World it currently occupies (approach "F3"). `act_one` walks it toward the edge
of the current zone in the direction of its next town on the circuit; when it
reaches that edge, the ENGINE ferries it into the neighbouring zone's World
(Engine._transfer_boundary_factions, mirroring the player's edge-walk). When its
zone isn't in the active set (player elsewhere) it simply freezes, exactly like a
dungeon monster on an inactive floor — long-absence projection is deferred.
"""
from __future__ import annotations
from typing import TYPE_CHECKING
from components import Position, FactionAgent
from systems.pathing import move_toward

if TYPE_CHECKING:
    from world import World
    from game_map import GameMap
    from game_clock import GameClock
    from message_log import MessageLog


def _sign(n: int) -> int:
    return (n > 0) - (n < 0)


def target_zone(agent: FactionAgent) -> tuple[int, int] | None:
    if not agent.circuit:
        return None
    return agent.circuit[agent.circuit_index % len(agent.circuit)]


def act_one(
    world: World, game_map: GameMap, player: int | None, clock: GameClock, message_log: MessageLog, eid: int,
) -> None:
    """One tile-step of the caravan toward the edge leading to its target town."""
    pos = world.get(eid, Position)
    agent = world.get(eid, FactionAgent)
    if pos is None or agent is None:
        return
    agent.last_ticked = clock.total_minutes

    tgt = target_zone(agent)
    if tgt is None:
        return
    if agent.zone == tgt:
        # Arrived at (this zone is) the target town — head for the next one.
        agent.circuit_index = (agent.circuit_index + 1) % len(agent.circuit)
        tgt = target_zone(agent)
        if agent.zone == tgt:
            return

    # Steer toward the border of the current zone in the target's direction; the
    # engine takes over at the border to cross into the neighbour zone.
    dzx = _sign(tgt[0] - agent.zone[0])
    dzy = _sign(tgt[1] - agent.zone[1])
    wx = (game_map.width - 1) if dzx > 0 else 0 if dzx < 0 else pos.x
    wy = (game_map.height - 1) if dzy > 0 else 0 if dzy < 0 else pos.y
    move_toward(world, game_map, eid, pos, (wx, wy))
