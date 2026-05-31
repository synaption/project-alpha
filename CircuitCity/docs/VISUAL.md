# CircuitCities — Visual Design Guide

## Aesthetic Direction

The city IS the circuit board. Every visual element maps to a real PCB concept:

| Game element | PCB equivalent |
|-------------|---------------|
| Canvas / map | PCB substrate (FR4) |
| Districts | Through-hole components |
| Traces | Copper traces |
| Vias | Plated through-holes (vias) |
| Layers | Copper layers (Top, Inner, Bottom) |
| Carriers | Signal pulses |

The aesthetic is **dark substrate, bright traces, glowing vias**. It should read like a professional PCB design tool that came alive — not a cartoon, not a retro game, something precise and slightly industrial.

---

## Color Palette

### Substrate (background)

| Role | Hex | Notes |
|------|-----|-------|
| Background | `#0B1210` | Very dark, green-black (FR4 board color) |
| Dot grid | `#0F1A15` | Barely visible alignment grid (12px spacing) |
| Selection highlight | `#FFFFFF18` | Light overlay on hovered item |

### Layers

Each layer has a primary, a glow, and a congested (warning) variant:

| Layer | Primary | Glow | Congested |
|-------|---------|------|-----------|
| **Power** (A) | `#F5A623` | `#F5A62340` | `#FF4020` |
| **Data** (B) | `#00C8E8` | `#00C8E830` | `#FF4020` |
| **Transit** (C) | `#39D353` | `#39D35330` | `#FF4020` |

Inactive layers (not the active layer) render at 25% opacity. The active layer is full brightness. This creates clear focus without hiding the other layers.

### Districts

Districts use a type-color for their outline, dark fill, and a subtle inner glow when at high tier.

| District | Outline | Fill | Tier 2 glow | Tier 3 glow |
|----------|---------|------|------------|------------|
| Residential | `#39D353` | `#001A06` | faint green | pulsing green |
| Power Plant | `#F5A623` | `#1A1000` | faint amber | pulsing amber |
| Data Center | `#00C8E8` | `#001518` | faint cyan | pulsing cyan |
| Transit Hub | `#39D353` | `#001A06` | faint green | pulsing green |
| Commercial | `#C8A0FF` | `#0A0010` | faint violet | pulsing violet |
| Industrial | `#A0A0A0` | `#101010` | faint grey | pulsing grey |

### Vias

Vias are always visible on all layers (they cross through).

| Via type | Colors |
|----------|--------|
| Power-Data | Amber + Cyan rings |
| Power-Transit | Amber + Green rings |
| Data-Transit | Cyan + Green rings |
| Full (3-layer) | All three rings |

Via base: filled circle `#1A2020`, radius 8px. Rings: 2px strokes in layer colors, 1px apart.

### HUD

| Element | Color |
|---------|-------|
| Text | `#B8C8C0` |
| Labels / secondary | `#507060` |
| Credit value | `#F5A623` (amber = money) |
| Active layer indicator | Layer primary color |
| Inactive layer indicator | `#304030` |

---

## District Shapes

Districts are drawn as component-like silhouettes. Each must be distinguishable at a glance.

### Residential Block — Rounded rectangle
- 28×22px, 4px corner radius
- Outline: 2px green
- Interior: 3 horizontal rows of tiny squares (windows)
- Tier 2: second outline ring 3px outside, opacity 60%
- Tier 3: outer ring animates a slow fill-clockwise (like a progress ring)

### Power Plant — Diamond (rotated square)
- 24px diagonal, rotated 45°
- Outline: 2px amber
- Interior: lightning bolt shape (two lines)
- Tier 2+: same double ring treatment

### Data Center — Square with corner cutouts
- 26×26px, 5px corner cuts (octagonal silhouette)
- Outline: 2px cyan
- Interior: grid of tiny dots (4×4)
- Tier 2+: same double ring treatment

### Transit Hub — Circle
- Radius 14px
- Outline: 2px green
- Interior: + crosshair
- Tier 2+: same double ring treatment

### Commercial District — Pentagon (flat-bottom)
- Circumradius 15px, flat bottom
- Outline: 2px violet
- Interior: $ symbol (two lines)

### Industrial Zone — Hexagon (flat-top)
- Circumradius 16px
- Outline: 2px grey
- Interior: gear symbol (rough approximation with gizmo lines)

---

## Trace Rendering

Traces are drawn per-layer. Render order: inactive layers first (dimmed), then active layer on top.

**Each trace = two draw calls:**
1. Glow pass: width `trace_width + 8px`, color at 15% opacity
2. Solid pass: width `trace_width`, color at 80% opacity

| Layer | Trace width |
|-------|------------|
| Power | 4px |
| Data | 2px |
| Transit | 5px |

**Congested trace:** Replace layer color with `#FF4020`, glow widens to +14px.

**Draft trace (while player is dragging):** Dashed, 60% opacity, same width. Show credit cost as a small text label near the midpoint.

**Pad at endpoints:** A small filled circle (radius = trace_width + 2px) at each endpoint where a trace meets a district or via. Color matches trace layer.

---

## Via Rendering

Vias are always drawn on top of all layers at full opacity (they're physical objects that pierce all layers).

```
draw_via(pos, connects: LayerSet):
  filled circle(pos, r=8, color=#1A2020)   // substrate fill
  if connects.has(Power):
    circle(pos, r=8, stroke=2, color=Amber)
  if connects.has(Data):
    circle(pos, r=11, stroke=2, color=Cyan)
  if connects.has(Transit):
    circle(pos, r=14, stroke=2, color=Green)
```

Three-layer via has three concentric rings. Two-layer via has two. The innermost ring corresponds to the "lowest" layer (Power).

**Via hover:** All rings brighten. A small tooltip shows which layers it connects.

---

## Carrier Rendering

Carriers move along routes. They are visual indicators of signal flow, not discrete agents.

**Shape:** Rectangle aligned to trace direction. Size: 12×6px.
**Color:** Route layer's primary color.
**Glow:** Rectangle + 6px glow pass at 25% opacity.

**Load indication:**
- 0–30% load: dim carrier, slow movement, no trail
- 30–70% load: normal brightness, normal speed, short trail (3 ghost frames)
- 70–100% load: bright, fast, long trail (6 ghost frames)
- >100% (congested): red carrier, fast, pulsing

Trail = draw the carrier at previous positions with decreasing opacity.

---

## Layer Panel (HUD)

The layer selector lives on the left edge of the screen, vertically stacked.

```
┌───┐
│ A │  ← Power layer (amber, if active: bright + underline)
├───┤
│ B │  ← Data layer
├───┤
│ C │  ← Transit layer
└───┘
```

Each button is 32×32px. Active layer: full color, 2px border. Inactive: 20% color, no border.
Pressing 1/2/3 or Tab activates layers and updates this indicator.

---

## Full HUD Layout

```
┌─────────────────────────────────────────────────────────────────────┐
│ ┌───┐  Credits: 248 ▲12/s      [Scenario: Connect the North]        │
│ │ A │                                                               │
│ │ B │                                                               │
│ │ C │           [game world]                                        │
│ └───┘                                                               │
│         [ BUILD PANEL: R B D T H I ]     Via: V                    │
└─────────────────────────────────────────────────────────────────────┘
```

- Top-left: credits + income rate
- Top-right: current scenario objective (if any)
- Left edge: layer panel
- Bottom: build panel shortcuts (R=Residential, B=Power plant, D=Data center, T=Transit hub, H=Commercial, I=Industrial, V=Via)

In sandbox mode, the scenario objective area shows total population instead.

---

## Growth Animation

When a district advances a tier:
1. Brief scale pulse (1.0 → 1.25 → 1.0 over 0.4s)
2. Ring of dots radiates outward from the district (like a ripple)
3. District shape redraws at new tier style

When a via is placed:
1. Rings animate in from center outward (each ring appears with 0.05s delay)
2. Brief flash at full white opacity

---

## Scenario Complete Screen

```
┌───────────────────────────────────────────────┐
│                                               │
│         CIRCUIT COMPLETE                      │
│                                               │
│   Population:      2,340                      │
│   Districts:       8 (3 at Tier 3)            │
│   Credits earned:  1,840                      │
│   Time:            7:32                       │
│                                               │
│         [Continue in Sandbox]   [Menu]        │
│                                               │
└───────────────────────────────────────────────┘
```
