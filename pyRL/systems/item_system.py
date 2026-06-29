from __future__ import annotations
from typing import TYPE_CHECKING
from components import Fighter, AI, Name, Position
import color

if TYPE_CHECKING:
    from world import World
    from game_map import GameMap
    from message_log import MessageLog

LIGHTNING_RANGE = 5
LIGHTNING_DAMAGE = 20
FIREBALL_RADIUS = 3
FIREBALL_DAMAGE = 12
CONFUSION_DURATION = 10
HEAL_AMOUNT = 40


def _nearest_visible_enemy(
    world: World, user: int, game_map: GameMap
) -> tuple[int | None, float]:
    pos = world.get(user, Position)
    best: int | None = None
    best_dist = float("inf")
    for eid, (epos, _) in world.query(Position, AI):
        if game_map.visible[epos.y, epos.x]:
            dist = abs(epos.x - pos.x) + abs(epos.y - pos.y)
            if dist < best_dist:
                best_dist = dist
                best = eid
    return best, best_dist


def use_health_potion(
    world: World, user: int, target: int | None, game_map: GameMap, message_log: MessageLog
) -> bool:
    fighter = world.get(user, Fighter)
    if fighter is None:
        return False
    if fighter.hp >= fighter.max_hp:
        message_log.add("Your health is already full.", color.INVALID)
        return False
    healed = fighter.heal(HEAL_AMOUNT)
    message_log.add(f"You consume the health potion, recovering {healed} HP!", color.MSG_HEAL)
    return True


def use_lightning_scroll(
    world: World, user: int, target: int | None, game_map: GameMap, message_log: MessageLog
) -> bool:
    best, dist = _nearest_visible_enemy(world, user, game_map)
    if best is None or dist > LIGHTNING_RANGE:
        message_log.add("No close enough target.", color.INVALID)
        return False

    name = world.get(best, Name)
    fighter = world.get(best, Fighter)
    message_log.add(
        f"A lightning bolt strikes the {name.name if name else 'creature'} "
        f"for {LIGHTNING_DAMAGE} damage!",
        color.LIGHTNING_SCROLL_FG,
    )
    fighter.hp -= LIGHTNING_DAMAGE
    if fighter.hp <= 0:
        from systems.combat_system import kill, award_xp
        xp = kill(world, best, user, message_log)
        award_xp(world, user, xp, message_log)
    return True


def use_fireball_scroll(
    world: World, user: int, target: int | None, game_map: GameMap, message_log: MessageLog
) -> bool:
    best, _ = _nearest_visible_enemy(world, user, game_map)
    if best is None:
        message_log.add("No visible targets.", color.INVALID)
        return False

    tpos = world.get(best, Position)
    tx, ty = tpos.x, tpos.y
    message_log.add(
        f"The fireball explodes, burning everything within {FIREBALL_RADIUS} tiles!",
        color.FIREBALL_SCROLL_FG,
    )

    from systems.combat_system import kill, award_xp
    for eid, (pos, fighter) in list(world.query(Position, Fighter)):
        if abs(pos.x - tx) <= FIREBALL_RADIUS and abs(pos.y - ty) <= FIREBALL_RADIUS:
            name = world.get(eid, Name)
            message_log.add(
                f"The {name.name if name else 'creature'} takes {FIREBALL_DAMAGE} fire damage.",
                color.FIREBALL_SCROLL_FG,
            )
            fighter.hp -= FIREBALL_DAMAGE
            if fighter.hp <= 0:
                xp = kill(world, eid, user, message_log)
                award_xp(world, user, xp, message_log)
    return True


def use_confusion_scroll(
    world: World, user: int, target: int | None, game_map: GameMap, message_log: MessageLog
) -> bool:
    best, _ = _nearest_visible_enemy(world, user, game_map)
    if best is None:
        message_log.add("No visible target.", color.INVALID)
        return False

    ai = world.get(best, AI)
    name = world.get(best, Name)
    ai.behavior = "confused"
    ai.turns_confused = CONFUSION_DURATION
    message_log.add(
        f"The {name.name if name else 'creature'} starts stumbling around!",
        color.MSG_STATUS,
    )
    return True
