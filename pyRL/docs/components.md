# Components Reference

All components are plain `@dataclass` objects in [components.py](../components.py). Entities are ints; components are attached via `world.add_component(entity, component)`.

## Position
```python
@dataclass
class Position:
    x: int
    y: int
```
Map-space grid coordinates. Removing this component hides the entity from spatial queries (used to "hold" inventory items).

## Renderable
```python
@dataclass
class Renderable:
    char: str                     # single character
    fg: tuple[int, int, int]      # RGB foreground
    bg: tuple[int, int, int]      # RGB background (default black)
    render_order: int             # 0=corpse, 1=item, 2=actor
```
Lower `render_order` is drawn first (actors appear on top of items and corpses).

## Fighter
```python
@dataclass
class Fighter:
    max_hp: int
    hp: int
    defense: int
    power: int
    xp_reward: int = 0            # XP given to killer on death
```
Damage formula: `damage = max(0, attacker.power - defender.defense)`.  
`heal(amount)` clamps to `max_hp`.

## AI
```python
@dataclass
class AI:
    behavior: str = "hostile"     # "hostile" | "confused"
    turns_confused: int = 0
```
`hostile` — A* pathfind toward the player if visible.  
`confused` — random adjacent movement, decrements `turns_confused` each turn.

## BlocksMovement
```python
@dataclass
class BlocksMovement:
    pass
```
Tag. Presence means the entity occupies its tile and prevents movement through it.

## Name
```python
@dataclass
class Name:
    name: str
```
Human-readable display name. `kill()` rewrites it to `"remains of {name}"`.

## Item
```python
@dataclass
class Item:
    use_function: Callable | None = None
```
Tag + optional use callback. Signature: `fn(world, user, target, game_map, message_log) -> bool`.  
Returns `True` if the item was successfully used (consumed if also has `Consumable`).

## Consumable
```python
@dataclass
class Consumable:
    pass
```
Tag. Combined with `Item`: the item is removed from inventory on successful use.

## Inventory
```python
@dataclass
class Inventory:
    capacity: int
    items: list[int]              # entity IDs of held items
```
Held items have their `Position` component removed (they're not on the map).

## Stairs
```python
@dataclass
class Stairs:
    floor: int                    # destination floor number
```
Placed at the center of the last room. Player presses `>` on the same tile to descend.

## Level
```python
@dataclass
class Level:
    current_level: int = 1
    current_xp: int = 0
    level_up_base: int = 200
    level_up_factor: int = 150
```
XP threshold: `level_up_base + current_level × level_up_factor`.  
At level 1: 350 XP to advance. At level 2: 500 XP. etc.  
`needs_level_up` property checks if threshold crossed; engine enters `LEVEL_UP` state.

## Component combinations by entity type

| Entity | Components |
|--------|-----------|
| Player | Position, Renderable, Fighter, BlocksMovement, Name, Inventory, Level |
| Orc / Troll | Position, Renderable, Fighter, AI, BlocksMovement, Name |
| Consumable item | Position†, Renderable, Name, Item, Consumable |
| Stairs | Position, Stairs |
| Corpse | Position, Renderable (char=`%`), Name |

† `Position` is removed when picked up; re-added on drop.
