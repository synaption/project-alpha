# CircuitCities — Development Roadmap

The current codebase is a Mini Metro survival prototype. The target is a city-builder with layers and vias. These phases treat that as a ground-up redesign of the game loop, keeping only the Bevy ECS scaffolding and rendering approach.

---

## Phase 0: Foundation Rewrite

The survival loop (spawn timers, game-over, passenger routing) needs to be removed and replaced with the city-builder loop. This is the biggest structural change.

**Remove from current code:**
- `spawn_stations` system and `SpawnTimers` resource
- `spawn_passengers` system
- `move_trains` system (replace with carrier visualization)
- Game-over check
- `ActiveLine` / drag-to-connect as the primary input (replace with build modes)

**Add:**
- `Layer` enum and `active_layer: Layer` resource
- `District` component (replaces `Station`)
- `Trace` component (replaces implicit line segments)
- `Via` component (new)
- `Route` resource (ordered list of districts+vias on one layer)
- `Game` resource: `credits: f32`, `income_rate: f32`, `mode: GameMode`
- `BuildMode` resource: `PlacingDistrict(DistrictKind)` | `RoutingLayer(Layer)` | `PlacingVia(LayerSet)` | `Idle`

**Keep:**
- `Rng` resource (custom xorshift PRNG)
- `draw` system skeleton
- `update_ui` system skeleton
- Bevy app bootstrap structure

**New systems (stubs for Phase 0):**
- `build_input` — handle clicks/drags for placing districts, routing traces, placing vias
- `layer_switch` — Tab/1/2/3 input
- `service_score` — placeholder (always returns 50.0)
- `city_growth` — placeholder (disabled)
- `income` — placeholder (trickle 1 credit/sec)
- `draw_layers` — render each layer's traces, dimming inactive ones
- `draw_districts` — render all districts by type and tier
- `draw_vias` — render all vias with their ring indicators

Goal: by end of Phase 0, the player can place districts, draw traces on the active layer, place vias, and switch layers. Nothing grows yet, but the core interaction is functional.

---

## Phase 1: Layers and Vias Working

Make layers meaningful and vias functional.

### 1.1 Layer rendering
- [ ] Render traces per-layer with correct colors (amber/cyan/green)
- [ ] Dim inactive layers to 25% opacity
- [ ] Active layer renders at full brightness
- [ ] Substrate dot-grid background

### 1.2 Layer switching
- [ ] Tab cycles A→B→C→A
- [ ] 1/2/3 jump to layer directly
- [ ] Layer panel indicator on left edge of screen

### 1.3 Via placement and rendering
- [ ] Place via with V key + click
- [ ] Via type selector (cycle with repeated V, or click to open type picker)
- [ ] Draw vias with concentric rings per connected layer
- [ ] Vias deduct credits on placement

### 1.4 Trace routing
- [ ] Drag from district/via to district/via on active layer
- [ ] Preview trace (dashed) while dragging, with credit cost label
- [ ] Confirm on release: create trace, deduct credits
- [ ] Right-click trace to remove (partial refund)
- [ ] Traces visually connect to their endpoint pads

### 1.5 Route and carrier
- [ ] Route = ordered node list on one layer
- [ ] Carrier auto-spawns when route has ≥ 2 nodes
- [ ] Carrier moves back and forth along route
- [ ] Carrier color matches layer color

---

## Phase 2: Service Score and Growth

Make connectivity meaningful — districts that are connected should thrive.

### 2.1 Service score
- [ ] Flood-fill reachability from each district along its layer's traces
- [ ] Via crossing: flood-fill can jump to another layer's traces at a via
- [ ] Identify supply nodes reachable (Power Plants for power layer, etc.)
- [ ] Compute weighted service score per district based on demand profile
- [ ] Display service score as a fill/progress ring around district

### 2.2 City growth
- [ ] Track `tier_timer` per district
- [ ] Advance tier when score sustained above threshold
- [ ] Decay tier timer when score falls below floor
- [ ] Tier-up animation: scale pulse + radiating dots
- [ ] Visual tier indicator: double ring at tier 2, animated ring at tier 3

### 2.3 Income
- [ ] Each district generates credits/sec based on tier × (service_score / 100)
- [ ] Credits display in HUD with income rate (+X/s)
- [ ] Building is disabled when credits < cost (show red cost preview)

### 2.4 Congestion
- [ ] Track load per trace (number of routes using it × carrier load proxy)
- [ ] Congested traces render with red tint
- [ ] Congestion reduces service score for downstream districts
- [ ] No game-over — just visual indicator and reduced growth

---

## Phase 3: Districts and Build Panel

Full set of district types with distinct demand profiles and costs.

### 3.1 Build panel
- [ ] Bottom HUD bar with district type shortcuts (R/B/D/T/H/I)
- [ ] Click district type to enter placement mode
- [ ] Preview district at cursor (ghost, shows cost and spacing check)
- [ ] Click to place; invalid placement turns preview red

### 3.2 All district types
- [ ] Residential: needs Transit + Power + Data (low), generates population
- [ ] Power Plant: needs Data (low), generates power supply on power layer
- [ ] Data Center: needs Power (high) + Data (med), generates data supply
- [ ] Transit Hub: needs Power (med) + Transit (high), generates transit supply
- [ ] Commercial: needs all three (med), high income
- [ ] Industrial: needs Power (high) + Transit (med), unlocks future upgrades

### 3.3 District shapes
- [ ] Draw each type with its unique silhouette (see VISUAL.md)
- [ ] Interior detail lines (windows, bolts, dots, crosshair)
- [ ] Tier visual variants (single/double/animated ring)

---

## Phase 4: Scenarios and Sandbox

Two fully playable modes.

### 4.1 Sandbox mode
- [ ] Open canvas, no objectives
- [ ] Credits regenerate slowly even with no districts (seed budget)
- [ ] HUD shows total population as the loose metric
- [ ] No end condition

### 4.2 Scenario system
- [ ] `Objective` enum with conditions (see MECHANICS.md)
- [ ] Scenario definition: starting map, starting credits, list of objectives
- [ ] Objectives panel in HUD (checkmarks as conditions are met)
- [ ] Scenario complete screen on all objectives met

### 4.3 Starter scenarios (3 minimum)
- [ ] Tutorial scenario: 3 pre-placed districts, objectives guide first connections
- [ ] "Northern Quarter": connect an isolated industrial zone to power + transit
- [ ] "High Density": reach Tier 3 on a residential block before time runs out

---

## Phase 5: Polish

- [ ] Smooth trace routing (prefer axis-aligned segments with 45° turns)
- [ ] Carrier trail (ghost frames for load visualization)
- [ ] Sound: placement clicks, tier-up chime, congestion warning
- [ ] Animated node rings on district placement (Mini Metro–style)
- [ ] Scenario complete animation + summary stats
- [ ] Persist high score / best city to disk

---

## What the current prototype becomes

The current codebase (survival clone) becomes a historical reference point. The ECS architecture and rendering approach are worth keeping. The game-loop logic (timers, overflow, train routing) is replaced wholesale in Phase 0. Think of Phase 0 as "gutting the engine and installing a new one in the same chassis."

If you want to preserve the prototype for comparison, tag the current commit as `v0-survival-prototype` before starting Phase 0.
