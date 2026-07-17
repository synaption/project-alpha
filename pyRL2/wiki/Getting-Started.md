# Getting Started

## Requirements

- **Python 3.12+** (uses `str | None` syntax in annotations)
- **[esper](https://github.com/benmoran56/esper) 3.x** — the ECS library
- **curses** — for the terminal backend (standard library on Linux/macOS; on
  Windows use `windows-curses` or run under WSL)

## Install

```bash
pip install esper
```

## Run

```bash
cd project-alpha/pyRL2
python3 main.py
```

> ⚠️ curses needs a **real terminal**. It will not run from an IDE output pane or
> a captured/non-TTY process.

## Controls

| Action | Keys |
|--------|------|
| Move up | `w` · `k` · ↑ |
| Move down | `s` · `j` · ↓ |
| Move left | `a` · `h` · ← |
| Move right | `d` · `l` · → |
| Quit | `q` · `Esc` |

Key-to-action mapping lives in [`renderer/terminal.py`](../renderer/terminal.py);
see [Renderers](Renderers.md) to change it.

## Verifying without a terminal

Because the renderer is decoupled, you can drive the whole game headless with a
fake renderer that records `draw_glyph` calls and feeds actions to
`esper.process(...)`. This is how movement and collision are tested. See
[Architecture](Architecture.md#testing-headless).
