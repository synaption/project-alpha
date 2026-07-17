# pyRL2

GOALS:
- use ecs, esper
- make a roguelike game in python that runs in the terminal and later can be
  rendered with tcod, pygame, raylib, opengl, or something else.
- start with very basic and go from there
- wasd movement, fully configurable configurable controls, controller support eventually
- lot's of simulation, testing, and prcedural generation
- mods are a top priority.  anybody should easily be able to add there own files to add or change content.
- seed based
## Run

    python3 main.py

Or bypass the title screen/main menu and load a specific save file:

    python3 main.py --save_file data/saves/my_run.json

Move: wasd (also arrow keys / hjkl). Menu: Esc. Save/Quit are in the menu.
(Needs a real terminal — curses won't run from an IDE output pane.)

## Menus

- Startup flow: Title Screen -> Main Menu (`Continue`, `New Game`, `Quit`)
- In-game menu: press `Esc` to open Pause Menu (`Save Game`, `Options`, `Quit`)
- Pause menu navigation: arrows/WASD to move selection, Enter to select, `Esc` to resume game
- Options menu: toggle `Fullscreen` and `Show FPS`; changes are written to working options file

## Saves and options

- Default save file: `data/saves/default_save.json`
- Default options file: `data/config/default_options.json`
- Working options file: `data/config/options.json`
- On startup, if `data/config/options.json` is missing, it is copied from
  `data/config/default_options.json`.
- User save files can live in `data/saves/*.json` and can be loaded directly
  with `--save_file`.
- `--save_file` also bypasses title screen and main menu.

## Documentation

Full docs live in the [wiki/](wiki/Home.md) — architecture, ECS model, per-module
reference, how to add a renderer backend, and the roadmap.

## Layout

| file                   | role                                                      |
|------------------------|-----------------------------------------------------------|
| `main.py`              | entry point + turn loop                                   |
| `components.py`        | ECS data: `Position`, `Renderable`, `Player`              |
| `game_map.py`          | tile grid (renderer-agnostic)                             |
| `systems.py`           | `MovementProcessor`, `RenderProcessor` (esper processors) |
| `renderer/base.py`     | `Renderer` interface — the seam for swapping backends     |
| `renderer/terminal.py` | curses implementation of `Renderer`                       |

ECS via [esper](https://github.com/benmoran56/esper) (3.x, module-level API).

## Swapping renderers later

Game/system code never imports curses. To add tcod/pygame/raylib, implement the
`Renderer` interface (`setup/teardown/clear/draw_glyph/draw_text/present/
poll_action`) and pass that instance to `RenderProcessor` in `main.py`. Input is
already abstracted to action strings (`move_up`, `quit`, …), so nothing else
changes.
