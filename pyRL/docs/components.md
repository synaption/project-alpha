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
Held item ids refer to entities in `Engine.inventory_world` — a separate `World` from any floor's, so a picked-up item stays valid no matter which floor's `World` is current afterward. See [architecture.md](architecture.md#persistence).

## Location
```python
@dataclass(frozen=True)
class Location:
    kind: str = "surface"   # "surface" | "dungeon"
    site: str = ""          # town name (a town surface zone, or that town's dungeon); "" = wilderness
    depth: int = 0          # dungeon depth within `site`; unused for surface
    zx: int = 0             # absolute surface zone coord (world cell = zx // ZONES_PER_CELL)
    zy: int = 0
```
The key into `Engine.floors`. Frozen (hashable) so it works as a dict key and pickles trivially. The world is a flat grid of walkable **surface** zones addressed by `(zx, zy)`, plus **dungeon** depths hanging below town zones. A surface zone **is a town** iff `site` is set — town-ness is an `Engine.surface_towns` registry lookup, not a `kind`, so navigation code (edge-walk, LOD, fast-travel, render) sees one uniform `"surface"` and only life-sim code checks `site`. See [architecture.md](architecture.md#the-surface-and-navigation).

## Stairs
```python
@dataclass
class Stairs:
    destination: Location
    direction: str = "down"       # "down" | "up"
```
A transition tile — used only for the vertical (dungeon) axis now that towns are ground level. `destination` is the `Location` it leads to. Every dungeon depth has a `down` entity (to the next depth) and an `up` entity (to the depth above, or the town's surface zone for depth 1). Every town surface zone has a `down` entity (to its own dungeon depth 1). `Engine._use_stairs(pos, direction)` requires the `Stairs` entity at the player's feet to match the requested direction. Moving *between surface zones* is not stairs — you just walk off the edge (`Engine._try_edge_walk`). A depth-1 up-stairs names its town by `site` but emits placeholder `zx/zy=0`; `Engine._canonical_location` resolves it to the town's registered zone before it's used as a `floors` key.

## Friendly
```python
@dataclass
class Friendly:
    pass
```
Tag. Bumping into this entity opens dialog instead of attacking. Used on all town villagers.

## Dialog
```python
@dataclass
class Dialog:
    lines: list[str]
```
Holds the conversation lines for an NPC. The engine cycles through them one per key press, then closes the dialog box. Requires `Friendly` to be triggered.

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

## Speed
```python
@dataclass
class Speed:
    value: int = 100
    next_turn: float = 0.0
```
`value` is a Qud-style speed stat (100 = baseline; higher acts more often, lower less). `next_turn` is the `GameClock.total_minutes` timestamp at which this actor is next scheduled to act — maintained by `Engine._resolve_npc_turns`/`_spend_player_turn`. See [architecture.md](architecture.md#turn-scheduling).

## Needs
```python
@dataclass
class Needs:
    hunger: float = 20.0    # 0 = full, 100 = starving
    energy: float = 80.0    # 100 = fully rested, 0 = exhausted
    social: float = 80.0    # 100 = content, 0 = lonely
```
Villager life-sim stats. Decayed/restored every turn by `systems/villager_system.update_needs`. Crossing an urgent threshold (see `systems/villager_system.py`) overrides the daily schedule.

## VillagerAI
```python
@dataclass
class VillagerAI:
    role: str                          # "farmer" | "villager"
    home: tuple[int, int]
    social_spot: tuple[int, int]
    work: list[int] = field(default_factory=list)   # FarmPlot entity ids (farmers only)
    activity: str = "sleeping"         # sleeping|eating|working|socializing|wandering
    activity_timer: int = 0            # turns remaining committed to eating/socializing
    wander_target: tuple[int, int] | None = None
```
Drives the daily routine in `systems/villager_system.py`. `home` is where the villager sleeps and eats; `social_spot` is the shared gathering point (town square). Only `role == "farmer"` villagers work `FarmPlot`s.

## FarmPlot
```python
@dataclass
class FarmPlot:
    stage: int = 0             # UNTILLED..RIPE, see systems/farm_system.py
    watered_today: bool = False
```
One tillable tile. Stage advances `UNTILLED → TILLED → PLANTED → SPROUT → GROWING → RIPE`, one stage per day, only if watered that day. `world.add_component`/`remove_component(FarmPlot entity, Renderable)` toggles whether a crop sprite is drawn above the dirt tile.

## FactionAgent
```python
@dataclass
class FactionAgent:
    faction: str                                # "trading_caravan"
    zone: tuple[int, int] = (0, 0)              # its authoritative current surface zone
    circuit: list = field(default_factory=list) # [(zx, zy), ...] town zones to visit in order
    circuit_index: int = 0
    last_ticked: float = 0.0
```
A roaming faction member — currently just the trading caravan. It lives as an ordinary entity in whichever surface zone's `World` it occupies; `systems/faction_system.py` walks it toward the edge leading to `circuit[circuit_index]`, and `Engine._transfer_boundary_factions` ferries it across zone edges. `zone` is kept in sync on spawn and each transfer. `circuit` (a fixed list of town zone coords) lets `act_one` route without the Engine's registry. Guard/raider factions and long-absence projection are deferred. See [architecture.md](architecture.md#the-surface-and-navigation).

## Component combinations by entity type

| Entity | Components |
|--------|-----------|
| Player | Position, Renderable, Fighter, BlocksMovement, Name, Inventory, Level, Speed |
| Orc / Troll | Position, Renderable, Fighter, AI, BlocksMovement, Name, Speed |
| Villager | Position, Renderable, Name, Friendly, Dialog, BlocksMovement, Needs, VillagerAI, Speed |
| Faction agent (caravan) | Position, Renderable, Name, FactionAgent, Speed |
| Farm plot | Position, FarmPlot, Renderable† |
| Well | Position, Renderable, Name, BlocksMovement |
| Consumable item | Position‡, Renderable, Name, Item, Consumable |
| Stairs / transition tile | Position, Stairs |
| Corpse | Position, Renderable (char=`%`), Name |

† Only present once the plot is planted (stage ≥ `PLANTED`).
‡ `Position` is removed when picked up; re-added on drop.
