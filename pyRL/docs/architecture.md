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

After the player's action sets their own next scheduled time (`Engine._spend_player_turn`), the engine flips to `ENEMY_TURN`. `_do_enemy_turn` then runs `_resolve_npc_turns_for` on each floor in the active set (see Persistence → Level-of-detail active set), letting every hostile / villager / faction agent act — possibly more than once each, if they're faster than the player — up until the player's next turn, before flipping back to `PLAYER_TURN`. Crossing a day boundary triggers `farm_system.on_new_day()` on any active town floor.

### Turn scheduling

pyRL doesn't use an abstract energy pool (as in Angband/DCSS/Caves of Qud) — it expresses the same idea directly in `game_clock` minutes, since the engine already tracks real game time for the calendar and day/night cycle. Two independent knobs, deliberately kept apart:

- **`game_clock.TURN_MINUTES` / `action_cost(speed)`** — the *action-economy* cost of a standard action at Speed 100, in "economy-minutes". This is what `Speed` affects, and it's the only thing that determines how many turns any given actor needs to get through a fixed span of calendar time. It has nothing to do with how long a day is.
- **`game_clock.DAY_STRETCH`** — how many economy-minutes make up one calendar minute. This is the knob for "how long is a day/night cycle" — raising it means *every* actor, regardless of Speed, needs proportionally more of their own turns to cross one calendar day, but the *ratio* of turns-per-day between a fast and slow actor is untouched (that ratio only ever comes from `action_cost`/Speed).

`GameClock.total_minutes` is the master scheduling clock, tracked in economy-minutes — the same unit as `Speed.next_turn`, so the scheduler below never has to think about `DAY_STRETCH` at all. Calendar-facing properties (`hour`, `day_count`, `tide`, `weekday`, `light_level()`, ...) convert via `game_clock.to_calendar_minutes()` before deriving anything.

- `components.Speed` holds `value` (100 = baseline) and `next_turn` (the `GameClock.total_minutes`, in economy-minutes, at which this actor may next act).
- `Engine._spend_player_turn()` sets the player's `next_turn = clock.total_minutes + action_cost(speed)` whenever they take a costed action (move, attack, wait, pick up, use/drop an item).
- `Engine._resolve_npc_turns_for(fs, target_time)` repeatedly picks whichever non-player actor on that floor has the smallest `next_turn <= target_time`, has it act once, then advances that actor's own `next_turn` by its own `action_cost`. This repeats until every actor's `next_turn` exceeds the player's — so a fast actor (e.g. an orc at Speed 110) can act several times before a slow one (a troll at Speed 85) gets a single turn, *regardless* of how `DAY_STRETCH` is set. Dispatch to the right per-kind handler goes through `_ACT_ONE_BY_TAG` (`AI`→`ai_system.act_one`, `VillagerAI`→`villager_system.act_one`, `FactionAgent`→`faction_system.act_one`), which all share one `(world, game_map, player, clock, message_log, eid)` signature so a new entity kind is a one-line addition, not another branch.
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

Floors are addressed by a `components.Location(kind, site, depth, zx, zy)` (not a bare int). `Engine.location` is the current one. See "The surface and navigation" below.

## The surface and navigation

The world is a Caves-of-Qud-style two-tier map:

- **Surface zones** (`kind="surface"`): a bounded `SURFACE_ZONES_W × H` grid of walkable ground-level screens, addressed by absolute `(zx, zy)`. You walk from one to the next by stepping off a screen edge. A surface zone is generated as **wilderness** (`surface_gen.py`) unless it's a **town** zone — `Engine.surface_towns` maps certain `(zx,zy)` to a site name, and those zones are generated by `town_gen.py`/`town_gen_procedural.py` instead. Town-ness is thus a registry lookup on `site`, not a distinct `kind`.
- **World map / cells**: `ZONES_PER_CELL²` zones make up one coarse **world-map cell** (`cell = (zx // ZONES_PER_CELL, ...)`) — the granularity of the zoomed-out map you open with `m` to **fast-travel** (`GameState.WORLD_MAP`).
- **Dungeons** (`kind="dungeon"`) hang *below* a town's surface zone via `>` stairs, exactly as before.

The starting town (Thornveil) is a surface zone at the center cell — you spawn in it and walk straight out into wilderness; there are no stairs "up to an overworld". `Engine.surface_towns` (and its reverse index `Engine.town_zone`) are built deterministically from the seed at new-game (`_build_surface_towns`).

### Walking between zones (edge-walk)

`Engine._try_edge_walk`, called at the top of `_move_or_attack`, handles a move that steps off a surface zone's edge: it computes the neighbour `(zx±1, zy±1)` and the opposite-edge arrival (right→`x=0`, left→`x=W-1`, etc.; a diagonal resolves the x-axis first), stamps the town's `last_active_calendar` if leaving a town, then `_enter_floor(dest, arrive_at=(ax,ay))` and spends one action (so day/night, LOD, and catch-up all fire via the normal enemy turn). Stepping off the outermost grid edge logs "the edge of the world" and costs nothing. `surface_gen` keeps every zone's outer ring walkable so an arriving entity never lands in an impassable tile.

### Fast-travel (world map)

`m` opens `GameState.WORLD_MAP` (surface only). A cursor moves over world cells; Enter on a **discovered** cell calls `_fast_travel_to`, which picks that cell's representative zone (its town zone if any, else the center zone), sets the player's `Speed.next_turn = now + distance·ZONE_CROSS_HOURS·…` and flips to `ENEMY_TURN` — the standard enemy turn then advances the clock by the whole travel span, so town catch-up and day/night stay consistent. Fast-travel is refused while a hostile is near. `discovered_cells` fills in as you enter zones. Opening/closing the map is free.

### Dungeon stairs

`Engine._use_stairs(pos, direction)` is now only the *vertical* axis. `>` on a `direction="down"` entity descends; `<` on `direction="up"` ascends. A depth-1 up-stairs's destination is a `Location(kind="surface", site=<town>)` with placeholder coords; `Engine._canonical_location` resolves it to the town's registered zone before it's used as a `floors` key. The player entity is removed from the floor being left (`delete_entity`+`flush_dead` — just the player; everything else persists), and `_enter_floor` switches to the destination's `World`/`GameMap`, generating it the first time and reusing it after. Arrival is `arrive_at` (explicit, e.g. edge-walk/fast-travel), else `downstairs_location` (ascending), else `player_start`.

## Persistence

The whole world persists per playthrough — killing a monster, looting a room, tilling a farm plot, or a caravan advancing along its route all stay that way if you leave and come back. Several pieces make this work together:

### One World + one GameMap per floor

`Engine.floors: dict[Location, FloorState]` holds a `FloorState(world, game_map, last_active_calendar)` per *visited* floor (each surface zone, each dungeon depth). `Engine.world`/`Engine.game_map` are just aliases for whichever floor is current. This is deliberately a *separate* `World` instance per floor, not one shared `World` tagged by floor — every system (`ai_system`, `villager_system`, `faction_system`, `farm_system`, `render_system`, the turn scheduler) only ever operates on the `World`s in the current *active set* (below), so a floor outside that set is structurally invisible to all of them, not just conventionally skipped. That's what makes graded off-screen simulation both correct and cheap: there's no filter to forget, no query that could leak another floor's monsters into view or into the scheduler.

### Level-of-detail active set

Simulation fidelity degrades with distance rather than a hard current-floor-only cutoff. `Engine._active_locations()` returns the floors ticked this turn:

- **Dungeon depth window** — in a dungeon, every *already-visited* depth within `DEPTH_WINDOW_RADIUS` of the current one (same `site`) stays active (1D window along depth).
- **Surface zone window** — on the surface, every *already-visited* zone within `SURFACE_WINDOW_RADIUS` (Chebyshev) of the current `(zx,zy)` stays active — the 2D analogue. So monsters (and the caravan) one screen over keep moving in real time while you're on the adjacent screen.
- Neither window **eagerly generates** unvisited neighbours; it only covers floors that already exist in `self.floors`.
- **Everything outside the window** simply **freezes exactly as left** (positions, HP, confusion timers, items, caravan position — untouched), the floor-level generalization of a hostile freezing while merely out of FOV. The "sync `Speed.next_turn` to now on entry" trick means a re-activated floor never bursts through a backlog of owed actions — it just resumes.

`_do_enemy_turn` loops over the active set, calling `_resolve_npc_turns_for(fs, ...)` per floor. Two behaviours the multi-floor loop forces: entities on a nearby-but-not-*current* floor get `player=None` (the player entity only exists in the current floor's `World`), so hostiles idle rather than chase an absent player and villagers/caravans just continue their routines; and the FOV gate only applies on the current floor (FOV isn't computed for the others), so a windowed floor's monsters are simply always eligible to act.

### The trading caravan across zones

The caravan is an ordinary `FactionAgent` entity living in whichever surface zone's `World` it currently occupies — no parallel world-level record, so it pickles with its floor automatically. `faction_system.act_one` walks it toward the edge of its current zone that heads for the next town on its `circuit`; after the turn's active-set loop, `Engine._transfer_boundary_factions` ferries any caravan sitting on a zone edge into the neighbouring zone's `World` (via `_move_entity`, mirroring the player's edge-walk) and updates its `zone`. When its zone isn't active (player elsewhere) it simply freezes like any off-window entity. (Long-absence *projection* — advancing a frozen caravan to where it "should" be on return — is deferred; for now it resumes exactly where it froze.)

### Per-floor town catch-up

Town zones get an active catch-up instead of a plain freeze, since their whole point is being alive. `Engine._catch_up_floor`, called from `_enter_floor` for any town zone (`_is_town_zone`, i.e. `kind=="surface" and site`), uses the floor's own `FloorState.last_active_calendar` (stamped whenever the town stops being current — in `_use_stairs`, `_try_edge_walk`, and `_fast_travel_to`) and compares it to the current calendar time on return:

- `villager_system.update_needs(fs.world, elapsed_calendar_minutes)` runs once with the *whole* elapsed span — cheap, since needs decay is a linear function of elapsed time, not a turn-by-turn replay.
- `farm_system.catch_up_day` runs once per whole elapsed calendar day, abstracting a full day of the farmer's tending into one step per plot.

`_do_enemy_turn` then drives each active town's per-turn needs off the same `last_active_calendar` delta (updating it each turn), so a fast-travel arrival — already caught up on entry — is never double-counted. Villager position/`activity` are left as-is; the ordinary per-turn `_decide_activity` self-corrects them within one turn.

### Seeded generation

`Engine.seed` (random at a fresh game, restored on load) makes generation reproducible. `_generate_floor` derives a per-location RNG via `random.Random(_derive_seed(seed, ...))` — keyed `("surface", zx, zy)` for wilderness, `("town", site)` for a town zone (so Thornveil stays hand-crafted and procedural towns are stable wherever they sit), `("dungeon", site, depth)` for a dungeon — and threads it explicitly through `surface_gen`/`town_gen_procedural`/`map_gen` (which use only that `rng`, never the bare `random` module). `_build_surface_towns` likewise seeds town placement. `_derive_seed` uses `hashlib.sha256` rather than the builtin `hash()` — Python randomizes string hashing per process (`PYTHONHASHSEED`), so `hash(("...", site))` would give a *different* world each run and make save/reload regenerate never-visited floors differently; SHA-256 is stable everywhere. The same seed always produces the same world *the first time each floor is generated*; after that the floor's mutated state persists.

### Inventory is not tied to any floor

Held items can't simply stay registered in whichever floor's `World` they were picked up from — once the player moves to a different floor (a different `World` object, with its own independent entity-id namespace), that id would be meaningless there. `Engine.inventory_world` is a separate `World` instance that exists outside the floor system entirely; `Engine._move_entity` (using `World.all_components`) transfers an item's components into it on pickup and back into the current floor's world (with a fresh `Position`) on drop. `render_system.render_inventory` and `Engine._use_item`/`_drop_item` all take `inventory_world` as a distinct parameter from `world` for exactly this reason.

### Save/load

`Engine.save_game(path)`/`Engine.load_game(path)` pickle the entire `Engine` object — every floor's `World`+`GameMap` in `Engine.floors` (including numpy tile arrays), the `inventory_world`, `GameClock`, `MessageLog`, and `seed`. This works with no custom serialization code because everything reachable from `Engine` is either a plain dataclass, a numpy array, or (for `Item.use_function`) a reference to a module-level function — all natively picklable. `main.py` auto-loads `constants.SAVE_PATH` if it exists, otherwise starts a fresh `Engine()`. Press `s` in-game to save (costs no game time). The save file is deleted the moment the player dies (`Engine._do_enemy_turn`) — a save resumes one ongoing life, consistent with death being permanent; it isn't a way to undo dying.

## Module map

```
main.py            Entry point; loads a save if one exists, else starts fresh; drives the loop
engine.py          Engine class; owns per-floor World/GameMap, inventory_world, MessageLog, GameClock; dispatches input; save/load
world.py           ECS core
components.py      All component dataclasses
tiles.py           Tile type constants (FLOOR, WALL, DIRT, DOWN_STAIRS, ...) as numpy scalars
color.py           RGB color constants
constants.py       Screen/map dimensions, file paths (incl. SAVE_PATH)
game_map.py        GameMap; numpy tile/visibility arrays; entity spatial queries
game_clock.py      GameClock; the Reckoning calendar, day/night light_level()
map_gen.py         Seeded BSP-style procedural dungeon generator (takes site + depth + rng)
surface_gen.py     Seeded wilderness surface-zone generator (grass/forest/water/mountain, walkable borders)
town_gen.py        Hand-crafted town of Thornveil (a surface zone); farm plots + villagers; shared _carve_building helper
town_gen_procedural.py  Seeded generator for every other town zone (guaranteed inn/guard/mayor/well + randomized rest)
message_log.py     MessageLog; renders the last N messages into a console region
entity_factories.py  Spawn functions for monsters, items, villagers, farm plots, caravans, and make_player_components()
systems/
  fov_system.py    Recomputes game_map.visible using tcod.map.compute_fov
  render_system.py Draws map, entities, and UI panel to the console; day/night dimming
  combat_system.py attack(), kill(), award_xp()
  pathing.py       Shared A* one-step move_toward(), used by ai/villager/faction systems
  ai_system.py     Hostile pathfinding (A*) and confused random walk; act_one() per scheduled turn
  item_system.py   Use functions for every consumable item type
  villager_system.py Needs decay + daily schedule (sleep/eat/farm/socialize); act_one() per scheduled turn
  faction_system.py  Overworld faction agents (trading caravan): circuit routing + LOD projection
  farm_system.py   Till/plant/water/harvest FarmPlot state machine + day rollover + catch_up_day()
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
  → _spend_player_turn()   (schedules the player's next Speed.next_turn)
  → state = ENEMY_TURN
  → engine._do_enemy_turn()
      → _resolve_npc_turns()   (ai_system.act_one / villager_system.act_one, possibly several times each — see Turn scheduling)
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
