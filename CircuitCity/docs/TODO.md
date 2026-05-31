# CircuitCities — TODO

## Phase 0: Foundation Rewrite
- [x] Remove survival loop (spawn timers, game-over, passenger queue, move_trains)
- [x] Add Layer enum and active_layer resource
- [x] Add District component (replaces Station)
- [x] Add Trace component (replaces implicit line segments)
- [x] Add Via component
- [x] Add BuildMode resource and build_input system
- [x] Add layer_switch system (Tab/1/2/3)
- [x] Stub out service_score, city_growth, income systems

## Phase 1: Layers and Vias Working
- [ ] Render traces per-layer with amber/cyan/green, dim inactive layers to 25%
- [ ] Draw substrate dot-grid background
- [ ] Layer panel indicator (left edge of screen)
- [ ] Via placement (V key + click, type picker, concentric ring rendering)
- [ ] Trace routing (drag preview, credit cost label, pad endpoints, right-click remove)
- [ ] Route + carrier (auto-spawn on 2+ nodes, back-and-forth movement, layer color)

## Phase 2: Service Score and Growth
- [ ] Flood-fill service score with via layer-crossing
- [ ] City growth (tier timer, advance/decay, tier-up animation)
- [ ] Income system (credits/sec per district based on tier × service score)
- [ ] Congestion (load per trace, red tint, service score penalty)

## Phase 3: Districts and Build Panel
- [ ] Build panel HUD (R/B/D/T/H/I shortcuts, placement preview, spacing check)
- [ ] All 6 district types with demand profiles and unique shapes

## Phase 4: Scenarios and Sandbox
- [ ] Sandbox mode (open canvas, no objectives, population as metric)
- [ ] Scenario system (Objective enum, starting maps, objectives HUD panel)
- [ ] Build 3 starter scenarios (tutorial, Northern Quarter, High Density)

## Phase 5: Polish
- [ ] Carrier trail (ghost frames for load visualization)
- [ ] Sound (placement clicks, tier-up chime, congestion warning)
- [ ] Scenario complete screen with summary stats
- [ ] Persist high score / best city to disk
