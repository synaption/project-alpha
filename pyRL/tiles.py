import numpy as np
import color
import tile_ids as TID

# Per-cell graphic: codepoint + RGB foreground + RGB background
graphic_dt = np.dtype([
    ("ch", np.int32),
    ("tile_id", "U32"),
    ("fg", "3B"),
    ("bg", "3B"),
])

# Full tile: walkability flags + dark/light graphics
tile_dt = np.dtype([
    ("walkable", bool),
    ("transparent", bool),
    ("dark", graphic_dt),
    ("light", graphic_dt),
])

SHROUD = np.array((ord(" "), "", (0, 0, 0), (0, 0, 0)), dtype=graphic_dt)


def new_tile(*, walkable: bool, transparent: bool, tile_id: str, dark: tuple, light: tuple):
    return np.array((walkable, transparent, dark, light), dtype=tile_dt)


FLOOR = new_tile(
    walkable=True,
    transparent=True,
    tile_id=TID.MAP_FLOOR,
    dark=(ord("."), TID.MAP_FLOOR, color.FLOOR_DARK_FG, color.FLOOR_DARK_BG),
    light=(ord("."), TID.MAP_FLOOR, color.FLOOR_LIGHT_FG, color.FLOOR_LIGHT_BG),
)

WALL = new_tile(
    walkable=False,
    transparent=False,
    tile_id=TID.MAP_WALL,
    dark=(ord("#"), TID.MAP_WALL, color.WALL_DARK_FG, color.WALL_DARK_BG),
    light=(ord("#"), TID.MAP_WALL, color.WALL_LIGHT_FG, color.WALL_LIGHT_BG),
)

GRASS = new_tile(
    walkable=True,
    transparent=True,
    tile_id=TID.MAP_GRASS,
    dark=(ord("."), TID.MAP_GRASS, color.GRASS_DARK_FG, color.GRASS_DARK_BG),
    light=(ord("."), TID.MAP_GRASS, color.GRASS_LIGHT_FG, color.GRASS_LIGHT_BG),
)

COBBLESTONE = new_tile(
    walkable=True,
    transparent=True,
    tile_id=TID.MAP_COBBLESTONE,
    dark=(ord("."), TID.MAP_COBBLESTONE, color.COBBLE_DARK_FG, color.COBBLE_DARK_BG),
    light=(ord("."), TID.MAP_COBBLESTONE, color.COBBLE_LIGHT_FG, color.COBBLE_LIGHT_BG),
)

INDOOR_FLOOR = new_tile(
    walkable=True,
    transparent=True,
    tile_id=TID.MAP_INDOOR_FLOOR,
    dark=(ord("."), TID.MAP_INDOOR_FLOOR, color.INDOOR_DARK_FG, color.INDOOR_DARK_BG),
    light=(ord("."), TID.MAP_INDOOR_FLOOR, color.INDOOR_LIGHT_FG, color.INDOOR_LIGHT_BG),
)

DOOR = new_tile(
    walkable=True,
    transparent=True,
    tile_id=TID.MAP_DOOR,
    dark=(ord("+"), TID.MAP_DOOR, color.DOOR_DARK_FG, color.DOOR_DARK_BG),
    light=(ord("+"), TID.MAP_DOOR, color.DOOR_LIGHT_FG, color.DOOR_LIGHT_BG),
)

DIRT = new_tile(
    walkable=True,
    transparent=True,
    tile_id=TID.MAP_DIRT,
    dark=(ord("."), TID.MAP_DIRT, color.DIRT_DARK_FG, color.DIRT_DARK_BG),
    light=(ord("."), TID.MAP_DIRT, color.DIRT_LIGHT_FG, color.DIRT_LIGHT_BG),
)

DIRT_WET = new_tile(
    walkable=True,
    transparent=True,
    tile_id=TID.MAP_DIRT_WET,
    dark=(ord("."), TID.MAP_DIRT_WET, color.DIRT_WET_DARK_FG, color.DIRT_WET_DARK_BG),
    light=(ord("."), TID.MAP_DIRT_WET, color.DIRT_WET_LIGHT_FG, color.DIRT_WET_LIGHT_BG),
)

DOWN_STAIRS = new_tile(
    walkable=True,
    transparent=True,
    tile_id=TID.MAP_DOWN_STAIRS,
    dark=(ord(">"), TID.MAP_DOWN_STAIRS, color.FLOOR_DARK_FG, color.FLOOR_DARK_BG),
    light=(ord(">"), TID.MAP_DOWN_STAIRS, color.FLOOR_LIGHT_FG, color.FLOOR_LIGHT_BG),
)

UP_STAIRS = new_tile(
    walkable=True,
    transparent=True,
    tile_id=TID.MAP_UP_STAIRS,
    dark=(ord("<"), TID.MAP_UP_STAIRS, color.FLOOR_DARK_FG, color.FLOOR_DARK_BG),
    light=(ord("<"), TID.MAP_UP_STAIRS, color.FLOOR_LIGHT_FG, color.FLOOR_LIGHT_BG),
)

# Overworld terrain
FOREST = new_tile(
    walkable=True,
    transparent=True,
    tile_id=TID.MAP_FOREST,
    dark=(ord("^"), TID.MAP_FOREST, color.FOREST_DARK_FG, color.FOREST_DARK_BG),
    light=(ord("^"), TID.MAP_FOREST, color.FOREST_LIGHT_FG, color.FOREST_LIGHT_BG),
)

TOWN_ENTRANCE = new_tile(
    walkable=True,
    transparent=True,
    tile_id=TID.MAP_TOWN_ENTRANCE,
    dark=(ord("A"), TID.MAP_TOWN_ENTRANCE, color.TOWN_ENTRANCE_DARK_FG, color.TOWN_ENTRANCE_DARK_BG),
    light=(ord("A"), TID.MAP_TOWN_ENTRANCE, color.TOWN_ENTRANCE_LIGHT_FG, color.TOWN_ENTRANCE_LIGHT_BG),
)

WATER = new_tile(
    walkable=False,
    transparent=True,
    tile_id=TID.MAP_WATER,
    dark=(ord("~"), TID.MAP_WATER, color.WATER_DARK_FG, color.WATER_DARK_BG),
    light=(ord("~"), TID.MAP_WATER, color.WATER_LIGHT_FG, color.WATER_LIGHT_BG),
)

MOUNTAIN = new_tile(
    walkable=False,
    transparent=False,
    tile_id=TID.MAP_MOUNTAIN,
    dark=(ord("▲"), TID.MAP_MOUNTAIN, color.MOUNTAIN_DARK_FG, color.MOUNTAIN_DARK_BG),
    light=(ord("▲"), TID.MAP_MOUNTAIN, color.MOUNTAIN_LIGHT_FG, color.MOUNTAIN_LIGHT_BG),
)
