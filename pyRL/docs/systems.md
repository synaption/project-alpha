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

## ai_system.run_ai(world, game_map, player, message_log)
[systems/ai_system.py](../systems/ai_system.py)

Iterates all entities with `(Position, AI)`. Per entity:

- **confused** — decrements `turns_confused`; random step in any of 9 directions (including wait); attacks player if adjacent.
- **hostile** — skips if not in `game_map.visible`; attacks if adjacent (Manhattan distance ≤ 1); otherwise pathfinds with `tcod.path.SimpleGraph` + A* (cardinal cost 2, diagonal cost 3, other blockers inflate cost by 10).

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
8. Spawn the well and six named villagers.

Called by `Engine._new_floor()` when `floor == 0`.

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
