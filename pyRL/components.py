from __future__ import annotations
from dataclasses import dataclass, field
from typing import Callable


@dataclass
class Position:
    x: int
    y: int


@dataclass
class Renderable:
    char: str
    fg: tuple[int, int, int]
    bg: tuple[int, int, int] = (0, 0, 0)
    render_order: int = 1  # 0=corpse, 1=item, 2=actor


@dataclass
class Fighter:
    max_hp: int
    hp: int
    defense: int
    power: int
    xp_reward: int = 0

    def heal(self, amount: int) -> int:
        healed = min(amount, self.max_hp - self.hp)
        self.hp += healed
        return healed


@dataclass
class AI:
    behavior: str = "hostile"   # "hostile" | "confused"
    turns_confused: int = 0


@dataclass
class BlocksMovement:
    pass


@dataclass
class Name:
    name: str


@dataclass
class Item:
    use_function: Callable | None = None


@dataclass
class Consumable:
    pass


@dataclass
class Inventory:
    capacity: int
    items: list[int] = field(default_factory=list)


@dataclass
class Stairs:
    floor: int


@dataclass
class Friendly:
    """Tag: entity cannot be attacked; bumping opens dialog."""
    pass


@dataclass
class Dialog:
    lines: list[str]


@dataclass
class Level:
    current_level: int = 1
    current_xp: int = 0
    level_up_base: int = 200
    level_up_factor: int = 150

    @property
    def xp_to_next(self) -> int:
        return self.level_up_base + self.current_level * self.level_up_factor

    @property
    def needs_level_up(self) -> bool:
        return self.current_xp >= self.xp_to_next


@dataclass
class Speed:
    """100 = baseline pace. Higher acts more often; see game_clock.action_cost()."""
    value: int = 100
    next_turn: float = 0.0   # game_clock time (minutes) this actor may next act


@dataclass
class Needs:
    """Villager life-sim stats. 0 = satisfied, 100 = urgent, except energy (inverted)."""
    hunger: float = 20.0
    energy: float = 80.0    # 100 = fully rested, 0 = exhausted
    social: float = 80.0    # 100 = content, 0 = lonely


@dataclass
class VillagerAI:
    """Drives a villager's daily routine: sleep, eat, work, socialize, wander."""
    role: str                          # "farmer" | "villager"
    home: tuple[int, int]
    social_spot: tuple[int, int]
    work: list[int] = field(default_factory=list)   # FarmPlot entity ids (farmers only)
    activity: str = "sleeping"         # sleeping|eating|working|socializing|wandering
    activity_timer: int = 0            # turns remaining committed to eating/socializing
    wander_target: tuple[int, int] | None = None


@dataclass
class FarmPlot:
    """A single tillable tile. See systems/farm_system.py for stage constants."""
    stage: int = 0
    watered_today: bool = False
