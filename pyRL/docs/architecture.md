# Architecture

pyRL uses an **Entity Component System (ECS)** with `python-tcod` for rendering and input.

## Core loop

```
main.py
  └─ Engine.handle_events(events)   ← process input, dispatch to handlers
  └─ Engine.render(console)         ← draw everything
  └─ context.present(console)       ← flip to screen
```

Time only advances when the player acts (or waits). After each player action, the engine flips to `ENEMY_TURN`, runs all AI, then flips back to `PLAYER_TURN`.

## ECS — world.py

| Concept | Implementation |
|---------|---------------|
| Entity | An `int` (auto-incremented ID) |
| Component | A `@dataclass` stored in `World._components[type][entity_id]` |
| System | A plain function that calls `world.query(CompA, CompB, ...)` |

```
World
├── create_entity(*components) → int
├── add_component(entity, component)
├── remove_component(entity, ctype)
├── get(entity, ctype) → T | None
├── has(entity, *ctypes) → bool
├── query(*ctypes) → Iterator[(eid, (comp, ...))]
├── query1(ctype) → Iterator[(eid, comp)]
├── delete_entity(entity)          # deferred; removed on flush_dead()
└── flush_dead()
```

`delete_entity` is deferred so systems can finish iterating before removals happen.

## Game states

```
PLAYER_TURN  ──(move/attack)──► ENEMY_TURN ──(AI runs)──► PLAYER_TURN
                                                       └──► PLAYER_DEAD
PLAYER_TURN  ──(bump villager)──► TALKING ──(any key / ESC)──► PLAYER_TURN
PLAYER_TURN  ──(opens inv)──► SHOW_INVENTORY ──(ESC)──► PLAYER_TURN
PLAYER_TURN  ──(levels up)──► LEVEL_UP ──(a/b/c)──► ENEMY_TURN
```

TALKING never transitions to ENEMY_TURN — it costs no game time.

`floor == 0` → town (Thornveil, `town_gen.py`). `floor >= 1` → dungeon (`map_gen.py`).

## Module map

```
main.py            Entry point; creates tileset, context, console; drives the loop
engine.py          Engine class; owns World, GameMap, MessageLog; dispatches input
world.py           ECS core
components.py      All component dataclasses
tiles.py           Tile type constants (FLOOR, WALL, DOWN_STAIRS) as numpy scalars
color.py           RGB color constants
constants.py       Screen/map dimensions, file paths
game_map.py        GameMap; numpy tile/visibility arrays; entity spatial queries
map_gen.py         BSP-style procedural dungeon generator
town_gen.py        Hand-crafted town of Thornveil (floor 0)
message_log.py     MessageLog; renders the last N messages into a console region
entity_factories.py  Spawn functions for player, monsters, and items
systems/
  fov_system.py    Recomputes game_map.visible using tcod.map.compute_fov
  render_system.py Draws map, entities, and UI panel to the console
  combat_system.py attack(), kill(), award_xp()
  ai_system.py     Hostile pathfinding (A*) and confused random walk
  item_system.py   Use functions for every consumable item type
```

## Data flow: player moves

```
KeyDown(arrow)
  → engine._handle_player_key
  → _move_or_attack(dx, dy)
      if cell blocked by Fighter → combat_system.attack()
                                       → kill() if hp <= 0
                                       → award_xp() if player killed it
      else → update position → fov_system.update_fov()
  → state = ENEMY_TURN
  → engine._do_enemy_turn()
      → ai_system.run_ai()   (each visible hostile moves/attacks)
      → world.flush_dead()
      → state = PLAYER_TURN (or PLAYER_DEAD)
```

## Rendering

The console is `order="C"` (row-major), so all array indexing is `[y, x]`.

```
render_system._render_map:
    console.rgb[0:MAP_H, 0:MAP_W] = np.select(
        [visible, explored],
        [tiles["light"], tiles["dark"]],
        default=SHROUD,
    )

render_system._render_entities:
    console.rgb["ch"][pos.y, pos.x] = ord(char)
    console.rgb["fg"][pos.y, pos.x] = fg_color
```

The screen layout is:

```
┌─────────────────── 80 cols ───────────────────┐
│                                               │
│              MAP AREA  (80 × 43)              │ rows 0–42
│                                               │
├──────────────────────────────────────────────┤ row 43
│ [HP bar]   [message log ………………………………………] │
│ Lv:1 XP:.. │                                  │ rows 43–49
│ Floor: 1   │                                  │
└─────────────────────────────────────────────┘
```
