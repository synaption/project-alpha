from __future__ import annotations
import numpy as np
from typing import TYPE_CHECKING
import tiles as tile_types
import color
import constants as C
from components import Position, Renderable, Fighter, Level

if TYPE_CHECKING:
    from world import World
    from game_map import GameMap
    from message_log import MessageLog
    import tcod.console


def render_all(
    console: tcod.console.Console,
    world: World,
    game_map: GameMap,
    player: int,
    message_log: MessageLog,
    floor: int,
) -> None:
    console.clear()
    _render_map(console, game_map)
    _render_entities(console, world, game_map)
    _render_ui(console, world, player, message_log, floor)


def _render_map(console, game_map: GameMap) -> None:
    console.rgb[0:game_map.height, 0:game_map.width] = np.select(
        condlist=[game_map.visible, game_map.explored],
        choicelist=[game_map.tiles["light"], game_map.tiles["dark"]],
        default=tile_types.SHROUD,
    )


def _render_entities(console, world: World, game_map: GameMap) -> None:
    for eid, (pos, rend) in sorted(
        world.query(Position, Renderable), key=lambda e: e[1][1].render_order
    ):
        if game_map.in_bounds(pos.x, pos.y) and game_map.visible[pos.y, pos.x]:
            console.rgb["ch"][pos.y, pos.x] = ord(rend.char)
            console.rgb["fg"][pos.y, pos.x] = rend.fg


def _render_ui(console, world: World, player: int, message_log: MessageLog, floor: int) -> None:
    py = C.PANEL_Y
    fighter = world.get(player, Fighter)
    if fighter:
        _render_bar(
            console, x=1, y=py + 1,
            current=fighter.hp, maximum=fighter.max_hp,
            total_width=C.BAR_WIDTH,
            label="HP",
            fg_full=color.HP_FULL,
            fg_empty=color.HP_EMPTY,
        )

    lvl = world.get(player, Level)
    if lvl:
        console.print(x=1, y=py + 3, string=f"Lv:{lvl.current_level}  XP:{lvl.current_xp}/{lvl.xp_to_next}", fg=color.WHITE)

    console.print(x=1, y=py + 4, string=f"Dungeon floor: {floor}", fg=color.WHITE)

    message_log.render(console, x=C.MSG_X, y=py, width=C.MSG_WIDTH, height=C.MSG_HEIGHT)


def _render_bar(
    console,
    x: int, y: int,
    current: int, maximum: int,
    total_width: int,
    label: str,
    fg_full: tuple,
    fg_empty: tuple,
) -> None:
    bar_width = max(0, int(current / maximum * total_width))
    console.draw_rect(x=x, y=y, width=total_width, height=1, ch=ord(" "), bg=fg_empty)
    if bar_width > 0:
        console.draw_rect(x=x, y=y, width=bar_width, height=1, ch=ord(" "), bg=fg_full)
    console.print(x=x, y=y, string=f"{label}: {current}/{maximum}", fg=color.WHITE)


def render_inventory(console, world: World, player: int, title: str) -> None:
    inv_comp = world.get(player, __import__("components").Inventory)
    items = inv_comp.items if inv_comp else []
    height = max(3, len(items) + 2)
    x, y, w = 5, 5, 40
    console.draw_frame(x=x, y=y, width=w, height=height, title=title, fg=color.WHITE, bg=color.BLACK)
    if not items:
        console.print(x=x + 1, y=y + 1, string="(empty)", fg=color.GRAY)
    for i, item_id in enumerate(items):
        name = world.get(item_id, __import__("components").Name)
        letter = chr(ord("a") + i)
        console.print(
            x=x + 1, y=y + 1 + i,
            string=f"({letter}) {name.name if name else '?'}",
            fg=color.WHITE,
        )


def render_level_up(console, world: World, player: int) -> None:
    fighter = world.get(player, Fighter)
    x, y, w = 5, 5, 44
    console.draw_frame(x=x, y=y, width=w, height=8, title="Level Up!", fg=color.YELLOW, bg=color.BLACK)
    console.print(x=x+1, y=y+1, string="You have gained a level!", fg=color.WHITE)
    console.print(x=x+1, y=y+2, string="Choose an attribute to increase:", fg=color.WHITE)
    console.print(x=x+1, y=y+4, string=f"(a) +20 Max HP   (current: {fighter.max_hp})", fg=color.WHITE)
    console.print(x=x+1, y=y+5, string=f"(b) +1 Attack    (current: {fighter.power})", fg=color.WHITE)
    console.print(x=x+1, y=y+6, string=f"(c) +1 Defense   (current: {fighter.defense})", fg=color.WHITE)
