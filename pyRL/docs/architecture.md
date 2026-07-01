# Architecture

pyRL uses an **Entity Component System (ECS)** with `python-tcod` for rendering and input.

## Core loop

```
main.py
  └─ Engine.handle_events(events)   ← process input, dispatch to handlers
  └─ Engine.render(console)         ← draw everything
  └─ context.present(console)       ← flip to screen
```

Time only advances when the player acts (or waits). Each actor (player, monster, villager) has a `Speed` (100 = baseline); an action costs `game_clock.action_cost(speed)` game-minutes, so a Speed-200 actor spends half the minutes per action of a Speed-100 one — and consequently gets scheduled roughly twice as often. See "Turn scheduling" below.

After the player's action sets their own next scheduled time (`Engine._spend_player_turn`), the engine flips to `ENEMY_TURN`. `Engine._resolve_npc_turns` then lets every hostile and villager act — possibly more than once each, if they're faster than the player — up until the player's next turn, before flipping back to `PLAYER_TURN`. Crossing a day boundary triggers `farm_system.on_new_day()`.

### Turn scheduling

pyRL doesn't use an abstract energy pool (as in Angband/DCSS/Caves of Qud) — it expresses the same idea directly in `game_clock` minutes, since the engine already tracks real game time for the calendar and day/night cycle. Two independent knobs, deliberately kept apart:

- **`game_clock.TURN_MINUTES` / `action_cost(speed)`** — the *action-economy* cost of a standard action at Speed 100, in "economy-minutes". This is what `Speed` affects, and it's the only thing that determines how many turns any given actor needs to get through a fixed span of calendar time. It has nothing to do with how long a day is.
- **`game_clock.DAY_STRETCH`** — how many economy-minutes make up one calendar minute. This is the knob for "how long is a day/night cycle" — raising it means *every* actor, regardless of Speed, needs proportionally more of their own turns to cross one calendar day, but the *ratio* of turns-per-day between a fast and slow actor is untouched (that ratio only ever comes from `action_cost`/Speed).

`GameClock.total_minutes` is the master scheduling clock, tracked in economy-minutes — the same unit as `Speed.next_turn`, so the scheduler below never has to think about `DAY_STRETCH` at all. Calendar-facing properties (`hour`, `day_count`, `tide`, `weekday`, `light_level()`, ...) convert via `game_clock.to_calendar_minutes()` before deriving anything.

- `components.Speed` holds `value` (100 = baseline) and `next_turn` (the `GameClock.total_minutes`, in economy-minutes, at which this actor may next act).
- `Engine._spend_player_turn()` sets the player's `next_turn = clock.total_minutes + action_cost(speed)` whenever they take a costed action (move, attack, wait, pick up, use/drop an item).
- `Engine._resolve_npc_turns(target_time)` repeatedly picks whichever non-player actor has the smallest `next_turn <= target_time`, has it act once via `ai_system.act_one` / `villager_system.act_one`, then advances that actor's own `next_turn` by its own `action_cost`. This repeats until every actor's `next_turn` exceeds the player's — so a fast actor (e.g. an orc at Speed 110) can act several times before a slow one (a troll at Speed 85) gets a single turn, *regardless* of how `DAY_STRETCH` is set.
- Hostiles outside the player's FOV are frozen (`ai_system.is_active`) rather than banking a backlog of owed turns — their `next_turn` is clamped to "now" every dispatch instead of accumulating while off-screen.
- Freshly-spawned entities (a new floor's monsters, or town's villagers) have their `next_turn` synced to the clock's current time right after generation, so they don't burst through turns "owed" since their component's zero-valued default.
- `Needs` decay/restoration is *not* tied to how often a villager gets scheduled, nor to `DAY_STRETCH` — `villager_system.update_needs` runs once per player action, scaled by however many *calendar* minutes just elapsed (`game_clock.to_calendar_minutes(elapsed)`), so hunger/energy/social always track the true calendar day regardless of Speed or how long a day/night cycle has been stretched to be.

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
engine.py          Engine class; owns World, GameMap, MessageLog, GameClock; dispatches input
world.py           ECS core
components.py      All component dataclasses
tiles.py           Tile type constants (FLOOR, WALL, DIRT, DOWN_STAIRS, ...) as numpy scalars
color.py           RGB color constants
constants.py       Screen/map dimensions, file paths
game_map.py        GameMap; numpy tile/visibility arrays; entity spatial queries
game_clock.py      GameClock; the Reckoning calendar, day/night light_level()
map_gen.py         BSP-style procedural dungeon generator
town_gen.py        Hand-crafted town of Thornveil (floor 0); farm plots + villagers
message_log.py     MessageLog; renders the last N messages into a console region
entity_factories.py  Spawn functions for player, monsters, items, villagers, farm plots
systems/
  fov_system.py    Recomputes game_map.visible using tcod.map.compute_fov
  render_system.py Draws map, entities, and UI panel to the console; day/night dimming
  combat_system.py attack(), kill(), award_xp()
  ai_system.py     Hostile pathfinding (A*) and confused random walk
  item_system.py   Use functions for every consumable item type
  villager_system.py Needs decay + daily schedule (sleep/eat/farm/socialize) for villagers
  farm_system.py   Till/plant/water/harvest FarmPlot state machine + day rollover
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
