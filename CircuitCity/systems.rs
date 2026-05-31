//! ECS **systems** — all game logic for CircuitCities.

use crate::components::*;
use crate::resources::*;
use bevy::prelude::*;

// ---- Constants -----------------------------------------------------------

pub const DISTRICT_RADIUS: f32 = 18.0;
pub const VIA_RADIUS: f32 = 8.0;
pub const MIN_DISTRICT_SPACING: f32 = 80.0;
pub const GRAB_RADIUS: f32 = 26.0; // click tolerance around a district
pub const VIA_GRAB_RADIUS: f32 = 14.0;

pub const TRACE_COST_POWER: u32 = 2;   // also used for Data layer
pub const TRACE_COST_TRANSIT: u32 = 3;

// ---- Startup -------------------------------------------------------------

pub fn setup(mut commands: Commands) {
    commands.spawn(Camera2d);

    commands.spawn((
        Text::new(""),
        TextFont { font_size: 20.0, ..default() },
        TextColor(Color::WHITE),
        Node {
            position_type: PositionType::Absolute,
            top: Val::Px(10.0),
            left: Val::Px(12.0),
            ..default()
        },
        ScoreText,
    ));

    // Three starting districts in a triangle so the player can immediately
    // start routing traces between them.
    for (i, kind) in [
        DistrictKind::PowerPlant,
        DistrictKind::Residential,
        DistrictKind::DataCenter,
    ]
    .into_iter()
    .enumerate()
    {
        let angle = i as f32 * std::f32::consts::TAU / 3.0 - std::f32::consts::FRAC_PI_2;
        let pos = Vec2::new(angle.cos() * 210.0, angle.sin() * 210.0);
        commands.spawn((District::new(kind), Transform::from_translation(pos.extend(0.0))));
    }
}

// ---- Layer switch --------------------------------------------------------

pub fn layer_switch(keys: Res<ButtonInput<KeyCode>>, mut active: ResMut<ActiveLayer>) {
    if keys.just_pressed(KeyCode::Tab) {
        active.0 = active.0.cycle();
    }
    if keys.just_pressed(KeyCode::Digit1) {
        active.0 = Layer::Power;
    }
    if keys.just_pressed(KeyCode::Digit2) {
        active.0 = Layer::Data;
    }
    if keys.just_pressed(KeyCode::Digit3) {
        active.0 = Layer::Transit;
    }
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
    transforms: Query<&Transform>,
    districts: Query<Entity, With<District>>,
    vias: Query<Entity, With<Via>>,
    mut commands: Commands,
) {
    // V key: switch to via placement mode (toggles back to routing on second press).
    if keys.just_pressed(KeyCode::KeyV) {
        build.mode = match build.mode {
            BuildMode::PlacingVia => BuildMode::Routing,
            _ => BuildMode::PlacingVia,
        };
        build.drag_from = None;
        return;
    }

    // Escape cancels any placement mode back to routing.
    if keys.just_pressed(KeyCode::Escape) {
        build.mode = BuildMode::Routing;
        build.drag_from = None;
        return;
    }

    let Some(cursor) = cursor_world(&windows, &cam) else {
        return;
    };

    match build.mode {
        BuildMode::Routing => {
            if mouse.just_pressed(MouseButton::Left) {
                build.drag_from = endpoint_at(&transforms, &districts, &vias, cursor);
            }

            if mouse.just_released(MouseButton::Left) {
                if let Some(from) = build.drag_from.take() {
                    if let Some(to) = endpoint_at(&transforms, &districts, &vias, cursor) {
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
                if credits.0 >= cost as f32 && !too_close_to_any(&transforms, &districts, &vias, cursor) {
                    credits.0 -= cost as f32;
                    commands.spawn((
                        District::new(kind),
                        Transform::from_translation(cursor.extend(0.0)),
                    ));
                }
            }
        }

        BuildMode::PlacingVia => {
            if mouse.just_pressed(MouseButton::Left) {
                // Phase 1 adds a type picker; for now always place a full via.
                commands.spawn((
                    Via { connects: LayerSet::all() },
                    Transform::from_translation(cursor.extend(0.0)),
                ));
                build.mode = BuildMode::Routing;
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

fn too_close_to_any(
    transforms: &Query<&Transform>,
    districts: &Query<Entity, With<District>>,
    vias: &Query<Entity, With<Via>>,
    cursor: Vec2,
) -> bool {
    for e in districts.iter() {
        if let Ok(t) = transforms.get(e) {
            if t.translation.truncate().distance(cursor) < MIN_DISTRICT_SPACING {
                return true;
            }
        }
    }
    for e in vias.iter() {
        if let Ok(t) = transforms.get(e) {
            if t.translation.truncate().distance(cursor) < MIN_DISTRICT_SPACING * 0.4 {
                return true;
            }
        }
    }
    false
}

// ---- Phase 2 stubs -------------------------------------------------------

/// Flood-fill reachability per layer and compute each district's service score.
pub fn service_score() {
    // Phase 2: flood-fill from each District along same-layer Traces,
    // crossing Vias where the layer is in Via::connects. Weighted average
    // of per-layer coverage ratios gives District::service_score.
}

/// Advance or decay district tiers based on sustained service score.
pub fn city_growth() {
    // Phase 2: increment District::tier_timer while service_score meets the
    // threshold, promote tier after TIER_UP_DURATION seconds, decay toward
    // lower tier when score drops below TIER_DOWN_THRESHOLD.
}

/// Accumulate Credits from districts proportional to tier × service_score.
pub fn income() {
    // Phase 2: each second add district income_rate[tier] × (service_score/100)
    // to the Credits resource.
}

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
) {
    // Traces — dim inactive layers to ~25% brightness.
    for trace in traces.iter() {
        let Ok(from_t) = transforms.get(trace.from) else { continue };
        let Ok(to_t)   = transforms.get(trace.to)   else { continue };
        let color = if trace.layer == active.0 {
            trace.layer.color()
        } else {
            trace.layer.dim_color()
        };
        gizmos.line_2d(from_t.translation.truncate(), to_t.translation.truncate(), color);
    }

    // Drag-preview trace from grabbed endpoint to cursor.
    if let Some(from_e) = build.drag_from {
        if let Ok(from_t) = transforms.get(from_e) {
            if let Some(cursor) = cursor_world(&windows, &cam) {
                gizmos.line_2d(from_t.translation.truncate(), cursor, active.0.color());
            }
        }
    }

    // Vias — concentric rings, one per connected layer.
    for (e, via) in vias.iter() {
        let Ok(t) = transforms.get(e) else { continue };
        let pos = t.translation.truncate();
        let mut r = VIA_RADIUS;
        for layer in [Layer::Power, Layer::Data, Layer::Transit] {
            if via.connects.contains(layer) {
                let color = if layer == active.0 {
                    layer.color()
                } else {
                    layer.dim_color()
                };
                gizmos.circle_2d(pos, r, color);
                r += 4.0;
            }
        }
    }

    // Districts — circle outline sized by tier, colored by kind.
    for (e, district) in districts.iter() {
        let Ok(t) = transforms.get(e) else { continue };
        let pos = t.translation.truncate();
        let color = district.kind.color();
        let r = DISTRICT_RADIUS + (district.tier as f32 - 1.0) * 5.0;
        gizmos.circle_2d(pos, r, color);

        // Tier pips below the circle.
        for i in 0..district.tier {
            let dot = pos + Vec2::new(-4.0 + i as f32 * 4.5, -r - 9.0);
            gizmos.circle_2d(dot, 2.0, color);
        }
    }

    // Via placement preview.
    if build.mode == BuildMode::PlacingVia {
        if let Some(cursor) = cursor_world(&windows, &cam) {
            gizmos.circle_2d(cursor, VIA_RADIUS, Color::WHITE);
        }
    }
}

// ---- HUD -----------------------------------------------------------------

pub fn update_ui(
    active: Res<ActiveLayer>,
    credits: Res<Credits>,
    build: Res<BuildState>,
    mut q: Query<&mut Text, With<ScoreText>>,
) {
    let Ok(mut text) = q.single_mut() else { return };
    let mode_hint = match build.mode {
        BuildMode::Routing             => "drag between nodes to trace  |  V = place via",
        BuildMode::PlacingDistrict(_)  => "click to place district  |  Esc = cancel",
        BuildMode::PlacingVia          => "click to place via  |  V / Esc = cancel",
    };
    text.0 = format!(
        "Credits: {:.0}   Layer: {}   (Tab / 1 2 3)   {}",
        credits.0,
        active.0.name(),
        mode_hint,
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

/// Returns the district or via entity under cursor `p`, preferring districts.
fn endpoint_at(
    transforms: &Query<&Transform>,
    districts: &Query<Entity, With<District>>,
    vias: &Query<Entity, With<Via>>,
    p: Vec2,
) -> Option<Entity> {
    for e in districts.iter() {
        if let Ok(t) = transforms.get(e) {
            if t.translation.truncate().distance(p) <= GRAB_RADIUS {
                return Some(e);
            }
        }
    }
    for e in vias.iter() {
        if let Ok(t) = transforms.get(e) {
            if t.translation.truncate().distance(p) <= VIA_GRAB_RADIUS {
                return Some(e);
            }
        }
    }
    None
}
