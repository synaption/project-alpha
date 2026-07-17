# pyRL2

GOALS:
- use ecs, esper
- make a roguelike game in python that runs in the terminal and later can be
  rendered with tcod, pygame, raylib, opengl, or something else.
- start with very basic and go from there
- wasd movement

## Run

    python3 main.py

Move: wasd (also arrow keys / hjkl).  Quit: q or Esc.
(Needs a real terminal — curses won't run from an IDE output pane.)

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
