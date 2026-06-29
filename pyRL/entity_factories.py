from __future__ import annotations
from typing import TYPE_CHECKING
from components import (
    Position, Renderable, Fighter, AI, BlocksMovement,
    Name, Item, Consumable, Inventory, Level,
)
import color

if TYPE_CHECKING:
    from world import World


def spawn_player(world: World, x: int, y: int) -> int:
    return world.create_entity(
        Position(x, y),
        Renderable("@", color.PLAYER_FG, render_order=2),
        Fighter(max_hp=30, hp=30, defense=2, power=5),
        BlocksMovement(),
        Name("Player"),
        Inventory(capacity=26),
        Level(current_level=1),
    )


def spawn_monster(world: World, x: int, y: int, kind: str) -> int:
    if kind == "orc":
        return world.create_entity(
            Position(x, y),
            Renderable("o", color.ORC_FG, render_order=2),
            Fighter(max_hp=10, hp=10, defense=0, power=3, xp_reward=35),
            AI(behavior="hostile"),
            BlocksMovement(),
            Name("Orc"),
        )
    if kind == "troll":
        return world.create_entity(
            Position(x, y),
            Renderable("T", color.TROLL_FG, render_order=2),
            Fighter(max_hp=16, hp=16, defense=1, power=4, xp_reward=100),
            AI(behavior="hostile"),
            BlocksMovement(),
            Name("Troll"),
        )
    raise ValueError(f"Unknown monster: {kind!r}")


def spawn_item(world: World, x: int, y: int, kind: str) -> int:
    from systems.item_system import (
        use_health_potion,
        use_lightning_scroll,
        use_fireball_scroll,
        use_confusion_scroll,
    )
    templates = {
        "health_potion": (
            Renderable("!", color.HEALTH_POTION_FG, render_order=1),
            Name("Health Potion"),
            Item(use_function=use_health_potion),
            Consumable(),
        ),
        "lightning_scroll": (
            Renderable("~", color.LIGHTNING_SCROLL_FG, render_order=1),
            Name("Lightning Scroll"),
            Item(use_function=use_lightning_scroll),
            Consumable(),
        ),
        "fireball_scroll": (
            Renderable("~", color.FIREBALL_SCROLL_FG, render_order=1),
            Name("Fireball Scroll"),
            Item(use_function=use_fireball_scroll),
            Consumable(),
        ),
        "confusion_scroll": (
            Renderable("~", color.CONFUSION_SCROLL_FG, render_order=1),
            Name("Confusion Scroll"),
            Item(use_function=use_confusion_scroll),
            Consumable(),
        ),
    }
    if kind not in templates:
        raise ValueError(f"Unknown item: {kind!r}")
    return world.create_entity(Position(x, y), *templates[kind])
