# Systems Reference

Systems are functions (not classes) that operate on the world by querying components. None of them store state — all state lives in components.

---

## fov_system.update_fov(world, game_map, player)
[systems/fov_system.py](../systems/fov_system.py)

Recomputes `game_map.visible` using `tcod.map.compute_fov` (symmetric shadowcast, radius 8). Then ORs visible into `game_map.explored` so fog-of-war tiles persist.

Called after every player move and on floor generation.

---

## render_system.render_all(console, world, game_map, player, message_log, location, clock)
[systems/render_system.py](../systems/render_system.py)

Three-pass render:

1. **Map** — bulk numpy `np.select` over `game_map.visible` / `game_map.explored` into `console.rgb`; outdoors (`location.kind == "surface"`) the visible tiles are dimmed by `clock.light_level()`, dungeons are always torch-lit. `render_world_map(...)` is a separate full-screen pass the Engine calls instead when in `GameState.WORLD_MAP`.
2. **Entities** — sorted by `Renderable.render_order`, only draws tiles inside `game_map.visible`.
3. **UI panel** — HP bar, XP/level line, location label (`"The Wilds"` / town name / `"{site} Depths, level {depth}"`), time/day-night, message log.

Helper functions exposed for the Engine:
- `render_inventory(console, world, inventory_world, player, title)` — box + item list. `world` supplies the player's `Inventory` component; `inventory_world` supplies each held item's `Name` (items live in a separate World — see [architecture.md](architecture.md#persistence)).
- `render_level_up(console, world, player)` — level-up selection menu

---

## combat_system
[systems/combat_system.py](../systems/combat_system.py)

### attack(world, attacker, defender, player, message_log, is_player_attacker)
Computes `damage = max(0, power - defense)`, applies it, logs the message, and calls `kill()` if hp drops to 0. If the player was the attacker, also calls `award_xp()`.

### kill(world, entity, player, message_log) → int
Converts entity to a corpse (changes `Renderable`, renames `Name`). For non-player entities, removes `AI` and `BlocksMovement` so they stop acting and blocking. Returns `xp_reward` (0 for player death).

### award_xp(world, player, xp, message_log)
Adds XP to the player's `Level.current_xp` and logs it.

---

## pathing.move_toward(world, game_map, eid, pos, target, exclude=())
[systems/pathing.py](../systems/pathing.py)

Shared "one A* step toward a target tile" helper, used by `ai_system`, `villager_system`, and `faction_system` (they all wanted the identical behavior). Builds a cost array from `game_map.tiles["walkable"]`, inflates other `BlocksMovement` tiles by 10 (so a crowd slows but doesn't fully block), and moves `eid` one tile along the `tcod.path.SimpleGraph` A* path (cardinal 2, diagonal 3). `exclude` keeps specific entities (e.g. the player, for a hostile pathing right up to them) from being costed.

---

## ai_system
[systems/ai_system.py](../systems/ai_system.py)

### act_one(world, game_map, player, clock, message_log, eid)
Takes one action for a single `(Position, AI)` entity — called via `Engine._ACT_ONE_BY_TAG` once per scheduled turn (see [architecture.md](architecture.md#turn-scheduling); a fast monster can get several calls per player turn). `clock` is unused here — it's part of the shared act_one signature so all three entity kinds dispatch uniformly.

- **confused** — decrements `turns_confused`; random step in any of 9 directions (including wait); attacks player if adjacent.
- **hostile** — chases via `pathing.move_toward` (attacks if adjacent). `player` is `None` on a nearby-but-not-current dungeon floor (no player entity exists there) — such hostiles just idle; confused ones still wander.

### is_active(game_map, pos, ai) -> bool
Whether this AI entity is eligible for a scheduled turn *on the current floor* — `True` for confused entities always, and for hostiles only while inside `game_map.visible`. The engine clamps ineligible hostiles' `Speed.next_turn` to "now" instead of letting them bank owed turns. (On a windowed non-current floor the FOV gate is skipped entirely — see [architecture.md](architecture.md#persistence).)

---

## faction_system
[systems/faction_system.py](../systems/faction_system.py)

Surface faction agents (currently just the trading caravan). Mirrors `villager_system`'s shape.

- **act_one(world, game_map, player, clock, message_log, eid)** — one tile-step toward the edge of the caravan's current zone that heads for `target_zone(agent)` (its next town on the `circuit`), via `pathing.move_toward`. When the caravan's `zone` equals its target, it advances `circuit_index` to the next town.
- **target_zone(agent)** — the current destination town's absolute zone coords (`circuit[circuit_index]`).

Cross-zone travel is handled by the engine, not here: after the active-set loop, `Engine._transfer_boundary_factions` ferries any caravan sitting on a zone edge into the neighbouring zone's `World` (via `_move_entity`) and updates its `zone`. A caravan on an inactive floor simply freezes; long-absence projection is deferred. See [architecture.md](architecture.md#the-surface-and-navigation).

---

## item_system
[systems/item_system.py](../systems/item_system.py)

All use functions share the signature `fn(world, user, target, game_map, message_log) -> bool`.

| Function | Effect | Range |
|----------|--------|-------|
| `use_health_potion` | Heal 40 HP (fails if full) | — |
| `use_lightning_scroll` | 20 damage to nearest visible enemy | ≤ 5 tiles |
| `use_fireball_scroll` | 12 damage to all entities within radius 3 of nearest visible enemy | — |
| `use_confusion_scroll` | Confuses nearest visible enemy for 10 turns | — |

All scroll effects that kill enemies call `kill()` + `award_xp()` so XP is awarded correctly.

---

## town generation — town_gen.generate_town(...)
[town_gen.py](../town_gen.py)

Generates the hand-crafted starting area (**Thornveil**). The layout is fixed rather than random to give the town a consistent feel. Steps:

1. Fill 80×43 map with `GRASS`.
2. Carve cobblestone town square and main roads (horizontal + vertical).
3. Carve side paths from building doors to the main road.
4. Place five buildings (`_carve_building`: WALL perimeter + INDOOR_FLOOR interior).
5. Place DOOR tiles on each building's entrance.
6. Place only the dungeon `DOWN_STAIRS` (south) + a `Stairs(destination=Location("dungeon","thornveil",1), direction="down")`. There is no "up" stairs — the town is a ground-level surface zone, so you leave by walking off any edge (`Engine._try_edge_walk`).
7. Set `game_map.player_start` to town centre.
8. Spawn the well, six `FarmPlot` entities south of House 1, and six named villagers (Gus the farmer is assigned the farm plots via `VillagerAI.work`).

Thornveil is the surface zone at `Engine.town_zone["thornveil"]`. Generated once by `Engine._generate_floor` the first time it's entered — no randomness, so it never regenerates; persists in `Engine.floors` like every floor. Its `_carve_building` helper is reused by `town_gen_procedural.py`.

---

## procedural town generation — town_gen_procedural.generate_town(world, site, ..., rng)
[town_gen_procedural.py](../town_gen_procedural.py)

Generates every town zone other than Thornveil, seeded per-site (`_derive_seed(seed, "town", site)`). Guarantees a consistent core across every seed — an Inn, a Guard post, the Mayor, and a Well — then randomizes the rest: extra building count/placement (rejection-sampled to not overlap), the additional villager roster (drawn from merchant/child/farmer/elder), and farm-plot count (only if a farmer was rolled). Doors face the town square. Places only the dungeon-`down` stairs (parameterized by `site`); like Thornveil, it's exited by walking off an edge.

## surface generation — surface_gen.generate_surface_zone(world, zx, zy, rng)
[surface_gen.py](../surface_gen.py)

Generates one wilderness surface zone (the screens between towns), seeded `_derive_seed(seed, "surface", zx, zy)`. Fills `GRASS`, scatters walkable `FOREST` and some impassable `WATER`/`MOUNTAIN` blobs, then forces the **outer ring** back to grass — a walkable-border invariant so an entity arriving on any edge lands on a walkable tile and zones connect seamlessly. Generated lazily the first time the player (or a caravan) reaches `(zx, zy)`; then persists.

---

## game_clock.GameClock
[game_clock.py](../game_clock.py)

Thornveil's calendar ("the Reckoning") and day/night clock. Deliberately not named `calendar.py` to avoid shadowing the stdlib module.

`total_minutes` is tracked in *economy*-minutes (the same unit `Speed.next_turn` uses — see [architecture.md](architecture.md#turn-scheduling)), not calendar minutes. `DAY_STRETCH` (economy-minutes per calendar-minute) controls how long a day/night cycle takes without touching `action_cost()`/Speed at all — every calendar-facing property converts through `to_calendar_minutes()` first.

- `advance(minutes=TURN_MINUTES) -> bool` — called once per player action from `Engine._do_enemy_turn` with however many economy-minutes that action's `_resolve_npc_turns` catch-up window spanned; returns `True` the instant a new *calendar* day begins.
- `to_calendar_minutes(economy_minutes) -> float` — divides by `DAY_STRETCH`; used both internally (for `hour`/`day_count`/etc.) and by `Engine._do_enemy_turn` to convert elapsed economy-time into calendar-time before calling `villager_system.update_needs`.
- Weeks are 7 named days (`WEEKDAYS`), years are 4 named "tides" of 30 days each (`TIDES`) standing in for seasons/months.
- `date_string()` — e.g. `"Wellday, the 14th of Harvest, Year 214 of the Reckoning"`.
- `light_level()` — 0.25 (deep night) .. 1.0 (full day), with 1-hour dawn/dusk ramps around `DAWN_HOUR`/`DUSK_HOUR`. Used by `render_system` to dim outdoor tiles/entities (any surface zone — wilderness or town) at night; dungeons are unaffected (torch-lit).

---

## villager_system
[systems/villager_system.py](../systems/villager_system.py)

Villagers eat, sleep, farm, and socialize on a daily schedule, overridden by urgent `Needs`.

### update_needs(world, elapsed_minutes)
Called once per player action with however many *calendar*-minutes just elapsed — the caller passes `game_clock.to_calendar_minutes(elapsed)`, not raw economy-minutes, so needs track real calendar time uniformly regardless of a villager's `Speed` or `game_clock.DAY_STRETCH`. `hunger` rises, `energy` drains while awake and restores while `sleeping`, `social` decays and restores while `socializing`, `hunger` falls while `eating` — all as `_PER_MINUTE` rates multiplied by `elapsed_minutes`. This keeps villager needs in sync with the calendar-hour-based schedule in `_decide_activity` no matter how long a day/night cycle has been stretched to be.

### act_one(world, game_map, player, clock, message_log, eid)
Takes one action for a single `(Position, VillagerAI, Needs)` entity — dispatched via `Engine._ACT_ONE_BY_TAG` once per scheduled turn (`player` is unused here, present only for the shared signature):
1. **`_decide_activity`** — picks `sleeping`/`eating`/`socializing`/`working`/`wandering`. Priority: an in-progress eat/socialize commitment (`activity_timer`) → night → urgent need (`energy ≤ 15`, `hunger ≥ 75`, `social ≤ 20`) → scheduled meal hours (12:00/18:00) → scheduled social hours (20:00–22:00) → farm work (farmers only) → wandering.
2. **`_act`** — moves toward the activity's target (`home`, `social_spot`, or the next `FarmPlot` needing attention) via the shared `pathing.move_toward`. When a farmer reaches a plot needing attention, calls `farm_system.tend()` and logs the action.

---

## farm_system
[systems/farm_system.py](../systems/farm_system.py)

Tilling, planting, watering, and harvesting for `FarmPlot` entities. Stage constants: `UNTILLED, TILLED, PLANTED, SPROUT, GROWING, RIPE = range(6)`.

| Function | Effect |
|----------|--------|
| `till` | `UNTILLED → TILLED`; changes the underlying tile to `DIRT`. |
| `plant` | `TILLED → PLANTED`; attaches a crop `Renderable` (render_order 1, drawn above the dirt, below actors). |
| `water` | Marks `watered_today`; changes the tile to `DIRT_WET` for the rest of the day. Fails if already watered today. |
| `harvest` | `RIPE → TILLED`; removes the crop `Renderable`, ready to replant. |
| `needs_attention(plot_id) -> bool` | Whether any of the above is currently actionable. |
| `tend(plot_id) -> str \| None` | Performs whichever action is due; returns its name for logging. |
| `on_new_day(world, game_map)` | Called from `Engine._do_enemy_turn` when `GameClock.advance()` rolls a new day *while the player is in town*. Advances the stage of any plot watered the previous day, then resets `watered_today` and the tile back to dry `DIRT` for every tilled plot. |
| `catch_up_day(world, game_map)` | Called from `Engine._catch_up_floor` once per whole calendar day the player was away from a town. Abstracts a full day of tending into one pass: tills any `UNTILLED` plot, plants any `TILLED` one, harvests any `RIPE` one, else waters it — then calls `on_new_day`. See [architecture.md](architecture.md#persistence). |

A crop takes 3 in-game days of watering (`PLANTED → SPROUT → GROWING → RIPE`) to ripen; a missed watering day stalls growth without killing the plant.

---

## map generation — map_gen.generate_dungeon(world, site, depth, ..., rng)
[map_gen.py](../map_gen.py)

Not a system file but uses the same pattern. Takes `site` + `depth` (which town's dungeon, how deep) and an `rng: random.Random` (see [architecture.md](architecture.md#persistence) — `Engine._generate_floor` derives one per location) which it uses exclusively; never the bare `random` module, so generation is reproducible from the seed. Algorithm:

1. Attempt to place `max_rooms` rectangular rooms at random positions.
2. Skip any room that intersects an existing room.
3. Carve room interior to `FLOOR`.
4. First room: set `game_map.player_start` to its center, no monsters; carve `UP_STAIRS` there too and spawn a `Stairs(direction="up")` — destination is `depth-1` in the same `site`, or (when `depth == 1`) the town's surface zone as a placeholder-coord `Location("surface", site=site)` that `Engine._canonical_location` resolves to the registered zone. This is where the player lands when climbing up into this floor or descending back into it from above.
5. Subsequent rooms: connect center to previous room's center via an L-shaped Bresenham tunnel; call `_place_entities`.
6. After all rooms: carve `DOWN_STAIRS` at the last room's center; spawn a `Stairs(destination=Location("dungeon", site, depth+1), direction="down")`.

Monster/item counts scale with `depth`. Trolls appear from depth 3 onward.

Once generated, a floor's `FloorState` persists in `Engine.floors` for the rest of the playthrough (see [architecture.md](architecture.md#persistence)) — `generate_dungeon` only runs again the first time the player reaches a `(site, depth)` never visited before.
