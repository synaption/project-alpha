# CircuitCities — Mechanics Reference

## Core Systems

The game has no update loop that fights the player. These systems run continuously and inform the player about their city's state:

1. `service_score` — recalculates each district's score based on connectivity
2. `city_growth` — advances district tiers based on sustained service score
3. `income` — drains/fills the credit pool based on district production
4. `congestion` — flags traces that are over capacity
5. `draw` — renders layers, traces, vias, districts, HUD
6. `build_input` — handles player building and routing actions
7. `layer_switch` — handles Tab/1/2/3 to change active layer

No spawn timers. No "game over" check. The player drives the pacing entirely.

---

## Data Model

### Layers

```rust
pub enum Layer { Power, Data, Transit }
```

The active layer is a global resource. All trace-routing operations act on the active layer.

### Districts (nodes)

```rust
pub struct District {
    pub kind: DistrictKind,
    pub tier: u8,              // 1–3
    pub service_score: f32,    // 0.0–100.0, recalculated each frame
    pub tier_timer: f32,       // seconds at current service threshold
    pub population: u32,       // grows with tier (residential only)
}

pub enum DistrictKind {
    Residential, PowerPlant, DataCenter,
    TransitHub, Commercial, Industrial,
}
```

Districts are placed by the player. They do not auto-spawn.

### Traces

```rust
pub struct Trace {
    pub layer: Layer,
    pub from: Entity,    // district or via
    pub to: Entity,      // district or via
    pub capacity: u32,   // max signal throughput (default 10)
    pub load: u32,       // current signal throughput (computed)
}
```

Traces live on exactly one layer. They connect two `Endpoint` entities (district or via).

### Vias

```rust
pub struct Via {
    pub position: Vec2,
    pub connects: LayerSet,  // which layers this via bridges (bitfield: A, B, C)
}
```

A via is a point entity, not connected to a specific district. It acts as a passthrough junction for traces from different layers to meet. Traces on layer A and layer B can both terminate at the same via; signals can then cross from one to the other.

### Routes (carriers)

```rust
pub struct Route {
    pub layer: Layer,
    pub nodes: Vec<Entity>,     // ordered list of districts/vias
    pub carrier: Option<Entity>,
}
```

A route is an ordered sequence of districts and vias connected by traces on the same layer. When a route is fully connected (2+ nodes), a carrier auto-launches. Carriers are visual — they move along the route and represent signal flow intensity. They do not carry discrete passenger units; the "signal" model is continuous flow.

---

## Service Score Calculation

Service score is calculated per district per frame based on reachability.

```
for each district D:
  for each layer L in D.demands:
    reachable[L] = flood-fill from D along traces on layer L,
                   crossing vias where L is in via.connects
    coverage[L]  = count of supply nodes reachable on layer L
                   (e.g., Power Plants on the Power layer)
    layer_score[L] = min(coverage[L] / D.demand_threshold[L], 1.0) * 100

  D.service_score = weighted_average(layer_score, D.demand_weights)
```

Example: A Residential block demands Transit (weight 50%), Power (weight 30%), Data (weight 20%).
- If it can reach 1 transit hub and 1 power plant but no data center → score = 50+30+0 = 80

A district with no connections at all scores 0.

---

## City Growth

```
each frame (dt):
  for each district D:
    if D.service_score >= TIER_UP_THRESHOLD[D.tier]:
      D.tier_timer += dt
      if D.tier_timer >= TIER_UP_DURATION[D.tier] AND D.tier < 3:
        D.tier += 1
        D.tier_timer = 0
        trigger growth animation
    else if D.service_score < TIER_DOWN_THRESHOLD[D.tier]:
      D.tier_timer -= dt * 0.5  // decay slower than growth
      if D.tier_timer <= 0 AND D.tier > 1:
        D.tier -= 1
        D.tier_timer = TIER_UP_DURATION[D.tier - 1]  // reset to partial progress
    else:
      // neutral band: no change
```

| Tier | Score to advance | Score to decline | Time to advance |
|------|-----------------|-----------------|-----------------|
| 1→2  | ≥ 50            | < 20            | 30s             |
| 2→3  | ≥ 80            | < 40            | 60s             |
| 3 (max) | —            | < 60            | —               |

Tier affects district capacity (queue size) and income rate.

---

## Income

```
each second:
  for each district D:
    credits += D.income_rate[D.tier] * (D.service_score / 100.0)
```

A district at tier 2 with service score 60 earns 60% of its tier-2 income rate. This creates a natural incentive to improve service.

| District | Tier 1 income/s | Tier 2 income/s | Tier 3 income/s |
|----------|----------------|----------------|----------------|
| Residential | 0.5 | 1.2 | 2.5 |
| Power Plant | 0.2 | 0.5 | 1.0 |
| Data Center | 1.0 | 2.5 | 5.0 |
| Transit Hub | 0.3 | 0.8 | 1.8 |
| Commercial | 1.5 | 3.5 | 7.0 |
| Industrial | 0.8 | 2.0 | 4.5 |

---

## Build Input

The player interacts through a **build mode** and a **route mode**.

### Build Mode

Activated by selecting a district type from the build panel (or pressing B to toggle panel).

```
click on empty canvas space:
  if credits >= district_cost[selected_kind]:
    place district at cursor
    credits -= cost
```

Districts cannot be placed overlapping existing districts or vias. Minimum spacing: 80px.

### Route Mode

Activated by selecting a layer (1/2/3 or Tab). This is the default mode.

```
left-click a district or via → grab it as route start

drag to another district or via:
  draw preview trace on active layer
  show credit cost (segments × cost_per_segment[layer])

release on a valid target:
  if credits >= cost AND target is not already connected on this route:
    create trace segment
    if route now has ≥ 2 nodes → spawn/update carrier
    deduct credits

right-click a trace segment:
  remove that segment
  refund credits × 0.5 (partial refund — infrastructure removal has overhead)
```

You can extend a route from either endpoint (or the middle — unlike the current prototype, mid-route insertions are allowed in the full design). The route's carrier adjusts its path.

### Via Placement Mode

Activated by pressing V (or selecting via type from build panel).

```
left-click on canvas:
  choose which layers to connect (popup with checkboxes, or cycle via type with V+V+V)
  place via at cursor
  deduct via cost
```

A via must have at least two layers checked. Traces can then be routed to/from the via on any of its connected layers.

---

## Congestion

Congestion is computed per-trace per-frame:

```
trace.load = sum of signal flows passing through this trace
           = count of routes using this trace × average_carrier_load

if trace.load > trace.capacity:
  trace.congested = true
  congestion_penalty = (trace.load - trace.capacity) / trace.capacity
  // reduces service score for all districts downstream of this trace
```

The player sees congested traces rendered in a warning state (red tint). They can fix it by:
- Adding a parallel trace (same layer, same nodes — doubles capacity)
- Rerouting through less-loaded paths
- Upgrading district tiers to reduce demand (higher tier = more efficient, lower relative load)

There is no time limit. The city just underperforms until it's fixed.

---

## Carrier Visualization

Carriers are visual indicators of signal flow — they do not carry discrete passengers.

- One carrier per route, moving back and forth
- Carrier speed proportional to route's average load (busier route = faster carrier)
- Carrier brightness/glow intensity = load percentage
- At low load: carrier moves slowly, appears dim
- At high load: carrier moves fast, appears bright, leaves a trail
- At congestion: carrier flashes warning color

This gives the player immediate visual feedback on which routes are busy.

---

## Scenario Win Conditions

Scenarios track objectives as a list of conditions checked each frame:

```rust
pub enum Objective {
    ReachPopulation(u32),               // total city population ≥ N
    ServiceScore { district: Entity, min_score: f32 },
    AllDistrictsConnected,              // all placed districts have service_score > 0
    CreditBalance(u32),                 // have ≥ N credits at any point
    TierReached { district: Entity, tier: u8 },
    TimeLimit(f32),                     // complete all other objectives within N seconds
}
```

When all objectives are met, the scenario ends with a summary screen.

---

## Constants (to tune)

```rust
// Spacing
MIN_DISTRICT_SPACING: 80.0
MIN_VIA_SPACING: 30.0
CARRIER_SPEED_BASE: 120.0   // world units/sec at 50% load
CARRIER_SPEED_MAX: 240.0    // at 100%+ load

// Credits
STARTING_CREDITS: 120
TRACE_COST_POWER: 2
TRACE_COST_DATA: 2
TRACE_COST_TRANSIT: 3
VIA_COST_TWO_LAYER: 8
VIA_COST_THREE_LAYER: 18
TRACE_REFUND_RATIO: 0.5

// District costs
COST_RESIDENTIAL: 20
COST_POWER_PLANT: 35
COST_DATA_CENTER: 45
COST_TRANSIT_HUB: 30
COST_COMMERCIAL: 50
COST_INDUSTRIAL: 60

// Growth
TIER_UP_THRESHOLD: [50.0, 80.0]   // score needed for tier 1→2, 2→3
TIER_DOWN_THRESHOLD: [20.0, 40.0] // score floor before decay
TIER_UP_DURATION: [30.0, 60.0]    // seconds to advance tier
```
