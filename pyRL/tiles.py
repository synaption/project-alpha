import numpy as np
import color

# Per-cell graphic: codepoint + RGB foreground + RGB background
graphic_dt = np.dtype([
    ("ch", np.int32),
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

SHROUD = np.array((ord(" "), (0, 0, 0), (0, 0, 0)), dtype=graphic_dt)


def new_tile(*, walkable: bool, transparent: bool, dark: tuple, light: tuple):
    return np.array((walkable, transparent, dark, light), dtype=tile_dt)


FLOOR = new_tile(
    walkable=True,
    transparent=True,
    dark=(ord("."), color.FLOOR_DARK_FG, color.FLOOR_DARK_BG),
    light=(ord("."), color.FLOOR_LIGHT_FG, color.FLOOR_LIGHT_BG),
)

WALL = new_tile(
    walkable=False,
    transparent=False,
    dark=(ord("#"), color.WALL_DARK_FG, color.WALL_DARK_BG),
    light=(ord("#"), color.WALL_LIGHT_FG, color.WALL_LIGHT_BG),
)

DOWN_STAIRS = new_tile(
    walkable=True,
    transparent=True,
    dark=(ord(">"), color.FLOOR_DARK_FG, color.FLOOR_DARK_BG),
    light=(ord(">"), color.FLOOR_LIGHT_FG, color.FLOOR_LIGHT_BG),
)
