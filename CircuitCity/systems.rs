//! ECS **systems** — all game logic for CircuitCities.

use crate::components::*;
use crate::resources::*;
use bevy::prelude::*;

// ---- Constants -----------------------------------------------------------

pub const GRID_SIZE: f32 = 40.0;
pub const DISTRICT_RADIUS: f32 = 18.0;
pub const VIA_RADIUS: f32 = 8.0;
pub const CIRCUIT_RADIUS: f32 = 14.0;   // PowerSource / Ground / Led visual radius
pub const MIN_NODE_SPACING: f32 = 70.0; // minimum gap between any two CircuitNodes
pub const GRAB_RADIUS: f32 = 26.0;      // click grab tolerance

pub const TRACE_COST_POWER: u32 = 2;    // also used for Data layer
pub const TRACE_COST_TRANSIT: u32 = 3;

pub const ELECTRON_SPEED: f32 = 140.0;        // world-units / second
pub const ELECTRON_SPAWN_INTERVAL: f32 = 1.2; // seconds between spawns per PowerSource
pub const PHOTON_SPEED: f32 = 28.0;
pub const PHOTON_LIFETIME: f32 = 7.0;
pub const PHOTON_COLLECT_RADIUS: f32 = 22.0;
pub const LED_LIT_DURATION: f32 = 0.35;

// ---- Startup -------------------------------------------------------------

pub fn setup(mut commands: Commands) {
    commands.spawn(Camera2d);

    commands.spawn((
        Text::new(""),
        TextFont { font_size: 19.0, ..default() },
        TextColor(Color::WHITE),
        Node {
            position_type: PositionType::Absolute,
            top: Val::Px(10.0),
            left: Val::Px(12.0),
            ..default()
        },
        ScoreText,
    ));

    // Starting city districts — grid-aligned positions (GRID_SIZE = 40).
    for (kind, pos) in [
        (DistrictKind::PowerPlant,  Vec2::new(  0.0,  240.0)),  // (0,  6)
        (DistrictKind::Residential, Vec2::new(-200.0, -120.0)), // (-5,-3)
        (DistrictKind::DataCenter,  Vec2::new( 200.0, -120.0)), // ( 5,-3)
    ] {
        commands.spawn((District::new(kind), CircuitNode, Transform::from_translation(pos.extend(0.0))));
    }

    // Starting circuit: PowerSource and Ground pre-placed so electrons flow
    // as soon as the player connects them with a Power-layer trace.
    // Drop an LED between them to see photons.
    commands.spawn((PowerSource::new(), CircuitNode, Transform::from_translation(Vec3::new(360.0,  240.0, 0.0))));
    commands.spawn((Ground,             CircuitNode, Transform::from_translation(Vec3::new(360.0, -240.0, 0.0))));
}

// ---- Layer switch --------------------------------------------------------

pub fn layer_switch(keys: Res<ButtonInput<KeyCode>>, mut active: ResMut<ActiveLayer>) {
    if keys.just_pressed(KeyCode::Tab)    { active.0 = active.0.cycle(); }
    if keys.just_pressed(KeyCode::Digit1) { active.0 = Layer::Power; }
    if keys.just_pressed(KeyCode::Digit2) { active.0 = Layer::Data; }
    if keys.just_pressed(KeyCode::Digit3) { active.0 = Layer::Transit; }
}

// ---- Build input ---------------------------------------------------------

pub fn build_input(
    mouse: Res<ButtonInput<MouseButton>>,
    keys: Res<ButtonInput<KeyCode>>,
    windows: Query<&Window>,
    cam: Query<(&Camera, &GlobalTransform)>,
    active: Res<ActiveLayer>,
    mut build: ResMut<BuildState>,
    mut credits: ResMut<Credits>,
    nodes: Query<(Entity, &Transform), With<CircuitNode>>,
    mut commands: Commands,
) {
    // Mode-toggle shortcuts (second press cancels back to Routing).
    let mode_keys: &[(KeyCode, BuildMode)] = &[
        (KeyCode::KeyV, BuildMode::PlacingVia),
        (KeyCode::KeyP, BuildMode::PlacingPowerSource),
        (KeyCode::KeyG, BuildMode::PlacingGround),
        (KeyCode::KeyL, BuildMode::PlacingLed),
    ];
    for &(key, target_mode) in mode_keys {
        if keys.just_pressed(key) {
            build.mode = if build.mode == target_mode { BuildMode::Routing } else { target_mode };
            build.drag_from = None;
            return;
        }
    }

    if keys.just_pressed(KeyCode::Escape) {
        build.mode = BuildMode::Routing;
        build.drag_from = None;
        return;
    }

    let Some(cursor) = cursor_world(&windows, &cam) else { return };
    // Routing uses raw cursor (grab existing nodes by proximity).
    // Placement uses the grid-snapped position.
    let snapped = snap_to_grid(cursor);

    match build.mode {
        BuildMode::Routing => {
            if mouse.just_pressed(MouseButton::Left) {
                build.drag_from = endpoint_at(&nodes, cursor);
            }
            if mouse.just_released(MouseButton::Left) {
                if let Some(from) = build.drag_from.take() {
                    if let Some(to) = endpoint_at(&nodes, cursor) {
                        if to != from {
                            let cost = trace_cost(active.0);
                            if credits.0 >= cost as f32 {
                                credits.0 -= cost as f32;
                                commands.spawn(Trace {
                                    layer: active.0,
                                    from,
                                    to,
                                    capacity: 10,
                                    load: 0,
                                    congested: false,
                                });
                            }
                        }
                    }
                }
            }
        }

        BuildMode::PlacingDistrict(kind) => {
            if mouse.just_pressed(MouseButton::Left) {
                let cost = kind.placement_cost();
                if credits.0 >= cost as f32 && !too_close(&nodes, snapped) {
                    credits.0 -= cost as f32;
                    commands.spawn((
                        District::new(kind),
                        CircuitNode,
                        Transform::from_translation(snapped.extend(0.0)),
                    ));
                }
            }
        }

        BuildMode::PlacingVia => {
            if mouse.just_pressed(MouseButton::Left) {
                if !too_close(&nodes, snapped) {
                    commands.spawn((
                        Via { connects: LayerSet::all() },
                        CircuitNode,
                        Transform::from_translation(snapped.extend(0.0)),
                    ));
                    build.mode = BuildMode::Routing;
                }
            }
        }

        BuildMode::PlacingPowerSource => {
            if mouse.just_pressed(MouseButton::Left) {
                if !too_close(&nodes, snapped) {
                    commands.spawn((
                        PowerSource::new(),
                        CircuitNode,
                        Transform::from_translation(snapped.extend(0.0)),
                    ));
                    build.mode = BuildMode::Routing;
                }
            }
        }

        BuildMode::PlacingGround => {
            if mouse.just_pressed(MouseButton::Left) {
                if !too_close(&nodes, snapped) {
                    commands.spawn((
                        Ground,
                        CircuitNode,
                        Transform::from_translation(snapped.extend(0.0)),
                    ));
                    build.mode = BuildMode::Routing;
                }
            }
        }

        BuildMode::PlacingLed => {
            if mouse.just_pressed(MouseButton::Left) {
                if !too_close(&nodes, snapped) {
                    commands.spawn((
                        Led::new(),
                        CircuitNode,
                        Transform::from_translation(snapped.extend(0.0)),
                    ));
                    build.mode = BuildMode::Routing;
                }
            }
        }
    }
}

fn trace_cost(layer: Layer) -> u32 {
    match layer {
        Layer::Power | Layer::Data => TRACE_COST_POWER,
        Layer::Transit             => TRACE_COST_TRANSIT,
    }
}

// ---- Electron simulation -------------------------------------------------

/// Spawn electrons from every PowerSource — only if a Power-layer path to Ground exists.
pub fn spawn_electrons(
    time: Res<Time>,
    mut commands: Commands,
    mut sources: Query<(Entity, &mut PowerSource)>,
    traces: Query<(Entity, &Trace)>,
    grounds: Query<Entity, With<Ground>>,
) {
    let dt = time.delta_secs();
    let trace_snap: Vec<(Entity, Trace)> = traces.iter().map(|(e, t)| (e, *t)).collect();

    for (src_entity, mut ps) in sources.iter_mut() {
        ps.timer -= dt;
        if ps.timer > 0.0 { continue; }
        ps.timer = ELECTRON_SPAWN_INTERVAL;

        // Only emit if there's a complete path to a Ground node.
        if !can_reach_ground(src_entity, &trace_snap, &grounds) { continue; }

        for &(trace_entity, trace) in &trace_snap {
            if trace.layer != Layer::Power { continue; }
            if trace.from != src_entity && trace.to != src_entity { continue; }
            commands.spawn(Electron {
                trace: trace_entity,
                t: 0.0,
                forward: trace.from == src_entity,
                prev_node: src_entity,
            });
        }
    }
}

/// Advance electrons along traces; route at junctions, spawn photons at LEDs, despawn at Ground.
pub fn move_electrons(
    time: Res<Time>,
    mut commands: Commands,
    mut electrons: Query<(Entity, &mut Electron)>,
    traces: Query<(Entity, &Trace)>,
    transforms: Query<&Transform>,
    grounds: Query<Entity, With<Ground>>,
    mut leds: Query<&mut Led>,
    mut rng: ResMut<Rng>,
) {
    let dt = time.delta_secs();

    // Snapshot trace data so we can pass it to the routing helper without lifetime issues.
    let trace_snap: Vec<(Entity, Trace)> = traces.iter().map(|(e, t)| (e, *t)).collect();

    for (e_entity, mut electron) in electrons.iter_mut() {
        // Locate the trace this electron is on.
        let Some(&(_, trace)) = trace_snap.iter().find(|(e, _)| *e == electron.trace) else {
            commands.entity(e_entity).despawn();
            continue;
        };

        // Advance position, normalised by segment length so speed is world-unit-consistent.
        let from_pos = transforms.get(trace.from).map(|t| t.translation.truncate()).unwrap_or_default();
        let to_pos   = transforms.get(trace.to  ).map(|t| t.translation.truncate()).unwrap_or_default();
        let seg_len  = from_pos.distance(to_pos).max(1.0);

        electron.t += ELECTRON_SPEED * dt / seg_len;

        if electron.t < 1.0 { continue; }
        electron.t = 0.0;

        let arrived_at = if electron.forward { trace.to } else { trace.from };

        // Ground: absorb and despawn.
        if grounds.get(arrived_at).is_ok() {
            commands.entity(e_entity).despawn();
            continue;
        }

        // LED: light up and emit a photon.
        if let Ok(mut led) = leds.get_mut(arrived_at) {
            led.lit_timer = LED_LIT_DURATION;
            if let Ok(node_t) = transforms.get(arrived_at) {
                let pos   = node_t.translation.truncate();
                let angle = rng.range(0.0, std::f32::consts::TAU);
                let vel   = Vec2::new(angle.cos(), angle.sin()) * PHOTON_SPEED;
                commands.spawn((
                    Photon { velocity: vel, lifetime: PHOTON_LIFETIME },
                    Transform::from_translation(pos.extend(2.0)),
                ));
            }
        }

        // Route to the next trace, avoiding going straight back.
        match next_trace(&trace_snap, arrived_at, electron.prev_node, trace.layer) {
            Some((next_entity, forward)) => {
                electron.prev_node = arrived_at;
                electron.trace     = next_entity;
                electron.forward   = forward;
            }
            None => { commands.entity(e_entity).despawn(); }
        }
    }
}

/// Tick down LED lit timers.
pub fn tick_leds(time: Res<Time>, mut leds: Query<&mut Led>) {
    let dt = time.delta_secs();
    for mut led in leds.iter_mut() {
        led.lit_timer = (led.lit_timer - dt).max(0.0);
    }
}

/// Move photons and despawn expired ones.
pub fn drift_photons(
    time: Res<Time>,
    mut commands: Commands,
    mut photons: Query<(Entity, &mut Photon, &mut Transform)>,
) {
    let dt = time.delta_secs();
    for (entity, mut photon, mut t) in photons.iter_mut() {
        photon.lifetime -= dt;
        if photon.lifetime <= 0.0 {
            commands.entity(entity).despawn();
        } else {
            t.translation += (photon.velocity * dt).extend(0.0);
        }
    }
}

/// Auto-collect photons when the cursor passes within PHOTON_COLLECT_RADIUS.
pub fn collect_photons(
    windows: Query<&Window>,
    cam: Query<(&Camera, &GlobalTransform)>,
    photons: Query<(Entity, &Transform), With<Photon>>,
    mut count: ResMut<PhotonCount>,
    mut commands: Commands,
) {
    let Some(cursor) = cursor_world(&windows, &cam) else { return };
    for (entity, t) in photons.iter() {
        if t.translation.truncate().distance(cursor) <= PHOTON_COLLECT_RADIUS {
            count.0 += 1;
            commands.entity(entity).despawn();
        }
    }
}

// ---- Phase 2 stubs -------------------------------------------------------

pub fn service_score() {}
pub fn city_growth()   {}
pub fn income()        {}

// ---- Rendering -----------------------------------------------------------

pub fn draw(
    mut gizmos: Gizmos,
    active: Res<ActiveLayer>,
    build: Res<BuildState>,
    windows: Query<&Window>,
    cam: Query<(&Camera, &GlobalTransform)>,
    transforms: Query<&Transform>,
    districts: Query<(Entity, &District)>,
    vias: Query<(Entity, &Via)>,
    traces: Query<&Trace>,
    electrons: Query<&Electron>,
    photons: Query<(&Photon, &Transform)>,
    power_sources: Query<Entity, With<PowerSource>>,
    grounds: Query<Entity, With<Ground>>,
    leds: Query<(Entity, &Led)>,
) {
    // ── Substrate dot grid ───────────────────────────────────────────────
    let dot_color = Color::srgb(0.13, 0.14, 0.19);
    let (hw, hh) = (520.0_f32, 368.0_f32);
    let mut gx = ((-hw) / GRID_SIZE).ceil() * GRID_SIZE;
    while gx <= hw {
        let mut gy = ((-hh) / GRID_SIZE).ceil() * GRID_SIZE;
        while gy <= hh {
            gizmos.circle_2d(Vec2::new(gx, gy), 1.5, dot_color);
            gy += GRID_SIZE;
        }
        gx += GRID_SIZE;
    }

    // ── Traces (drawn first so nodes sit on top) ──────────────────────────
    for trace in traces.iter() {
        let Ok(ft) = transforms.get(trace.from) else { continue };
        let Ok(tt) = transforms.get(trace.to)   else { continue };
        let color = if trace.layer == active.0 { trace.layer.color() } else { trace.layer.dim_color() };
        gizmos.line_2d(ft.translation.truncate(), tt.translation.truncate(), color);
    }

    // ── Drag-preview ─────────────────────────────────────────────────────
    if let Some(from_e) = build.drag_from {
        if let Ok(ft) = transforms.get(from_e) {
            if let Some(cursor) = cursor_world(&windows, &cam) {
                gizmos.line_2d(ft.translation.truncate(), cursor, active.0.color());
            }
        }
    }

    // ── Vias ─────────────────────────────────────────────────────────────
    for (e, via) in vias.iter() {
        let Ok(t) = transforms.get(e) else { continue };
        let pos = t.translation.truncate();
        let mut r = VIA_RADIUS;
        for layer in [Layer::Power, Layer::Data, Layer::Transit] {
            if via.connects.contains(layer) {
                let c = if layer == active.0 { layer.color() } else { layer.dim_color() };
                gizmos.circle_2d(pos, r, c);
                r += 4.0;
            }
        }
    }

    // ── Districts ────────────────────────────────────────────────────────
    for (e, district) in districts.iter() {
        let Ok(t) = transforms.get(e) else { continue };
        let pos = t.translation.truncate();
        let color = district.kind.color();
        let r = DISTRICT_RADIUS + (district.tier as f32 - 1.0) * 5.0;
        gizmos.circle_2d(pos, r, color);
        for i in 0..district.tier {
            gizmos.circle_2d(pos + Vec2::new(-4.0 + i as f32 * 4.5, -r - 9.0), 2.0, color);
        }
    }

    // ── PowerSources — amber circle + crosshair ───────────────────────────
    let amber = Layer::Power.color();
    for e in power_sources.iter() {
        let Ok(t) = transforms.get(e) else { continue };
        let pos = t.translation.truncate();
        gizmos.circle_2d(pos, CIRCUIT_RADIUS, amber);
        let arm = CIRCUIT_RADIUS * 0.55;
        gizmos.line_2d(pos + Vec2::new(-arm, 0.0), pos + Vec2::new(arm, 0.0), amber);
        gizmos.line_2d(pos + Vec2::new(0.0, -arm), pos + Vec2::new(0.0, arm), amber);
    }

    // ── Grounds — circle + three shrinking horizontal lines below ─────────
    let gray = Color::srgb(0.55, 0.55, 0.55);
    for e in grounds.iter() {
        let Ok(t) = transforms.get(e) else { continue };
        let pos = t.translation.truncate();
        gizmos.circle_2d(pos, CIRCUIT_RADIUS, gray);
        // Stem
        let stem_bot = pos + Vec2::new(0.0, -CIRCUIT_RADIUS);
        let bar_top  = stem_bot + Vec2::new(0.0, -5.0);
        gizmos.line_2d(stem_bot, bar_top, gray);
        // Three bars
        for (i, half_w) in [(0, 11.0_f32), (1, 7.0), (2, 3.0)] {
            let y = bar_top.y - i as f32 * 5.0;
            gizmos.line_2d(Vec2::new(pos.x - half_w, y), Vec2::new(pos.x + half_w, y), gray);
        }
    }

    // ── LEDs — triangle, yellow when lit ─────────────────────────────────
    for (e, led) in leds.iter() {
        let Ok(t) = transforms.get(e) else { continue };
        let pos = t.translation.truncate();
        let lit  = led.lit_timer > 0.0;
        let base = if lit { Color::srgb(1.0, 0.97, 0.25) } else { Color::srgb(0.55, 0.55, 0.20) };
        let r = CIRCUIT_RADIUS;
        // LED symbol: right-pointing triangle
        let tip = pos + Vec2::new(r, 0.0);
        let bl  = pos + Vec2::new(-r * 0.65, -r * 0.75);
        let tl  = pos + Vec2::new(-r * 0.65,  r * 0.75);
        gizmos.linestrip_2d([tip, bl, tl, tip], base);
        // Vertical bar (cathode)
        gizmos.line_2d(pos + Vec2::new(r, -r * 0.75), pos + Vec2::new(r, r * 0.75), base);
        // Light rays when lit
        if lit {
            for angle_deg in [30.0_f32, 60.0] {
                let angle = angle_deg.to_radians();
                let dir = Vec2::new(angle.cos(), angle.sin());
                gizmos.line_2d(tip + dir * 4.0, tip + dir * 12.0, base);
                let dir2 = Vec2::new(angle.cos(), -angle.sin());
                gizmos.line_2d(tip + dir2 * 4.0, tip + dir2 * 12.0, base);
            }
        }
    }

    // ── Electrons — small bright dot interpolated along its trace ─────────
    for electron in electrons.iter() {
        let Ok(trace) = traces.get(electron.trace) else { continue };
        let Ok(ft) = transforms.get(trace.from) else { continue };
        let Ok(tt) = transforms.get(trace.to)   else { continue };
        let fp = ft.translation.truncate();
        let tp = tt.translation.truncate();
        let pos = if electron.forward { fp.lerp(tp, electron.t) } else { tp.lerp(fp, electron.t) };
        gizmos.circle_2d(pos, 3.5, Color::srgb(0.85, 0.92, 1.0));
    }

    // ── Photons — fading yellow ring pair ────────────────────────────────
    for (photon, pt) in photons.iter() {
        let alpha = (photon.lifetime / PHOTON_LIFETIME).clamp(0.0, 1.0);
        let c = Color::srgb(1.0 * alpha, 0.93 * alpha, 0.22 * alpha);
        let pos = pt.translation.truncate();
        gizmos.circle_2d(pos, 5.5, c);
        gizmos.circle_2d(pos, 3.0, c);
    }

    // ── Placement previews (snapped to grid) ────────────────────────────
    if let Some(raw) = cursor_world(&windows, &cam) {
        let c = snap_to_grid(raw);
        match build.mode {
            BuildMode::PlacingVia         => { gizmos.circle_2d(c, VIA_RADIUS,     Color::srgba(1.0,  1.0,  1.0,  0.6 )); }
            BuildMode::PlacingPowerSource => { gizmos.circle_2d(c, CIRCUIT_RADIUS, Color::srgba(0.96, 0.65, 0.14, 0.55)); }
            BuildMode::PlacingGround      => { gizmos.circle_2d(c, CIRCUIT_RADIUS, Color::srgba(0.55, 0.55, 0.55, 0.55)); }
            BuildMode::PlacingLed         => { gizmos.circle_2d(c, CIRCUIT_RADIUS, Color::srgba(1.0,  0.97, 0.25, 0.55)); }
            _ => {}
        }
    }
}

// ---- HUD -----------------------------------------------------------------

pub fn update_ui(
    active: Res<ActiveLayer>,
    credits: Res<Credits>,
    photons: Res<PhotonCount>,
    build: Res<BuildState>,
    mut q: Query<&mut Text, With<ScoreText>>,
) {
    let Ok(mut text) = q.single_mut() else { return };
    let mode_hint = match build.mode {
        BuildMode::Routing            => "drag nodes to trace",
        BuildMode::PlacingDistrict(_) => "click to place district | Esc=cancel",
        BuildMode::PlacingVia         => "click to place via      | V/Esc=cancel",
        BuildMode::PlacingPowerSource => "click to place power    | P/Esc=cancel",
        BuildMode::PlacingGround      => "click to place ground   | G/Esc=cancel",
        BuildMode::PlacingLed         => "click to place LED      | L/Esc=cancel",
    };
    text.0 = format!(
        "Credits: {:.0}   Layer: {}  (Tab/1-3)   Photons: {}   P/G/L/V=place  {}",
        credits.0, active.0.name(), photons.0, mode_hint,
    );
}

// ---- Helpers -------------------------------------------------------------

fn cursor_world(
    windows: &Query<&Window>,
    cam: &Query<(&Camera, &GlobalTransform)>,
) -> Option<Vec2> {
    let window = windows.single().ok()?;
    let cursor = window.cursor_position()?;
    let (camera, cam_t) = cam.single().ok()?;
    camera.viewport_to_world_2d(cam_t, cursor).ok()
}

/// Snap `pos` to the nearest GRID_SIZE-aligned point.
fn snap_to_grid(pos: Vec2) -> Vec2 {
    Vec2::new(
        (pos.x / GRID_SIZE).round() * GRID_SIZE,
        (pos.y / GRID_SIZE).round() * GRID_SIZE,
    )
}

/// BFS from `source` along Power-layer traces; returns true if any Ground is reachable.
fn can_reach_ground(
    source: Entity,
    traces: &[(Entity, Trace)],
    grounds: &Query<Entity, With<Ground>>,
) -> bool {
    let mut visited = vec![source];
    let mut queue = vec![source];
    while let Some(node) = queue.pop() {
        if grounds.get(node).is_ok() { return true; }
        for &(_, trace) in traces {
            if trace.layer != Layer::Power { continue; }
            let next = if trace.from == node { trace.to }
                       else if trace.to == node { trace.from }
                       else { continue };
            if !visited.contains(&next) {
                visited.push(next);
                queue.push(next);
            }
        }
    }
    false
}

/// Returns the CircuitNode entity closest to `p` within GRAB_RADIUS.
fn endpoint_at(nodes: &Query<(Entity, &Transform), With<CircuitNode>>, p: Vec2) -> Option<Entity> {
    nodes.iter()
        .filter(|(_, t)| t.translation.truncate().distance(p) <= GRAB_RADIUS)
        .min_by(|(_, a), (_, b)| {
            a.translation.truncate().distance(p)
                .partial_cmp(&b.translation.truncate().distance(p))
                .unwrap()
        })
        .map(|(e, _)| e)
}

/// True if `p` is within MIN_NODE_SPACING of any existing CircuitNode.
fn too_close(nodes: &Query<(Entity, &Transform), With<CircuitNode>>, p: Vec2) -> bool {
    nodes.iter().any(|(_, t)| t.translation.truncate().distance(p) < MIN_NODE_SPACING)
}

/// Find the next Power-layer trace to route onto from `current_node`,
/// preferring any direction that doesn't immediately reverse back to `prev_node`.
fn next_trace(
    traces: &[(Entity, Trace)],
    current_node: Entity,
    prev_node: Entity,
    layer: Layer,
) -> Option<(Entity, bool)> {
    // First: forward progress — avoid prev_node.
    for &(entity, trace) in traces {
        if trace.layer != layer { continue; }
        if trace.from == current_node && trace.to != prev_node { return Some((entity, true)); }
        if trace.to   == current_node && trace.from != prev_node { return Some((entity, false)); }
    }
    // Fallback: allow reversal if it's the only path (dead-end one-way trace).
    for &(entity, trace) in traces {
        if trace.layer != layer { continue; }
        if trace.from == current_node { return Some((entity, true)); }
        if trace.to   == current_node { return Some((entity, false)); }
    }
    None
}
