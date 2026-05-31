# Circuit Cities

A network-routing puzzle game inspired by Mini Metro and Mini Motorways. Route infrastructure traces between city nodes, launch carriers along those routes, and keep the city's circuits from overloading as the city grows.

Built with [Bevy](https://bevy.org) v0.18 (ECS architecture), renders entirely via Bevy's immediate-mode gizmos — self-contained binary, no asset files required.

## Design Docs

- [DESIGN.md](docs/DESIGN.md) — Game concept, pillars, core loop, node types
- [MECHANICS.md](docs/MECHANICS.md) — Full mechanics spec (timing, systems, algorithms)
- [VISUAL.md](docs/VISUAL.md) — Color palette, node shapes, trace style, HUD layout
- [ROADMAP.md](docs/ROADMAP.md) — Phased implementation plan

## Current State

Functional Mini Metro–style prototype:
- 3 routes (drag endpoints to extend)
- Nodes appear over time; signals queue at nodes
- Carriers shuttle along routes, deliver signals, score points
- Game over when a node's queue overflows

See [ROADMAP.md](docs/ROADMAP.md) for what's planned next.

## ECS Structure

| File | Role |
|------|------|
| `components.rs` | Per-entity data: `Shape`, `Station`, `Train`, `ScoreText` |
| `resources.rs` | Global state: `Game`, `Lines`, `ActiveLine`, `DragState`, `SpawnTimers`, `Rng` |
| `systems.rs` | All logic: spawning, input, carrier movement, rendering, HUD |
| `main.rs` | App bootstrap: registers resources, schedules systems |

## Controls

- **1 / 2 / 3** — select active route
- **Click a node and drag to another** — extend the active route (only from an endpoint)

## Run

```bash
cargo run            # debug
cargo run --release  # optimised
```

First Bevy build takes a few minutes (compiles the engine). Incremental builds are fast.

## Export Windows .exe

```powershell
# On Windows:
cargo build --release
# -> target\release\circuit-cities.exe
```

```bash
# Cross-compile from Linux (requires cargo-xwin):
cargo install cargo-xwin
rustup target add x86_64-pc-windows-msvc
cargo xwin build --release --target x86_64-pc-windows-msvc
# -> target/x86_64-pc-windows-msvc/release/circuit-cities.exe
```
