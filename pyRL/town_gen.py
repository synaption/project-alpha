"""
Hand-crafted town of Thornveil.

Layout (80 × 43):

  y=2–13   : Inn (left) | Guard House (center) | Shop (right)
  y=14–18  : cobblestone paths connecting buildings to the square
  y=15–26  : Town Square (cobblestone) — crossroads of main roads
  y=19–22  : Horizontal main road (full width)
  y=27–36  : House 1 (lower-left) | House 2 (lower-right)
  y=25–41  : South road (leads to dungeon entrance)
  y=41     : Dungeon entrance '>'
"""
from __future__ import annotations
import numpy as np
from typing import TYPE_CHECKING
import tiles as tile_types
from game_map import GameMap
from components import Position, Stairs, VillagerAI, Location
from entity_factories import spawn_villager, spawn_well, spawn_farm_plot

if TYPE_CHECKING:
    from world import World

# ── fixed coordinates ──────────────────────────────────────────────────────

PLAYER_START = (39, 20)      # (x, y)
DUNGEON_ENTRANCE = (39, 41)  # (x, y)

# Buildings: (x1, y1, width, height)
_INN   = (2,  2, 18, 12)
_SHOP  = (60, 2, 18, 12)
_GUARD = (33, 2, 14, 12)
_HOUSE1 = (3,  27, 14, 9)
_HOUSE2 = (63, 27, 14, 9)

# Doors: (x, y) — each a single DOOR tile placed on the building perimeter
_INN_DOOR   = (10, 13)
_SHOP_DOOR  = (68, 13)
_GUARD_DOOR = (39, 13)
_HOUSE1_DOOR = (9, 27)
_HOUSE2_DOOR = (69, 27)

# Gus's farm plots, on the open grass south of House 1.
_FARM_PLOTS = [(x, y) for y in (37, 38) for x in (5, 6, 7)]

# Where off-duty villagers gather to socialize.
_SOCIAL_SPOT = (39, 24)


def _carve_building(tiles, x: int, y: int, w: int, h: int) -> None:
    """Fill perimeter with WALL, interior with INDOOR_FLOOR."""
    tiles[y:y+h, x:x+w] = tile_types.WALL
    tiles[y+1:y+h-1, x+1:x+w-1] = tile_types.INDOOR_FLOOR


def generate_town(world: World, map_width: int, map_height: int) -> GameMap:
    game_map = GameMap(world, map_width, map_height)

    # ── base layer ────────────────────────────────────────────────────────
    game_map.tiles[:, :] = tile_types.GRASS

    # ── town square (cobblestone) ─────────────────────────────────────────
    game_map.tiles[15:27, 33:47] = tile_types.COBBLESTONE

    # ── main roads ────────────────────────────────────────────────────────
    game_map.tiles[19:23, :] = tile_types.COBBLESTONE   # horizontal
    game_map.tiles[:, 38:42]  = tile_types.COBBLESTONE  # vertical

    # ── side paths: north buildings → horizontal road ─────────────────────
    game_map.tiles[14:20, 10] = tile_types.COBBLESTONE  # inn path
    game_map.tiles[14:20, 68] = tile_types.COBBLESTONE  # shop path
    # guard house door is already on the vertical road (x 38–41)

    # ── side paths: horizontal road → south houses ────────────────────────
    game_map.tiles[23:27, 9]  = tile_types.COBBLESTONE  # house1 path
    game_map.tiles[23:27, 69] = tile_types.COBBLESTONE  # house2 path

    # ── buildings (overwrite cobblestone inside footprints) ───────────────
    for rect in (_INN, _SHOP, _GUARD, _HOUSE1, _HOUSE2):
        _carve_building(game_map.tiles, *rect)

    # ── doors ─────────────────────────────────────────────────────────────
    for dx, dy in (_INN_DOOR, _SHOP_DOOR, _GUARD_DOOR, _HOUSE1_DOOR, _HOUSE2_DOOR):
        game_map.tiles[dy, dx] = tile_types.DOOR

    # ── dungeon entrance ──────────────────────────────────────────────────
    ex, ey = DUNGEON_ENTRANCE
    game_map.tiles[ey, ex] = tile_types.DOWN_STAIRS
    game_map.downstairs_location = DUNGEON_ENTRANCE
    world.create_entity(
        Position(ex, ey),
        Stairs(destination=Location(kind="dungeon", site="thornveil", depth=1), direction="down"),
    )

    # The town is ground level: you simply walk off any edge into the
    # surrounding wilderness (Engine._try_edge_walk) — no stairs out.

    # ── place player ──────────────────────────────────────────────────────
    game_map.player_start = PLAYER_START

    # ── well (decorative) ─────────────────────────────────────────────────
    spawn_well(world, 35, 21)

    # ── farmland ──────────────────────────────────────────────────────────
    farm_plot_ids = [spawn_farm_plot(world, x, y) for x, y in _FARM_PLOTS]

    # ── villagers ─────────────────────────────────────────────────────────
    spawn_villager(world, 10, 7,  "innkeeper", social_spot=_SOCIAL_SPOT)
    spawn_villager(world, 68, 7,  "merchant",  social_spot=_SOCIAL_SPOT)
    spawn_villager(world, 39, 14, "guard",     social_spot=_SOCIAL_SPOT, home=(39, 7))
    spawn_villager(world, 36, 22, "elder",     social_spot=_SOCIAL_SPOT)
    spawn_villager(world, 43, 22, "child",     social_spot=_SOCIAL_SPOT)
    farmer = spawn_villager(
        world, 8, 31, "farmer", social_spot=_SOCIAL_SPOT, role="farmer",
    )
    world.get(farmer, VillagerAI).work = farm_plot_ids

    return game_map
