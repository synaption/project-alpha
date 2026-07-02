from __future__ import annotations
from typing import Any, TYPE_CHECKING
from components import (
    Position, Renderable, Fighter, AI, BlocksMovement,
    Name, Item, Consumable, Inventory, Level, Friendly, Dialog,
    Needs, VillagerAI, FarmPlot, Speed, FactionAgent,
)
import color

if TYPE_CHECKING:
    from world import World


def make_player_components(x: int, y: int) -> list[Any]:
    """The player's core components, independent of any floor's World.

    Engine re-registers these same instances into whichever floor's World is
    current (see Engine._enter_floor) — they aren't owned by any single floor,
    since the player moves between floors that each have their own World.
    """
    return [
        Position(x, y),
        Renderable("@", color.PLAYER_FG, render_order=2),
        Fighter(max_hp=30, hp=30, defense=2, power=5),
        BlocksMovement(),
        Name("Player"),
        Inventory(capacity=26),
        Level(current_level=1),
        Speed(),
    ]


def spawn_monster(world: World, x: int, y: int, kind: str) -> int:
    if kind == "orc":
        return world.create_entity(
            Position(x, y),
            Renderable("o", color.ORC_FG, render_order=2),
            Fighter(max_hp=10, hp=10, defense=0, power=3, xp_reward=35),
            AI(behavior="hostile"),
            BlocksMovement(),
            Name("Orc"),
            Speed(value=110),   # quick raiders
        )
    if kind == "troll":
        return world.create_entity(
            Position(x, y),
            Renderable("T", color.TROLL_FG, render_order=2),
            Fighter(max_hp=16, hp=16, defense=1, power=4, xp_reward=100),
            AI(behavior="hostile"),
            BlocksMovement(),
            Name("Troll"),
            Speed(value=85),    # slow, lumbering brutes
        )
    raise ValueError(f"Unknown monster: {kind!r}")


_VILLAGERS = {
    "innkeeper": (
        "@", (255, 200, 150), "Mira",
        [
            "Welcome to the Rusty Flagon! We don't get many adventurers willing to face the dungeon.",
            "Stock up on supplies before you go down. Many who enter don't come back.",
            "If you survive, the first round's on me.",
        ],
    ),
    "merchant": (
        "@", (150, 200, 255), "Aldric",
        [
            "I trade in goods recovered from the dungeon. You'd be surprised what people bring back.",
            "Word of advice: the deeper you go, the deadlier it gets. Go prepared.",
            "Orcs on the upper floors are manageable. Trolls... less so.",
        ],
    ),
    "guard": (
        "@", (200, 200, 200), "Captain Vex",
        [
            "The dungeon entrance is south of town. Enter at your own risk — we won't follow.",
            "We've lost three adventurers this month alone. Good luck, stranger.",
        ],
    ),
    "elder": (
        "@", (200, 160, 100), "Elder Maren",
        [
            "Thornveil was built over these ruins centuries ago. We've learned to live alongside the dungeon.",
            "The dungeon shifts and changes. No two runs are ever the same — the old maps are useless.",
            "Seek the stairs down, but don't rush. Patience keeps adventurers alive.",
        ],
    ),
    "child": (
        "@", (255, 255, 150), "Pip",
        [
            "Are you going into the dungeon? Wow! Can I have your stuff if you die?",
            "I'm gonna be an adventurer when I grow up. Dad says I have to wait until I'm twelve.",
        ],
    ),
    "farmer": (
        "@", (150, 200, 100), "Gus",
        [
            "I used to adventure. Then I took an orc axe to the knee. Settled down after that.",
            "Tip from a veteran: always keep a health potion. Always.",
        ],
    ),
    "mayor": (
        "@", (220, 190, 90), "the Mayor",
        [
            "Welcome, traveler. We keep good relations with Thornveil — safe travels between us.",
            "This town's seen its share of hardship, but we endure.",
        ],
    ),
}


def spawn_villager(
    world: World,
    x: int,
    y: int,
    kind: str,
    home: tuple[int, int] | None = None,
    social_spot: tuple[int, int] = (0, 0),
    role: str = "villager",
) -> int:
    char, fg, name, lines = _VILLAGERS[kind]
    eid = world.create_entity(
        Position(x, y),
        Renderable(char, fg, render_order=2),
        Name(name),
        Friendly(),
        Dialog(lines=lines),
        BlocksMovement(),
        Needs(),
        VillagerAI(role=role, home=home or (x, y), social_spot=social_spot),
        Speed(),
    )
    return eid


def spawn_well(world: World, x: int, y: int) -> int:
    return world.create_entity(
        Position(x, y),
        Renderable("O", (150, 150, 200), render_order=1),
        Name("Well"),
        BlocksMovement(),
    )


def spawn_farm_plot(world: World, x: int, y: int) -> int:
    return world.create_entity(Position(x, y), FarmPlot())


def spawn_caravan(world: World, x: int, y: int, zone: tuple[int, int], circuit: list) -> int:
    return world.create_entity(
        Position(x, y),
        Renderable("c", (200, 160, 60), render_order=2),
        Name("Trading Caravan"),
        FactionAgent(faction="trading_caravan", zone=zone, circuit=list(circuit)),
        Speed(value=60),   # slower than a walking person -- it's hauling goods
    )


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
