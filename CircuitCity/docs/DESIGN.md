# CircuitCities — Game Design Document

## Concept

CircuitCities is a city-builder where you design the infrastructure of a growing city as if you were laying out a circuit board. The city is your PCB. Districts are components. Power lines, data cables, and transit routes are copper traces on separate layers. Vias punch through the layers to let infrastructure cross-connect.

You are not surviving — you are building. There is no failure state from an overflowing queue. The city grows or stagnates based on how well you've engineered its infrastructure. A poorly connected district just stays underdeveloped. A well-served one thrives.

The primary inspiration is the PCB design metaphor taken seriously as a city-building system: **layers, traces, and vias** are the literal mechanics, not just the aesthetic.

---

## Design Pillars

**1. You Are the Engineer, Not the Firefighter**
The player makes deliberate decisions about where to build and how to route. The game does not throw emergencies at you. It rewards good design with a city that hums. It punishes poor design with a city that stagnates.

**2. Layers Are Depth, Not Complexity**
Each infrastructure type lives on its own layer, like PCB copper layers. Switching layers should feel natural — like flipping between the power and data planes on a real board. The layers are visually distinct but the interaction pattern is always the same: pick a layer, route traces.

**3. Vias Are the Interesting Decision**
Vias connect layers at a point. They are the most powerful tool and the most expensive one. Deciding where to place a via — committing a cross-layer junction — is the highest-skill decision in the game. Everything else is routing.

**4. The City Is a Living Schematic**
As you connect districts, they grow. Population numbers rise on residential blocks. Power consumption graphs fill up. The city is not a backdrop — it is feedback. If a district is starved, it shows. If the power layer is overloaded on the east side, you see it.

---

## Infrastructure Layers

The city has three infrastructure layers. The player switches between them to route connections. Traces on one layer never conflict with traces on a different layer — they occupy different planes.

| Layer | Name | Color | Carries | Traces look like |
|-------|------|-------|---------|-----------------|
| **A** | Power | Amber `#F5A623` | Electrical power | Thick, warm traces |
| **B** | Data | Cyan `#00C8E8` | Network / communications | Fine, bright traces |
| **C** | Transit | Green `#39D353` | People / goods | Wide, muted traces |

Switching layers: **Tab** cycles A→B→C→A. **1/2/3** jump directly. The active layer's traces render at full brightness; inactive layers are dimmed.

---

## Vias

A **via** is a point where two or more layers connect. In PCB design, a via is a plated hole drilled through the board. In CircuitCities it's a junction node that you place on the map.

**What vias do:**
- Allow signals (power, data, people) to transfer between layers at that point
- A via placed where a Power trace and a Data trace cross lets a node receive both power and data services simultaneously
- Vias can connect any two or all three layers

**Why vias matter:**
Most city nodes need more than one type of infrastructure. A Data Center needs power AND a data connection. A Transit Hub needs power AND transit. Without vias, each district can only be served by one layer's routes. With a well-placed via, a single district node becomes a cross-layer junction — serving multiple needs at once.

**Via cost:** Vias are the most expensive item to place. They require physical space (no overlapping vias) and budget. This makes via placement the primary resource-management decision.

**Via types:**

| Type | Layers Connected | Cost | Icon |
|------|-----------------|------|------|
| Power-Data via | A ↔ B | 8 credits | Small circle, amber+cyan ring |
| Power-Transit via | A ↔ C | 8 credits | Small circle, amber+green ring |
| Data-Transit via | B ↔ C | 8 credits | Small circle, cyan+green ring |
| Full via (through-hole) | A ↔ B ↔ C | 18 credits | Filled circle, all three rings |

---

## District Nodes

Districts are the buildings of the city. The player places them from a build panel. They are not randomly spawned. Placing a district is a deliberate act of city planning.

Each district has a **demand profile** — which infrastructure layers it needs to function, and at what level.

| District | Demand | Produces |
|----------|--------|---------|
| **Residential Block** | Transit (med), Power (low), Data (low) | Population, tax revenue |
| **Power Plant** | Data (low — control systems) | Power capacity |
| **Data Center** | Power (high), Data (med) | Data capacity, revenue |
| **Transit Hub** | Power (med), Transit (high) | Transit capacity, population access |
| **Commercial District** | All three (med) | High revenue |
| **Industrial Zone** | Power (high), Transit (med) | Revenue, unlocks upgrades |

A district's **service score** is a 0–100 value based on how well each of its demanded layers is connected. Higher service score = faster development = more revenue.

A disconnected district scores 0. It exists, it occupies space, but it does nothing. The player's job is to bring it to life.

---

## Resource: Credits

Credits are the city's budget. They fund all construction.

**Income:**
- Residential blocks generate a small trickle per population unit per second
- Commercial and Industrial districts generate larger income on a slower cycle
- You can toggle "pause building" to conserve credits while waiting for income

**Costs:**
- Trace segment (Power layer): 2 credits/segment
- Trace segment (Data layer): 2 credits/segment
- Trace segment (Transit layer): 3 credits/segment (transit infrastructure is more expensive)
- Via placement: 8–18 credits depending on type
- District placement: 20–60 credits depending on type

**Starting budget:** 120 credits. The starter city has 3 pre-placed districts and a small income stream. The first few minutes are about routing the initial connections.

---

## City Growth

Districts do not grow by magic. Growth is driven by service score:

- **Tier 1 → Tier 2:** Requires service score ≥ 50 sustained for 30 seconds
- **Tier 2 → Tier 3:** Requires service score ≥ 80 sustained for 60 seconds

Tier affects:
- Visual: the district node grows larger, gains detail
- Income: higher-tier districts earn more
- Demand: higher-tier districts demand more infrastructure (they require better service to stay at their tier)

A Tier 2 district that loses infrastructure drops back toward Tier 1 over time. The city is not a ratchet — it can degrade if you neglect it.

---

## Game Modes

**Sandbox**
Open canvas. No win condition. Build any city. Credits grow over time. The game tracks your city's total population as a loose score.

**Scenario**
Pre-designed maps with specific win conditions. Examples:
- "Connect the Industrial Quarter to the power grid and reach 500 population in the residential district within 10 minutes"
- "Achieve a service score of 75+ across all districts"
- "Build a fully self-sustaining city (income > expenses)"

Scenarios have a fixed starting map, a fixed credit budget, and explicit objectives shown in the HUD.

---

## Congestion (not Game Over)

There is no game-over state. However, nodes can become **congested**:

- If a trace is carrying more signals than its capacity, it enters congestion
- Congested traces reduce the service score for all districts they serve
- The trace turns a warning color (red tint on its layer color)
- The fix: add a parallel trace (more capacity), reroute through less-loaded paths, or upgrade via type

Congestion is information, not punishment. It tells you where the bottlenecks are.

---

## What This Is Not

- Not a survival game — the city doesn't end when a node overflows
- Not a real-time strategy game — there are no enemies, no units to command
- Not a simulation — the model is abstracted. Signals flow, scores accumulate, the city grows. We are not simulating traffic jams in detail.
- Not a puzzle game — there is no single correct solution. A city built entirely on transit with power only where needed can work just as well as a symmetric grid.
