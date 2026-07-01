# Systems Reference

Systems are functions (not classes) that operate on the world by querying components. None of them store state — all state lives in components.

---

## fov_system.update_fov(world, game_map, player)
[systems/fov_system.py](../systems/fov_system.py)

Recomputes `game_map.visible` using `tcod.map.compute_fov` (symmetric shadowcast, radius 8). Then ORs visible into `game_map.explored` so fog-of-war tiles persist.

Called after every player move and on floor generation.

---

## render_system.render_all(console, world, game_map, player, message_log, floor)
[systems/render_system.py](../systems/render_system.py)

Three-pass render:

1. **Map** — bulk numpy `np.select` over `game_map.visible` / `game_map.explored` into `console.rgb`.
2. **Entities** — sorted by `Renderable.render_order`, only draws tiles inside `game_map.visible`.
3. **UI panel** — HP bar, XP/level line, floor number, message log.

Helper functions exposed for the Engine:
- `render_inventory(console, world, player, title)` — box + item list
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

## ai_system
[systems/ai_system.py](../systems/ai_system.py)

### act_one(world, game_map, player, message_log, eid)
Takes one action for a single `(Position, AI)` entity — called by `Engine._resolve_npc_turns` once per scheduled turn (see [architecture.md](architecture.md#turn-scheduling); a fast monster can get several calls per player turn).

- **confused** — decrements `turns_confused`; random step in any of 9 directions (including wait); attacks player if adjacent.
- **hostile** — no-ops if not in `game_map.visible`; attacks if adjacent (Manhattan distance ≤ 1); otherwise pathfinds with `tcod.path.SimpleGraph` + A* (cardinal cost 2, diagonal cost 3, other blockers inflate cost by 10).

### is_active(game_map, pos, ai) -> bool
Whether this AI entity is currently eligible for a scheduled turn — `True` for confused entities always, and for hostiles only while inside `game_map.visible`. The engine clamps ineligible hostiles' `Speed.next_turn` to "now" each dispatch instead of letting them bank owed turns while off-screen.

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
6. Place the dungeon `DOWN_STAIRS` at the south end + a `Stairs(floor=1)` entity.
7. Set player position to town centre.
8. Spawn the well, six `FarmPlot` entities south of House 1, and six named villagers (Gus the farmer is assigned the farm plots via `VillagerAI.work`).

Called by `Engine._new_floor()` when `floor == 0`.

---

## game_clock.GameClock
[game_clock.py](../game_clock.py)

Thornveil's calendar ("the Reckoning") and day/night clock. Deliberately not named `calendar.py` to avoid shadowing the stdlib module.

`total_minutes` is tracked in *economy*-minutes (the same unit `Speed.next_turn` uses — see [architecture.md](architecture.md#turn-scheduling)), not calendar minutes. `DAY_STRETCH` (economy-minutes per calendar-minute) controls how long a day/night cycle takes without touching `action_cost()`/Speed at all — every calendar-facing property converts through `to_calendar_minutes()` first.

- `advance(minutes=TURN_MINUTES) -> bool` — called once per player action from `Engine._do_enemy_turn` with however many economy-minutes that action's `_resolve_npc_turns` catch-up window spanned; returns `True` the instant a new *calendar* day begins.
- `to_calendar_minutes(economy_minutes) -> float` — divides by `DAY_STRETCH`; used both internally (for `hour`/`day_count`/etc.) and by `Engine._do_enemy_turn` to convert elapsed economy-time into calendar-time before calling `villager_system.update_needs`.
- Weeks are 7 named days (`WEEKDAYS`), years are 4 named "tides" of 30 days each (`TIDES`) standing in for seasons/months.
- `date_string()` — e.g. `"Wellday, the 14th of Harvest, Year 214 of the Reckoning"`.
- `light_level()` — 0.25 (deep night) .. 1.0 (full day), with 1-hour dawn/dusk ramps around `DAWN_HOUR`/`DUSK_HOUR`. Used by `render_system` to dim outdoor (`floor == 0`) tiles and entities at night; the dungeon is unaffected (torch-lit).

---

## villager_system
[systems/villager_system.py](../systems/villager_system.py)

Villagers eat, sleep, farm, and socialize on a daily schedule, overridden by urgent `Needs`.

### update_needs(world, elapsed_minutes)
Called once per player action with however many *calendar*-minutes just elapsed — the caller passes `game_clock.to_calendar_minutes(elapsed)`, not raw economy-minutes, so needs track real calendar time uniformly regardless of a villager's `Speed` or `game_clock.DAY_STRETCH`. `hunger` rises, `energy` drains while awake and restores while `sleeping`, `social` decays and restores while `socializing`, `hunger` falls while `eating` — all as `_PER_MINUTE` rates multiplied by `elapsed_minutes`. This keeps villager needs in sync with the calendar-hour-based schedule in `_decide_activity` no matter how long a day/night cycle has been stretched to be.

### act_one(world, game_map, clock, message_log, eid)
Takes one action for a single `(Position, VillagerAI, Needs)` entity — called by `Engine._resolve_npc_turns` once per scheduled turn:
1. **`_decide_activity`** — picks `sleeping`/`eating`/`socializing`/`working`/`wandering`. Priority: an in-progress eat/socialize commitment (`activity_timer`) → night → urgent need (`energy ≤ 15`, `hunger ≥ 75`, `social ≤ 20`) → scheduled meal hours (12:00/18:00) → scheduled social hours (20:00–22:00) → farm work (farmers only) → wandering.
2. **`_act`** — moves toward the activity's target (`home`, `social_spot`, or the next `FarmPlot` needing attention) using the same `tcod.path` A* approach as `ai_system._act_hostile`. When a farmer reaches a plot needing attention, calls `farm_system.tend()` and logs the action.

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
| `on_new_day(world, game_map)` | Called from `Engine._do_enemy_turn` when `GameClock.advance()` rolls a new day. Advances the stage of any plot watered the previous day, then resets `watered_today` and the tile back to dry `DIRT` for every tilled plot. |

A crop takes 3 in-game days of watering (`PLANTED → SPROUT → GROWING → RIPE`) to ripen; a missed watering day stalls growth without killing the plant.

---

## map generation — map_gen.generate_dungeon(...)
[map_gen.py](../map_gen.py)

Not a system file but uses the same pattern. Algorithm:

1. Attempt to place `max_rooms` rectangular rooms at random positions.
2. Skip any room that intersects an existing room.
3. Carve room interior to `FLOOR`.
4. First room: place the player at center, no monsters.
5. Subsequent rooms: connect center to previous room's center via an L-shaped Bresenham tunnel; call `_place_entities`.
6. After all rooms: carve `DOWN_STAIRS` at the last room's center; spawn a `Stairs` entity there.

Monster/item counts scale with floor depth. Trolls appear from floor 3 onward.
