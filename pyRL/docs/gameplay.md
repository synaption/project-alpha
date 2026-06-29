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

## The map

```
@  You (the player)
o  Orc
T  Troll
%  Corpse
!  Health potion
~  Scroll (color indicates type)
>  Stairs down
#  Wall
.  Floor (lit = currently visible, dark = explored)
```

Tiles you have never seen are completely black.

## Combat

Move into an enemy to attack. All combat is bump-to-attack — there is no separate attack key.

**Damage formula:** `max(0, attacker.power − defender.defense)`

| Enemy  | HP | ATK | DEF | XP |
|--------|-----|-----|-----|----|
| Orc    | 10  |  3  |  0  | 35 |
| Troll  | 16  |  4  |  1  | 100 |

Player starts with HP 30, ATK 5, DEF 2.

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
