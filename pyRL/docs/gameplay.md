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
| `>` (Shift+`.`) | Descend stairs (must be standing on `>`) |
| `Shift+?` | Print key help to message log |
| `Esc` | Quit |

## Starting in Thornveil

The game begins in the town of **Thornveil**. There are no enemies here. Explore freely, talk to the villagers, and prepare before descending.

The **dungeon entrance** (`>`) is at the south end of the vertical road. Step on it and press `>` to descend. There is no returning to town once you enter the dungeon.

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

---

## The map

```
@  You (the player) — or a villager (town only)
o  Orc
T  Troll
%  Corpse
!  Health potion
~  Scroll (color indicates type)
O  Well (decorative, blocks movement)
>  Dungeon entrance / stairs down
+  Door
#  Wall
.  Floor / grass / cobblestone / tilled dirt (lit vs dark) — also a planted seed on farmland
,  Sprouting crop
"  Growing crop
Y  Ripe crop, ready to harvest
```

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

Death is **permanent**. The game ends and the only option is to quit (`Esc`). Run again for a new procedurally generated dungeon.

## Tips

- The first room is always safe — no monsters spawn there.
- Trolls are tough; use scrolls on them before engaging in melee.
- A confused enemy still attacks if you walk into it.
- Pick up and hoard health potions; they are your only healing.
- The fireball scroll damages you too if you're within radius 3.
- The lightning scroll requires line of sight within 5 tiles — use it early in a fight before the enemy closes the gap.
- Press `>` only when you're ready; you can't go back up.
