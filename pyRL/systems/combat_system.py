from __future__ import annotations
from typing import TYPE_CHECKING
from components import Fighter, Name, Renderable, AI, BlocksMovement, Level
import color

if TYPE_CHECKING:
    from world import World
    from message_log import MessageLog


def award_xp(world: World, player: int, xp: int, message_log: MessageLog) -> None:
    lvl = world.get(player, Level)
    if lvl and xp > 0:
        lvl.current_xp += xp
        message_log.add(f"You gain {xp} experience points.", color.MSG_XP)


def kill(world: World, entity: int, player: int, message_log: MessageLog) -> int:
    """Turn entity into a corpse. Returns xp_reward (0 for player death)."""
    fighter = world.get(entity, Fighter)
    xp_reward = fighter.xp_reward if (fighter and entity != player) else 0

    name = world.get(entity, Name)
    name_str = name.name if name else "Something"

    if entity == player:
        message_log.add("You died!", color.MSG_PLAYER_DIE)
    else:
        message_log.add(f"{name_str} is dead!", color.MSG_ENEMY_DIE)
        world.remove_component(entity, AI)
        world.remove_component(entity, BlocksMovement)

    rend = world.get(entity, Renderable)
    if rend:
        rend.char = "%"
        rend.fg = color.CORPSE_FG
        rend.render_order = 0

    if name:
        name.name = f"remains of {name_str}"

    return xp_reward


def attack(
    world: World,
    attacker: int,
    defender: int,
    player: int,
    message_log: MessageLog,
    is_player_attacker: bool,
) -> None:
    atk = world.get(attacker, Fighter)
    dfn = world.get(defender, Fighter)
    if not atk or not dfn:
        return

    damage = max(0, atk.power - dfn.defense)
    atk_name = (world.get(attacker, Name) or Name("Someone")).name
    def_name = (world.get(defender, Name) or Name("Something")).name
    msg_color = color.MSG_PLAYER_ATK if is_player_attacker else color.MSG_ENEMY_ATK

    if damage > 0:
        dfn.hp -= damage
        message_log.add(f"{atk_name} attacks {def_name} for {damage} hit points.", msg_color)
    else:
        message_log.add(f"{atk_name} attacks {def_name} but does no damage.", msg_color)

    if dfn.hp <= 0:
        xp = kill(world, defender, player, message_log)
        if is_player_attacker:
            award_xp(world, player, xp, message_log)
