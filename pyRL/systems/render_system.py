from __future__ import annotations
import numpy as np
import textwrap
from typing import TYPE_CHECKING
import tiles as tile_types
import color
import constants as C
import palette_registry
import visual_registry
from components import Position, Renderable, Fighter, Level, Inventory, Name, Location
import tile_ids as TID

if TYPE_CHECKING:
    from world import World
    from game_map import GameMap
    from message_log import MessageLog
    from game_clock import GameClock
    import tcod.console


def render_all(
    console: tcod.console.Console,
    world: World,
    game_map: GameMap,
    player: int,
    message_log: MessageLog,
    location: Location,
    clock: GameClock | None = None,
    active_tileset: str = "ascii",
    fallback_preset: str = "registry_default",
    tile_scale: int = 100,
) -> None:
    console.clear()
    outdoors = location.kind == "surface"
    light = clock.light_level() if (clock is not None and outdoors) else 1.0
    _render_map(console, game_map, light, active_tileset, fallback_preset, tile_scale)
    _render_entities(console, world, game_map, light, active_tileset, fallback_preset, tile_scale)
    _render_ui(console, world, player, message_log, location, clock)


def _scale_char(ch: str, tile_scale: int) -> str:
    if tile_scale >= 150:
        return {
            ".": "•",
            "·": "•",
            ",": "▪",
            "~": "≈",
            "▾": "▼",
            "▴": "▲",
        }.get(ch, ch)
    if tile_scale <= 75:
        return {
            "•": "·",
            "█": "▓",
            "▼": "▾",
            "▲": "▴",
        }.get(ch, ch)
    return ch


def _styled_char(
    ch: str,
    tile_id: str,
    active_tileset: str,
    fallback_preset: str,
    tile_scale: int,
) -> str:
    glyph = visual_registry.resolve_tile_glyph(tile_id, ch, active_tileset, fallback_preset)
    return _scale_char(glyph, tile_scale)


_LEGACY_CHAR_TILE_IDS = {
    ".": TID.MAP_FLOOR,
    "#": TID.MAP_WALL,
    "^": TID.MAP_FOREST,
    "A": TID.MAP_TOWN_ENTRANCE,
    "~": TID.MAP_WATER,
    "+": TID.MAP_DOOR,
    ">": TID.MAP_DOWN_STAIRS,
    "<": TID.MAP_UP_STAIRS,
}


def _render_map(
    console,
    game_map: GameMap,
    light: float = 1.0,
    active_tileset: str = "ascii",
    fallback_preset: str = "registry_default",
    tile_scale: int = 100,
) -> None:
    composite = np.select(
        condlist=[game_map.visible, game_map.explored],
        choicelist=[game_map.tiles["light"], game_map.tiles["dark"]],
        default=tile_types.SHROUD,
    )
    composite = composite.copy()
    h, w = game_map.height, game_map.width
    # Backward compatibility: older saves may have tiles without tile_id.
    has_tile_id = "tile_id" in composite.dtype.names
    for y in range(h):
        for x in range(w):
            tile_id = composite["tile_id"][y, x] if has_tile_id else ""
            base_char = chr(int(composite["ch"][y, x]))
            if not tile_id:
                tile_id = _LEGACY_CHAR_TILE_IDS.get(base_char, "")
            styled = base_char if not tile_id else _styled_char(
                base_char, tile_id, active_tileset, fallback_preset, tile_scale
            )
            composite["ch"][y, x] = ord(styled)
    if light < 1.0:
        dim_mask = game_map.visible
        composite["fg"][dim_mask] = (composite["fg"][dim_mask] * light).astype(np.uint8)
        composite["bg"][dim_mask] = (composite["bg"][dim_mask] * light).astype(np.uint8)
    palette_registry.transform_rgb_array(composite["fg"])
    composite["bg"][:] = (0, 0, 0)
    region = console.rgb[0:h, 0:w]
    for field in ("ch", "fg", "bg"):
        region[field] = composite[field]


def _render_entities(
    console,
    world: World,
    game_map: GameMap,
    light: float = 1.0,
    active_tileset: str = "ascii",
    fallback_preset: str = "registry_default",
    tile_scale: int = 100,
) -> None:
    for eid, (pos, rend) in sorted(
        world.query(Position, Renderable), key=lambda e: e[1][1].render_order
    ):
        if game_map.in_bounds(pos.x, pos.y) and game_map.visible[pos.y, pos.x]:
            console.rgb["ch"][pos.y, pos.x] = ord(
                _styled_char(
                    rend.char,
                    getattr(rend, "tile_id", ""),
                    active_tileset,
                    fallback_preset,
                    tile_scale,
                )
            )
            fg = rend.fg if light >= 1.0 else tuple(int(c * light) for c in rend.fg)
            console.rgb["fg"][pos.y, pos.x] = palette_registry.transform_rgb(fg)


def _render_ui(console, world: World, player: int, message_log: MessageLog, location: Location, clock: GameClock | None = None) -> None:
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

    if location.kind == "surface":
        location_label = location.site.title() if location.site else "The Wilds"
    else:
        location_label = f"{location.site.title()} Depths, level {location.depth}"
    console.print(x=1, y=py + 4, string=location_label, fg=color.WHITE)

    if clock is not None:
        period = "Night" if clock.is_night else "Day"
        console.print(x=1, y=py + 5, string=f"{clock.time_string()}  ({period})", fg=color.WHITE)
        console.print(x=1, y=py + 6, string=clock.weekday, fg=color.GRAY)

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


def render_inventory(console, world: World, inventory_world: World, player: int, title: str) -> None:
    """`player`'s Inventory lives on the current floor's world; the carried items
    themselves live in the separate, floor-independent inventory_world (see
    Engine.inventory_world) — items must survive moving between floors' Worlds."""
    inv_comp = world.get(player, Inventory)
    items = inv_comp.items if inv_comp else []
    height = max(3, len(items) + 2)
    x, y, w = 5, 5, 40
    console.draw_frame(x=x, y=y, width=w, height=height, title=title, fg=color.WHITE, bg=color.BLACK)
    if not items:
        console.print(x=x + 1, y=y + 1, string="(empty)", fg=color.GRAY)
    for i, item_id in enumerate(items):
        name = inventory_world.get(item_id, Name)
        letter = chr(ord("a") + i)
        console.print(
            x=x + 1, y=y + 1 + i,
            string=f"({letter}) {name.name if name else '?'}",
            fg=color.WHITE,
        )


def render_world_map(console, player_cell, cursor, discovered, town_cells) -> None:
    """The zoomed-out overworld: one glyph per world cell. Fast-travel screen."""
    console.clear()
    ox, oy = 4, 3
    console.print(x=ox, y=1, string="World Map  —  arrows/hjkl move, Enter travel, Esc/m close", fg=color.WHITE)
    for cy in range(C.WORLD_CELLS_H):
        for cx in range(C.WORLD_CELLS_W):
            cell = (cx, cy)
            gx, gy = ox + cx * 2, oy + cy
            if cell == player_cell:
                ch, fg = "@", color.WORLDMAP_PLAYER
            elif cell in town_cells:
                ch, fg = ("A", color.WORLDMAP_TOWN) if cell in discovered else ("?", color.WORLDMAP_UNKNOWN)
            elif cell in discovered:
                ch, fg = ".", color.WORLDMAP_KNOWN
            else:
                ch, fg = " ", color.WORLDMAP_UNKNOWN
            bg = color.WORLDMAP_CURSOR if cell == cursor else color.BLACK
            console.print(x=gx, y=gy, string=ch, fg=fg, bg=bg)
    site = town_cells.get(cursor)
    if cursor in discovered and site:
        label = site.title()
    elif cursor in discovered:
        label = "Wilderness"
    else:
        label = "Undiscovered"
    console.print(x=ox, y=oy + C.WORLD_CELLS_H + 1, string=f"Cursor: {label}", fg=color.WHITE)


def render_dialog(console, speaker_name: str, lines: list[str], current_line: int, activity: str | None = None) -> None:
    line = lines[current_line % len(lines)]
    w, h = 70, 7
    x = (C.SCREEN_WIDTH - w) // 2
    y = 28
    console.draw_frame(
        x=x, y=y, width=w, height=h,
        title=f" {speaker_name} ",
        fg=color.DIALOG_BORDER, bg=color.BLACK,
    )
    text_start = y + 1
    if activity:
        console.print(x=x + 2, y=y + 1, string=f"({activity})", fg=color.GRAY)
        text_start += 1
    wrapped = textwrap.wrap(f'"{line}"', w - 4)
    max_lines = y + h - 2 - text_start
    for i, wline in enumerate(wrapped[:max_lines]):
        console.print(x=x + 2, y=text_start + i, string=wline, fg=color.WHITE)
    more = f"[{current_line + 1}/{len(lines)}  any key]"
    console.print(x=x + w - len(more) - 2, y=y + h - 2, string=more, fg=color.GRAY)


def render_level_up(console, world: World, player: int) -> None:
    fighter = world.get(player, Fighter)
    x, y, w = 5, 5, 44
    console.draw_frame(x=x, y=y, width=w, height=8, title="Level Up!", fg=color.YELLOW, bg=color.BLACK)
    console.print(x=x+1, y=y+1, string="You have gained a level!", fg=color.WHITE)
    console.print(x=x+1, y=y+2, string="Choose an attribute to increase:", fg=color.WHITE)
    console.print(x=x+1, y=y+4, string=f"(a) +20 Max HP   (current: {fighter.max_hp})", fg=color.WHITE)
    console.print(x=x+1, y=y+5, string=f"(b) +1 Attack    (current: {fighter.power})", fg=color.WHITE)
    console.print(x=x+1, y=y+6, string=f"(c) +1 Defense   (current: {fighter.defense})", fg=color.WHITE)


def _menu_frame(console, title: str, width: int, height: int) -> tuple[int, int]:
    x = (C.SCREEN_WIDTH - width) // 2
    y = (C.SCREEN_HEIGHT - height) // 2
    console.draw_frame(x=x, y=y, width=width, height=height, title=title, fg=color.WHITE, bg=color.BLACK)
    return x, y


def render_opening_screen(console) -> None:
    console.clear()
    logo = [
        "██████╗ ██╗   ██╗██████╗ ██╗     ",
        "██╔══██╗╚██╗ ██╔╝██╔══██╗██║     ",
        "██████╔╝ ╚████╔╝ ██████╔╝██║     ",
        "██╔═══╝   ╚██╔╝  ██╔══██╗██║     ",
        "██║        ██║   ██║  ██║███████╗",
        "╚═╝        ╚═╝   ╚═╝  ╚═╝╚══════╝",
    ]
    start_y = 10
    for i, line in enumerate(logo):
        x = max(0, (C.SCREEN_WIDTH - len(line)) // 2)
        console.print(x=x, y=start_y + i, string=line, fg=color.MSG_LEVEL_UP)
    title = "A True Roguelike Adventure"
    tx = max(0, (C.SCREEN_WIDTH - len(title)) // 2)
    console.print(x=tx, y=start_y + len(logo) + 2, string=title, fg=color.WHITE)
    hint = "Press any key to continue"
    hx = max(0, (C.SCREEN_WIDTH - len(hint)) // 2)
    console.print(x=hx, y=start_y + len(logo) + 6, string=hint, fg=color.GRAY)


def render_home_menu(console, items: list[str], selected: int) -> None:
    console.clear()
    x, y = _menu_frame(console, " pyRL ", 44, 14)
    subtitle = "Home"
    sx = x + (44 - len(subtitle)) // 2
    console.print(x=sx, y=y + 2, string=subtitle, fg=color.WHITE)
    for i, item in enumerate(items):
        fg = color.BLACK if i == selected else color.WHITE
        bg = color.WORLDMAP_CURSOR if i == selected else color.BLACK
        console.print(x=x + 3, y=y + 4 + i, string=item.ljust(36), fg=fg, bg=bg)


def render_pause_menu(console, items: list[str], selected: int) -> None:
    x, y = _menu_frame(console, " Pause Menu ", 50, 16)
    for i, item in enumerate(items):
        fg = color.BLACK if i == selected else color.WHITE
        bg = color.WORLDMAP_CURSOR if i == selected else color.BLACK
        console.print(x=x + 3, y=y + 2 + i, string=item.ljust(42), fg=fg, bg=bg)
    console.print(x=x + 3, y=y + 13, string="Use arrows + Enter. Esc resumes game.", fg=color.GRAY)


def render_options_menu(console, settings: dict[str, object], selected: int) -> None:
    x, y = _menu_frame(console, " Options ", 72, 22)
    rows = [
        f"Display Mode: {settings['display_mode']}",
        f"Render Scale: {settings['render_scale']}x",
        f"Brightness: {settings['brightness']}%",
        f"Master Volume: {settings['master_volume']}%",
        f"Music Volume: {settings['music_volume']}%",
        f"SFX Volume: {settings['sfx_volume']}%",
        f"Active Tileset: {settings['active_tileset']}",
        f"Tileset Fallback: {settings['tileset_fallback_preset']}",
        f"Text Scale: {settings['text_scale']}%",
        f"Tile Scale: {settings['tile_scale']}%",
        f"Palette: {settings['active_palette']}",
        "Controls: open bindings menu",
        f"Control Scheme: {settings['control_scheme']}",
    ]
    for i, row in enumerate(rows):
        fg = color.BLACK if i == selected else color.WHITE
        bg = color.WORLDMAP_CURSOR if i == selected else color.BLACK
        console.print(x=x + 2, y=y + 2 + i, string=row.ljust(66), fg=fg, bg=bg)
    console.print(x=x + 2, y=y + 17, string="Left/Right adjust. Enter opens Controls on that row.", fg=color.GRAY)
    console.print(x=x + 2, y=y + 18, string="Text scale applies on restart. Palette updates immediately.", fg=color.GRAY)
    console.print(x=x + 2, y=y + 19, string="Esc returns to previous menu.", fg=color.GRAY)


def render_controls_menu(console, control_scheme: str) -> None:
    x, y = _menu_frame(console, " Controls ", 72, 20)
    lines = [
        f"Active scheme: {control_scheme}",
        "",
        "Keyboard + Mouse",
        "  Move: Arrow keys / HJKL / Numpad",
        "  Interact/Pickup: G",
        "  Inventory: I",
        "  Drop: D",
        "  Pause: Esc",
        "  In-game menu: Tab",
        "",
        "Controller (planned mapping)",
        "  Left Stick / D-pad: Move",
        "  A: Interact / Select",
        "  B: Back / Pause",
        "  X: Inventory",
        "  Y: In-game menu",
    ]
    for i, line in enumerate(lines):
        console.print(x=x + 2, y=y + 2 + i, string=line, fg=color.WHITE if line else color.GRAY)
    console.print(x=x + 2, y=y + 18, string="Press Esc to return to Options.", fg=color.GRAY)


def render_ingame_menu(
    console,
    section_index: int,
    sections: list[str],
    world: World,
    inventory_world: World,
    player: int,
    location: Location,
    discovered_cells: set[tuple[int, int]],
    active_quests: list[str],
) -> None:
    x, y = _menu_frame(console, " In-Game Menu ", 72, 24)
    tab_x = x + 2
    for i, section in enumerate(sections):
        fg = color.BLACK if i == section_index else color.WHITE
        bg = color.WORLDMAP_CURSOR if i == section_index else color.BLACK
        console.print(x=tab_x, y=y + 2 + i, string=section.ljust(15), fg=fg, bg=bg)
    content_x = x + 20
    content_y = y + 3
    current = sections[section_index]
    if current == "Inventory":
        inv = world.get(player, Inventory)
        items = inv.items if inv else []
        if not items:
            console.print(x=content_x, y=content_y, string="Inventory is empty.", fg=color.GRAY)
        for i, item_id in enumerate(items[:14]):
            name = inventory_world.get(item_id, Name)
            console.print(x=content_x, y=content_y + i, string=f"- {name.name if name else 'Unknown Item'}", fg=color.WHITE)
    elif current == "Active Quests":
        if not active_quests:
            console.print(x=content_x, y=content_y, string="No active quests.", fg=color.GRAY)
        for i, quest in enumerate(active_quests[:14]):
            console.print(x=content_x, y=content_y + i, string=f"- {quest}", fg=color.WHITE)
    elif current == "Maps":
        if location.kind == "surface":
            place = location.site.title() if location.site else "Wilderness"
            console.print(x=content_x, y=content_y, string=f"Current region: {place}", fg=color.WHITE)
            console.print(x=content_x, y=content_y + 1, string=f"Zone: ({location.zx}, {location.zy})", fg=color.WHITE)
        else:
            console.print(x=content_x, y=content_y, string=f"Current dungeon: {location.site.title()}", fg=color.WHITE)
            console.print(x=content_x, y=content_y + 1, string=f"Depth: {location.depth}", fg=color.WHITE)
        console.print(x=content_x, y=content_y + 3, string=f"Discovered world cells: {len(discovered_cells)}", fg=color.WHITE)
    else:
        fighter = world.get(player, Fighter)
        lvl = world.get(player, Level)
        if fighter:
            console.print(x=content_x, y=content_y, string=f"HP: {fighter.hp}/{fighter.max_hp}", fg=color.WHITE)
            console.print(x=content_x, y=content_y + 1, string=f"Attack: {fighter.power}", fg=color.WHITE)
            console.print(x=content_x, y=content_y + 2, string=f"Defense: {fighter.defense}", fg=color.WHITE)
        if lvl:
            console.print(x=content_x, y=content_y + 4, string=f"Level: {lvl.current_level}", fg=color.WHITE)
            console.print(x=content_x, y=content_y + 5, string=f"XP: {lvl.current_xp}/{lvl.xp_to_next}", fg=color.WHITE)
    console.print(x=x + 20, y=y + 21, string="Up/Down switch sections. Esc/Tab closes.", fg=color.GRAY)
