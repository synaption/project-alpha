# Gameplay Guide

## Running the game

```bash
cd /home/bob/raylib/project-alpha/pyRL
python3 main.py
```

Requires `tcod` and `numpy`:
```bash
pip install tcod numpy
```

## Controls

| Key(s) | Action |
|--------|--------|
| Arrow keys | Move / attack |
| `h j k l` | Move west / south / north / east |
| `y u b n` | Move diagonally (NW / NE / SW / SE) |
| Numpad 1–9 | Move / attack in all 8 directions |
| `.` or numpad 5 | Wait one turn |
| `g` | Pick up item at your feet |
| `i` | Open inventory (then press letter to use item) |
| `d` | Drop item from inventory |
| `Tab` | Open in-game menu (Inventory / Active Quests / Maps / Stats; Up/Down changes section) |
| `>` (Shift+`.`) | Descend dungeon stairs (must be standing on `>`) |
| `<` (Shift+`,`) | Climb dungeon stairs up (must be standing on `<`) |
| Walk into a screen edge | Cross to the neighbouring surface screen |
| `m` | Open the world map (fast-travel) — surface only |
| `s` | Save game |
| `Shift+?` | Print key help to message log |
| `Esc` | Open pause menu |

## Menus

- **Opening screen**: press any key to continue to the home screen.
- **Home menu**: begin/continue, open options, or quit.
- **Pause menu** (`Esc` in-game): resume, open in-game menu, open options, save, or quit.
- **Options menu**: change display mode, brightness, audio levels, active tileset, tileset fallback chain preset, text/tile scale, palette pack, and control scheme.
- **Controls menu**: reference bindings for keyboard/mouse and controller mapping.
- **In-game menu** (`Tab`): view inventory, active quests, map info, and player stats.

## Tilesets, fallbacks, scaling, and palettes

- Tilesets are data-driven from `pyRL/data/tilesets/tilesets.json`.
- Rendering resolves each game tile ID by priority: selected tileset first, then fallback chain preset, then final `ascii` fallback.
- `hexany_visual` is the preferred non-ASCII profile (Hexany-inspired), while `enhanced_legacy` remains available for compatibility.
- Text scale controls the font pixel size (applies on restart) to keep high desktop readability.
- Tile scale controls glyph presentation density for visual tiles.
- Palette packs are loaded from `pyRL/data/palettes/palettes.json` and can be swapped at runtime.

## Starting in Thornveil

The game begins in the town of **Thornveil**. There are no enemies here. Explore freely, talk to the villagers, and prepare before descending.

The **dungeon entrance** (`>`) is at the south end of the vertical road; press `>` on it to descend. Thornveil is **ground level** — to leave, just walk off any edge of the screen into the surrounding wilderness.

### Walking the surface

The world above ground is a grid of screens. **Walk off the edge of a screen** and you cross onto the neighbouring one, arriving at the opposite edge — no stairs, no menus. Keep going and you'll reach the wilderness screens between towns, and eventually other towns. Walk to the very edge of the world and you'll be told so; there's nowhere further that way.

Press **`m`** to open the **world map** — a zoomed-out view where each cell is a 3×3 block of screens (Caves-of-Qud style). Move the cursor over a region you've already **discovered** and press Enter to **fast-travel** there; the journey takes in-game time (so time of day advances and towns live on while you travel). You can't fast-travel with an enemy nearby.

### Other towns

Thornveil is one of several towns scattered across the surface. Each sits on its own screen; you reach them by walking (or fast-travelling). Every town has its own dungeon beneath it (a separate dungeon from Thornveil's), its own townsfolk, and — because towns other than Thornveil are procedurally generated — a different layout each seed, though every one is guaranteed an inn, a guard post, a mayor, and a well.

Everything is **persistent within a playthrough**: a screen or dungeon depth is only generated the first time you set foot on it, then holds still. Whatever you leave behind — a cleared room, a dead orc, a dropped scroll, a tilled field — is exactly how you'll find it when you return. The same **seed** always builds the same world, so two players on one seed explore identical maps.

While you're away, the world doesn't fully pause — simulation fades with distance. Monsters and the trading caravan within a screen (or a dungeon level) or so of you keep moving even when you're not on their exact screen; towns you've left keep their clocks running so villager needs and crops catch up when you come back. Only things genuinely far away freeze exactly as you left them.

### Villagers

| Name | Location | What they say |
|------|----------|---------------|
| Mira | Inside the Inn (left building) | Inn lore, survival tips |
| Aldric | Inside the Shop (right building) | Item and enemy hints |
| Captain Vex | South of the Guard House (center) | Dungeon warning |
| Elder Maren | Town square (west side) | Dungeon history |
| Pip | Town square (east side) | Enthusiastic child |
| Gus | Inside House 1 (lower-left) | Retired adventurer tips |

Bump into any villager to open dialog. Press any key to advance lines; `Esc` to close early. Talking does **not** spend a turn. While talking, the dialog box shows the villager's current activity (e.g. `(sleeping)`, `(working)`) in gray above their line.

### The Reckoning — Thornveil's calendar

Time passes one 10-minute tick per player action. A day is split into named weekdays (Emberday, Stoneday, Wellday, Marketday, Huntday, Restday, Duskday) and the year into four 30-day "tides" — Thaw, Sunhigh, Harvest, Frostveil — dating from the founding of Thornveil over the ruins (currently Year 214 of the Reckoning). The current time and day appear in the left panel; the full date is announced in the message log each dawn.

Dusk falls at 20:00 and dawn breaks at 6:00. Outdoors in Thornveil, visible tiles and villagers dim toward deep night and brighten back up through a 1-hour dawn/dusk ramp. The dungeon is unaffected — it's always torch-lit down there.

### Villager life

Villagers keep a daily routine, tracked by hunger, energy, and social needs: they sleep at home overnight, eat around midday and evening, socialize in the town square in the early evening, and otherwise wander or work. An urgent need (near-starving, exhausted, or lonely) interrupts the schedule early.

Gus the farmer tends a small plot of farmland south of House 1. Farming is a four-step, multi-day cycle:

1. **Till** bare ground into workable dirt.
2. **Plant** a seed in tilled soil.
3. **Water** the seed — once per day. A plant only grows on days it was watered.
4. After three watered days the crop **ripens**; Gus harvests it and the plot returns to tilled soil, ready to replant.

Watch the farm patch over several in-game days to see plots move through seed (`.`) → sprout (`,`) → growing (`"`) → ripe (`Y`).

While you're away — down in a dungeon or off in another region — a town doesn't just pause: the moment you return, villager needs and farm growth are caught up for however much calendar time passed, so a long delve can mean crops have ripened (or the field's rhythm slipped) by the time you're back. Dungeons, by contrast, freeze exactly as you left them once they're far enough behind you.

---

## Saving

Press `s` at any time during your turn to save (this doesn't cost game time). The game auto-loads that save the next time you start it, picking up exactly where you left off — same floors, same villagers, same farm progress, same inventory. There's a single save slot. Because death is permanent (see below), the save is deleted the moment you die — it's there to let you stop and resume one ongoing life, not to undo a bad fight.

Dungeon floors you haven't reached yet are generated from a random seed chosen when you start a new game — so within one playthrough, revisiting an unexplored floor for the first time is still a surprise, even though everything you've already been to stays put.

---

## The map

```
@  You (the player) — or a villager (town only)
c  Trading caravan (roams the surface)
o  Orc
T  Troll
%  Corpse
!  Health potion
~  Scroll (color indicates type) — or water on the surface
O  Well (decorative, blocks movement)
>  Stairs down (dungeon entrance in a town / deeper in a dungeon)
<  Stairs up (within a dungeon)
^  Forest (surface, walkable)
▲  Mountain (surface, blocks movement)
+  Door
#  Wall
.  Floor / grass / cobblestone / tilled dirt (lit vs dark) — also a planted seed on farmland
,  Sprouting crop
"  Growing crop
Y  Ripe crop, ready to harvest
```

Walk off any edge of a surface screen to cross to the next one. Press `m` for the world map.

Tiles you have never seen are completely black.

## Combat

Move into an enemy to attack. All combat is bump-to-attack — there is no separate attack key.

**Damage formula:** `max(0, attacker.power − defender.defense)`

| Enemy  | HP | ATK | DEF | XP | Speed |
|--------|-----|-----|-----|----|-------|
| Orc    | 10  |  3  |  0  | 35 | 110 |
| Troll  | 16  |  4  |  1  | 100 | 85 |

Player starts with HP 30, ATK 5, DEF 2, Speed 100.

Speed governs how often a creature acts, not how hard it hits: at Speed 100 (baseline), one action costs `game_clock.TURN_MINUTES` game-minutes. Orcs (Speed 110) are quick raiders that get an extra action roughly every ten of yours; trolls (Speed 85) are slow brutes that occasionally miss a beat. Watch for it in a crowd — a pack of orcs can close distance faster than their Speed alone suggests, because each one is squeezing in bonus turns.

## Items

| Item | Color | Effect |
|------|-------|--------|
| Health Potion `!` | Purple | Heal 40 HP (can't overheal) |
| Lightning Scroll `~` | Yellow | 20 damage to nearest visible enemy within 5 tiles |
| Fireball Scroll `~` | Orange | 12 damage to all entities within 3 tiles of nearest visible enemy |
| Confusion Scroll `~` | Magenta | Nearest visible enemy stumbles randomly for 10 turns |

Press `i` to open inventory, then the letter shown next to the item to use it.  
Scrolls and potions are consumed on use.

## Leveling up

Killing enemies earns XP. When you accumulate enough, you'll see the level-up menu:

```
Level Up!
You have gained a level!
Choose an attribute to increase:

(a) +20 Max HP   (current: 30)
(b) +1 Attack    (current: 5)
(c) +1 Defense   (current: 2)
```

XP thresholds: `200 + (current_level × 150)`. Level 1→2 costs 350 XP.

## Death

Death is **permanent**. The game ends, the save file is deleted, and the only option is to quit (`Esc`). Start the game again for a new seed and a fresh dungeon.

## Tips

- The first room of every dungeon floor is always safe — no monsters spawn there, and it's also where that floor's up staircase is.
- Trolls are tough; use scrolls on them before engaging in melee.
- A confused enemy still attacks if you walk into it.
- Pick up and hoard health potions; they are your only healing.
- The fireball scroll damages you too if you're within radius 3.
- The lightning scroll requires line of sight within 5 tiles — use it early in a fight before the enemy closes the gap.
- Cleared floors stay cleared — retreating to a floor you've already fought through is a legitimate way to regroup, since nothing there respawns.
- Save before doing anything risky; `s` costs no time.
