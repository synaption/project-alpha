"""
Procedurally generated towns — every site other than the hand-crafted Thornveil.

Seeded per-site (see Engine._generate_floor: random.Random(hash((seed, "town",
site)))), so a given seed always produces the same town the first time it's
visited. After that, the town's own mutated state persists like any other
floor — the seed is never consulted again.

Every generated town guarantees the same core cast — an Inn, a Guard post, a
Well, and the Mayor — so it never feels like an empty shell, with building
count/placement and the rest of the villager roster randomized on top.
"""
from __future__ import annotations
import random
import numpy as np
from typing import TYPE_CHECKING
import tiles as tile_types
from game_map import GameMap
from components import Position, Stairs, VillagerAI, Location
from entity_factories import spawn_villager, spawn_well, spawn_farm_plot
from town_gen import _carve_building

if TYPE_CHECKING:
    from world import World

MAP_MARGIN = 4
_EXTRA_ARCHETYPES = ["merchant", "child", "farmer", "elder"]
_DECOR_GRASS_CHANCE = 0.04

# (kind, width, height)
_GUARANTEED_BUILDINGS = [
    ("innkeeper", 14, 8),
    ("guard", 10, 7),
    ("mayor", 12, 7),
]


def _overlaps(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> bool:
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return ax < bx + bw and ax + aw > bx and ay < by + bh and ay + ah > by


def _place_building(
    rng: random.Random, map_width: int, map_height: int, w: int, h: int,
    existing: list[tuple[int, int, int, int]], avoid: tuple[int, int, int, int],
) -> tuple[int, int, int, int] | None:
    for _ in range(100):
        x = rng.randint(MAP_MARGIN, map_width - MAP_MARGIN - w)
        y = rng.randint(MAP_MARGIN, map_height - MAP_MARGIN - h)
        rect = (x, y, w, h)
        if _overlaps(rect, avoid) or any(_overlaps(rect, r) for r in existing):
            continue
        return rect
    return None


def _door_position(rect: tuple[int, int, int, int], square_center: tuple[int, int]) -> tuple[int, int]:
    """Place the door on whichever wall faces the town square."""
    x, y, w, h = rect
    cx, cy = x + w // 2, y + h // 2
    sx, sy = square_center
    dx, dy = sx - cx, sy - cy
    if abs(dx) > abs(dy):
        return (x + w - 1, cy) if dx > 0 else (x, cy)
    return (cx, y + h - 1) if dy > 0 else (cx, y)


def generate_town(world: World, site: str, map_width: int, map_height: int, rng: random.Random) -> GameMap:
    game_map = GameMap(world, map_width, map_height)
    game_map.tiles[:, :] = tile_types.FLOOR
    grass_rolls = np.fromiter(
        (rng.random() for _ in range(map_width * map_height)),
        dtype=float,
        count=map_width * map_height,
    ).reshape((map_height, map_width))
    game_map.tiles[grass_rolls < _DECOR_GRASS_CHANCE] = tile_types.GRASS

    cx, cy = map_width // 2, map_height // 2
    square = (cx - 8, cy - 6, 16, 12)
    game_map.tiles[square[1]:square[1] + square[3], square[0]:square[0] + square[2]] = tile_types.COBBLESTONE

    # Vertical road connecting the square to the south (dungeon) and north
    # (overworld) edges — same convention as Thornveil.
    game_map.tiles[:, cx - 1:cx + 1] = tile_types.COBBLESTONE

    buildings: list[tuple[int, int, int, int]] = []
    roster: list[str] = [kind for kind, _, _ in _GUARANTEED_BUILDINGS]
    roster += [rng.choice(_EXTRA_ARCHETYPES) for _ in range(rng.randint(1, 3))]

    farm_villager_pos: tuple[int, int] | None = None
    villager_positions: list[tuple[str, tuple[int, int]]] = []

    for kind in roster:
        w, h = 10, 7
        for gk, gw, gh in _GUARANTEED_BUILDINGS:
            if gk == kind:
                w, h = gw, gh
                break
        rect = _place_building(rng, map_width, map_height, w, h, buildings, square)
        if rect is None:
            continue
        buildings.append(rect)
        _carve_building(game_map.tiles, *rect)
        dx, dy = _door_position(rect, (cx, cy))
        game_map.tiles[dy, dx] = tile_types.DOOR
        bx, by, bw, bh = rect
        interior = (bx + bw // 2, by + bh // 2)
        villager_positions.append((kind, interior))
        if kind == "farmer":
            farm_villager_pos = interior

    social_spot = (cx, cy)

    # ── dungeon entrance (south edge of the vertical road) ─────────────────
    ex, ey = cx, map_height - 1
    game_map.tiles[ey, ex] = tile_types.DOWN_STAIRS
    game_map.downstairs_location = (ex, ey)
    world.create_entity(
        Position(ex, ey),
        Stairs(destination=Location(kind="dungeon", site=site, depth=1), direction="down"),
    )

    # The town is ground level: walk off any edge into the wilderness
    # (Engine._try_edge_walk) — no stairs out.

    game_map.player_start = (cx, cy)

    # ── well ─────────────────────────────────────────────────────────────
    spawn_well(world, cx + 2, cy)

    # ── farmland (only if a farmer was rolled into the roster) ─────────────
    farm_plot_ids: list[int] = []
    if farm_villager_pos is not None:
        fx, fy = farm_villager_pos
        plot_positions = [(x, y) for y in (map_height - 4, map_height - 3) for x in range(fx - 1, fx + 2)]
        farm_plot_ids = [
            spawn_farm_plot(world, x, y) for x, y in plot_positions
            if 0 <= x < map_width and 0 <= y < map_height
        ]

    # ── villagers ────────────────────────────────────────────────────────
    for kind, (vx, vy) in villager_positions:
        role = "farmer" if kind == "farmer" else "villager"
        eid = spawn_villager(world, vx, vy, kind, social_spot=social_spot, role=role)
        if kind == "farmer" and farm_plot_ids:
            world.get(eid, VillagerAI).work = farm_plot_ids

    return game_map
