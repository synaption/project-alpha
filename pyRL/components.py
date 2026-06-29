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
