from __future__ import annotations
import random
from typing import Iterator, TYPE_CHECKING
import tcod.los
import tiles as tile_types
from game_map import GameMap
from components import Position, Stairs

if TYPE_CHECKING:
    from world import World


class Room:
    def __init__(self, x: int, y: int, w: int, h: int) -> None:
        self.x1, self.y1 = x, y
        self.x2, self.y2 = x + w, y + h

    @property
    def center(self) -> tuple[int, int]:
        return (self.x1 + self.x2) // 2, (self.y1 + self.y2) // 2

    @property
    def inner(self) -> tuple[slice, slice]:
        return slice(self.y1 + 1, self.y2), slice(self.x1 + 1, self.x2)

    def intersects(self, other: Room) -> bool:
        return (
            self.x1 <= other.x2 and self.x2 >= other.x1 and
            self.y1 <= other.y2 and self.y2 >= other.y1
        )


def _tunnel(start: tuple[int, int], end: tuple[int, int]) -> Iterator[tuple[int, int]]:
    x1, y1 = start
    x2, y2 = end
    corner = (x2, y1) if random.random() < 0.5 else (x1, y2)
    yield from ((x, y) for x, y in tcod.los.bresenham((x1, y1), corner).tolist())
    yield from ((x, y) for x, y in tcod.los.bresenham(corner, (x2, y2)).tolist())


def _place_entities(room: Room, game_map: GameMap, world: World, floor: int) -> None:
    from entity_factories import spawn_monster, spawn_item

    max_monsters = min(2 + floor // 2, 5)
    max_items = min(1 + floor // 3, 3)

    monster_pool = [("orc", max(1, 5 - floor)), ("troll", max(0, floor - 2))]
    item_pool = [
        ("health_potion", 35),
        ("lightning_scroll", 10 + floor * 2),
        ("fireball_scroll", 8 + floor),
        ("confusion_scroll", 8 + floor),
    ]

    for _ in range(random.randint(0, max_monsters)):
        x = random.randint(room.x1 + 1, room.x2 - 1)
        y = random.randint(room.y1 + 1, room.y2 - 1)
        if game_map.get_blocking_entity(x, y) is None:
            valid = [(k, w) for k, w in monster_pool if w > 0]
            if valid:
                choices, weights = zip(*valid)
                spawn_monster(world, x, y, random.choices(choices, weights=weights)[0])

    for _ in range(random.randint(0, max_items)):
        x = random.randint(room.x1 + 1, room.x2 - 1)
        y = random.randint(room.y1 + 1, room.y2 - 1)
        if not game_map.get_items_at(x, y):
            choices, weights = zip(*item_pool)
            spawn_item(world, x, y, random.choices(choices, weights=weights)[0])


def generate_dungeon(
    world: World,
    player: int,
    floor: int,
    map_width: int,
    map_height: int,
    max_rooms: int,
    room_min_size: int,
    room_max_size: int,
) -> GameMap:
    game_map = GameMap(world, map_width, map_height)
    rooms: list[Room] = []

    for _ in range(max_rooms):
        w = random.randint(room_min_size, room_max_size)
        h = random.randint(room_min_size, room_max_size)
        x = random.randint(0, map_width - w - 1)
        y = random.randint(0, map_height - h - 1)
        new_room = Room(x, y, w, h)

        if any(new_room.intersects(r) for r in rooms):
            continue

        game_map.tiles[new_room.inner] = tile_types.FLOOR

        if not rooms:
            cx, cy = new_room.center
            pos = world.get(player, Position)
            pos.x, pos.y = cx, cy
        else:
            for tx, ty in _tunnel(rooms[-1].center, new_room.center):
                if game_map.in_bounds(tx, ty):
                    game_map.tiles[ty, tx] = tile_types.FLOOR
            _place_entities(new_room, game_map, world, floor)

        rooms.append(new_room)

    if len(rooms) >= 2:
        sx, sy = rooms[-1].center
        game_map.tiles[sy, sx] = tile_types.DOWN_STAIRS
        game_map.downstairs_location = (sx, sy)
        world.create_entity(Position(sx, sy), Stairs(floor=floor + 1))

    return game_map
