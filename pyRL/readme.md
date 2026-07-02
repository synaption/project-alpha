# pyRL

A true roguelike built with [python-tcod](https://python-tcod.readthedocs.io/) and an Entity Component System architecture.

## What makes it a "true roguelike"

Adheres to the [Berlin Interpretation](http://www.roguebasin.com/index.php/Berlin_Interpretation) high-value factors:

| Factor | Description |
|--------|-------------|
| Random environment generation | Each run generates a new dungeon via BSP or cellular automata |
| Permadeath | Death ends the run; no saving mid-dungeon |
| Turn-based | Time advances only when the player acts |
| Grid-based | All movement and targeting is tile-aligned |
| Non-modal complexity | Items, spells, and status effects interact without special UI modes |
| Resource management | Food clock, ammo, consumables — scarcity creates decisions |
| Hack & slash | Combat is mechanical and meaningful, not cinematic |
| Exploration & discovery | Fog of war, unknown items, identified-on-use gear |

## Architecture: ECS

```
World
 ├── EntityManager   — creates/destroys integer entity IDs
 ├── ComponentStore  — maps (entity_id, ComponentType) → component data
 └── Systems         — query components, process logic, emit events
```

**Entities** are plain integers. Nothing more.

**Components** are dataclasses — pure data, no methods:

```python
@dataclass
class Position:
    x: int
    y: int

@dataclass
class Fighter:
    hp: int
    max_hp: int
    defense: int
    power: int

@dataclass
class AI:
    behavior: str  # "hostile", "passive", "confused"
```

**Systems** are functions (or classes) that operate on a filtered view of the world:

```python
def movement_system(world: World) -> None:
    for entity, (pos, vel) in world.query(Position, Velocity):
        pos.x += vel.dx
        pos.y += vel.dy
```

This separation keeps game rules readable, testable, and easy to extend without inheritance tangles.

## Tech stack

| Library | Purpose |
|---------|---------|
| `python-tcod` | Console rendering, FOV, pathfinding, BSP map generation |
| `tcod.event` | Keyboard/mouse input loop |
| `numpy` | Tile map arrays for fast FOV and collision checks |
| `attrs` / `dataclasses` | Lightweight component definitions |

## Project structure (planned)

```
pyRL/
├── main.py               # Entry point, game loop
├── engine.py             # Top-level Engine class, ties systems together
├── world.py              # EntityManager + ComponentStore
├── components/
│   ├── position.py
│   ├── renderable.py
│   ├── fighter.py
│   ├── inventory.py
│   └── ...
├── systems/
│   ├── movement.py
│   ├── combat.py
│   ├── ai.py
│   ├── fov.py
│   ├── render.py
│   └── ...
├── map/
│   ├── game_map.py       # Tile grid, walkability, transparency
│   ├── generator.py      # Procedural dungeon generation
│   └── tiles.py          # Tile type definitions
├── data/
│   ├── items.json        # Item templates (spawned as entities)
│   └── monsters.json     # Monster templates
└── readme.md
```

## Development roadmap

### Phase 1 — Foundation
- [ ] ECS core: EntityManager, ComponentStore, basic query
- [ ] Game loop with tcod event handling
- [ ] Tile map with walkability + transparency arrays
- [ ] Player entity with Position and Renderable components
- [ ] Render system drawing to tcod console

### Phase 2 — Dungeon
- [ ] BSP dungeon generator (rooms + corridors)
- [ ] FOV system using `tcod.map.compute_fov`
- [ ] Fog of war (explored vs. visible tiles)
- [ ] Camera / viewport scrolling

### Phase 3 — Combat
- [ ] Fighter component (HP, defense, power)
- [ ] Bump-to-attack movement resolution
- [ ] Combat system with damage calculation
- [ ] Death and corpse entities
- [ ] Message log

### Phase 4 — Monsters
- [ ] AI system: pathfinding toward player when in FOV
- [ ] Monster spawning from templates
- [ ] Multiple monster types with varied stats

### Phase 5 — Items & Inventory
- [ ] Inventory component + pickup/drop system
- [ ] Item identification (unidentified on first run)
- [ ] Consumables: health potions, scrolls
- [ ] Equipment: weapons and armor affecting Fighter stats

### Phase 6 — Roguelike polish
- [ ] Multiple dungeon levels (stairs)
- [ ] Food / hunger clock
- [ ] Saving disabled (permadeath enforced)
- [ ] Score screen on death
- [ ] Seed display for provably random runs

## Getting started

```bash
pip install tcod numpy
python main.py
```

## Controls (planned)

| Key | Action |
|-----|--------|
| Arrow keys / numpad | Move / attack |
| `g` | Pick up item |
| `i` | Open inventory |
| `d` | Drop item |
| `Tab` | Open in-game menu |
| `>` | Descend stairs |
| `v` | View message history |
| `Esc` | Open pause menu |

## References

- [python-tcod tutorial (2020)](https://rogueliketutorials.com/tutorials/tcod/v2/) — canonical starting point
- [RogueBasin Berlin Interpretation](http://www.roguebasin.com/index.php/Berlin_Interpretation)
- [Specs ECS (Rust)](https://specs.amethyst.rs/docs/tutorials/) — good ECS design reference even in a different language
- [Brogue](https://sites.google.com/site/broguegame/) — benchmark for elegant roguelike design
