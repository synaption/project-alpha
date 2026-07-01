"""
Villager daily routine: sleep, eat, farm, and socialize.

Each villager has Needs (hunger/energy/social) that decay over time, and a
VillagerAI that picks an activity each turn — following a fixed daily schedule
unless a need becomes urgent, in which case it takes priority.
"""
from __future__ import annotations
import random
import numpy as np
import tcod.path
from typing import TYPE_CHECKING
from components import Position, Needs, VillagerAI, BlocksMovement, Name
import systems.farm_system as farm_system
import color

if TYPE_CHECKING:
    from world import World
    from game_map import GameMap
    from game_clock import GameClock
    from message_log import MessageLog

# Rates are per calendar-minute (not per turn), so needs stay paced to the
# calendar itself — they don't drift out of sync if TURN_MINUTES ever changes
# (e.g. stretching the day/night cycle). Tuned so a ~10-hour night fully rests
# a villager and a normal day's activity brings on real hunger/loneliness.
HUNGER_PER_MINUTE = 0.04
SOCIAL_DECAY_PER_MINUTE = 0.03
ENERGY_AWAKE_DRAIN_PER_MINUTE = 0.03
ENERGY_SLEEP_RESTORE_PER_MINUTE = 0.4
HUNGER_EAT_RELIEF_PER_MINUTE = 0.6
SOCIAL_RESTORE_PER_MINUTE = 0.5

HUNGER_URGENT = 75.0
ENERGY_URGENT = 15.0
SOCIAL_URGENT = 20.0

EAT_DURATION = 6
SOCIAL_DURATION = 10


def update_needs(world: World, elapsed_minutes: float) -> None:
    """Decay/restore Needs by however much game-time just passed for everyone,
    independent of how often any individual villager gets a scheduled turn."""
    for _eid, (needs, ai) in world.query(Needs, VillagerAI):
        needs.hunger = min(100.0, needs.hunger + HUNGER_PER_MINUTE * elapsed_minutes)
        if ai.activity == "sleeping":
            needs.energy = min(100.0, needs.energy + ENERGY_SLEEP_RESTORE_PER_MINUTE * elapsed_minutes)
        else:
            needs.energy = max(0.0, needs.energy - ENERGY_AWAKE_DRAIN_PER_MINUTE * elapsed_minutes)
        if ai.activity == "socializing":
            needs.social = min(100.0, needs.social + SOCIAL_RESTORE_PER_MINUTE * elapsed_minutes)
        else:
            needs.social = max(0.0, needs.social - SOCIAL_DECAY_PER_MINUTE * elapsed_minutes)
        if ai.activity == "eating":
            needs.hunger = max(0.0, needs.hunger - HUNGER_EAT_RELIEF_PER_MINUTE * elapsed_minutes)


def act_one(world: World, game_map: GameMap, clock: GameClock, message_log: MessageLog, eid: int) -> None:
    """Take one action for a single villager (called by the turn scheduler)."""
    pos = world.get(eid, Position)
    ai = world.get(eid, VillagerAI)
    needs = world.get(eid, Needs)
    if pos is None or ai is None or needs is None:
        return
    _decide_activity(ai, needs, clock)
    _act(world, game_map, eid, pos, ai, message_log)


def _decide_activity(ai: VillagerAI, needs: Needs, clock: GameClock) -> None:
    if ai.activity_timer > 0:
        ai.activity_timer -= 1
        return  # committed to eating/socializing until the timer elapses

    if clock.is_night:
        ai.activity = "sleeping"
        return

    if needs.energy <= ENERGY_URGENT:
        ai.activity = "sleeping"
        return
    if needs.hunger >= HUNGER_URGENT:
        ai.activity = "eating"
        ai.activity_timer = EAT_DURATION
        return
    if needs.social <= SOCIAL_URGENT:
        ai.activity = "socializing"
        ai.activity_timer = SOCIAL_DURATION
        return

    hour = clock.hour
    if hour in (12, 18):
        ai.activity = "eating"
        ai.activity_timer = EAT_DURATION
    elif 20 <= hour < 22:
        ai.activity = "socializing"
        ai.activity_timer = SOCIAL_DURATION
    elif ai.role == "farmer" and ai.work:
        ai.activity = "working"
    else:
        ai.activity = "wandering"


def _act(world: World, game_map: GameMap, eid: int, pos: Position, ai: VillagerAI, message_log: MessageLog) -> None:
    if ai.activity in ("sleeping", "eating"):
        _move_toward(world, game_map, eid, pos, ai.home)
    elif ai.activity == "socializing":
        _move_toward(world, game_map, eid, pos, ai.social_spot)
    elif ai.activity == "working":
        _do_farm_work(world, game_map, eid, pos, ai, message_log)
    else:
        _wander(world, game_map, eid, pos, ai)


def _do_farm_work(world: World, game_map: GameMap, eid: int, pos: Position, ai: VillagerAI, message_log: MessageLog) -> None:
    target_plot = next((p for p in ai.work if farm_system.needs_attention(world, p)), None)
    if target_plot is None:
        _wander(world, game_map, eid, pos, ai)
        return

    plot_pos = world.get(target_plot, Position)
    if (pos.x, pos.y) == (plot_pos.x, plot_pos.y):
        action = farm_system.tend(world, game_map, target_plot)
        if action and message_log:
            name = world.get(eid, Name)
            message_log.add(f"{name.name if name else 'The farmer'} {farm_system.VERBS[action]}.", color.MSG_STATUS)
    else:
        _move_toward(world, game_map, eid, pos, (plot_pos.x, plot_pos.y))


def _wander(world: World, game_map: GameMap, eid: int, pos: Position, ai: VillagerAI) -> None:
    if ai.wander_target is None or (pos.x, pos.y) == ai.wander_target or random.random() < 0.05:
        tx = max(0, min(game_map.width - 1, pos.x + random.randint(-3, 3)))
        ty = max(0, min(game_map.height - 1, pos.y + random.randint(-3, 3)))
        ai.wander_target = (tx, ty)
    _move_toward(world, game_map, eid, pos, ai.wander_target)


def _move_toward(world: World, game_map: GameMap, eid: int, pos: Position, target: tuple[int, int]) -> None:
    tx, ty = target
    if (pos.x, pos.y) == (tx, ty):
        return

    cost = np.array(game_map.tiles["walkable"], dtype=np.int8)
    for bid, (bpos, _) in world.query(Position, BlocksMovement):
        if bid != eid:
            cost[bpos.y, bpos.x] += 10

    graph = tcod.path.SimpleGraph(cost=cost, cardinal=2, diagonal=3)
    pathfinder = tcod.path.Pathfinder(graph)
    pathfinder.add_root((pos.y, pos.x))
    path = pathfinder.path_to((ty, tx)).tolist()

    if len(path) > 1:
        next_y, next_x = path[1]
        if game_map.get_blocking_entity(next_x, next_y) is None:
            pos.x, pos.y = next_x, next_y
