//! ECS **systems** — all game logic.
//!
//! Each `fn` here is a Bevy system: it declares the data it needs as
//! parameters (queries over components, plus resources), and Bevy schedules
//! them, running non-conflicting systems in parallel automatically.

use crate::components::*;
use crate::resources::*;
use bevy::prelude::*;

// ---- Tunable constants -----------------------------------------------------

pub const STATION_RADIUS: f32 = 16.0;
pub const TRAIN_SPEED: f32 = 150.0; // world units / second
pub const TRAIN_CAPACITY: usize = 6;
pub const QUEUE_LIMIT: usize = 8; // passengers waiting before game over
pub const BOUNDS_X: f32 = 470.0;
pub const BOUNDS_Y: f32 = 300.0;
pub const MIN_STATION_DIST: f32 = 95.0;

// ---- Startup ---------------------------------------------------------------

/// Spawns the camera, the HUD text, three empty lines, and a few starting
/// stations.
pub fn setup(mut commands: Commands, mut lines: ResMut<Lines>) {
    commands.spawn(Camera2d);

    commands.spawn((
        Text::new("Score: 0"),
        TextFont {
            font_size: 26.0,
            ..default()
        },
        TextColor(Color::WHITE),
        Node {
            position_type: PositionType::Absolute,
            top: Val::Px(12.0),
            left: Val::Px(14.0),
            ..default()
        },
        ScoreText,
    ));

    lines.lines = vec![
        MetroLine {
            stations: vec![],
            color: Color::srgb(0.90, 0.27, 0.27),
            has_train: false,
        },
        MetroLine {
            stations: vec![],
            color: Color::srgb(0.27, 0.55, 0.95),
            has_train: false,
        },
        MetroLine {
            stations: vec![],
            color: Color::srgb(0.32, 0.80, 0.42),
            has_train: false,
        },
    ];

    // One station of each shape, arranged in a triangle.
    for (i, shape) in Shape::all().into_iter().enumerate() {
        let angle = i as f32 * std::f32::consts::TAU / 3.0;
        let pos = Vec2::new(angle.cos() * 150.0, angle.sin() * 150.0);
        spawn_station(&mut commands, shape, pos);
    }
}

fn spawn_station(commands: &mut Commands, shape: Shape, pos: Vec2) {
    commands.spawn((
        Station {
            shape,
            queue: Vec::new(),
        },
        Transform::from_translation(pos.extend(0.0)),
    ));
}

// ---- Spawning over time ----------------------------------------------------

/// Periodically adds a new station at a random, non-overlapping position.
pub fn spawn_stations(
    time: Res<Time>,
    mut timers: ResMut<SpawnTimers>,
    mut rng: ResMut<Rng>,
    mut commands: Commands,
    game: Res<Game>,
    existing: Query<&Transform, With<Station>>,
) {
    if game.phase != Phase::Playing {
        return;
    }
    timers.station.tick(time.delta());
    if !timers.station.just_finished() {
        return;
    }

    for _ in 0..40 {
        let pos = Vec2::new(rng.range(-BOUNDS_X, BOUNDS_X), rng.range(-BOUNDS_Y, BOUNDS_Y));
        let too_close = existing
            .iter()
            .any(|t| t.translation.truncate().distance(pos) < MIN_STATION_DIST);
        if !too_close {
            let shape = rng.pick_shape();
            spawn_station(&mut commands, shape, pos);
            return;
        }
    }
}

/// Periodically spawns a passenger at a random station, wanting a random
/// (different) shape. If a station's queue overflows, the game ends.
pub fn spawn_passengers(
    time: Res<Time>,
    mut timers: ResMut<SpawnTimers>,
    mut rng: ResMut<Rng>,
    mut game: ResMut<Game>,
    mut stations: Query<&mut Station>,
) {
    if game.phase != Phase::Playing {
        return;
    }
    timers.passenger.tick(time.delta());
    if !timers.passenger.just_finished() {
        return;
    }

    let count = stations.iter().count();
    if count == 0 {
        return;
    }
    let pick = (rng.next_u64() as usize) % count;

    for (idx, mut st) in stations.iter_mut().enumerate() {
        if idx != pick {
            continue;
        }
        let mut dest = rng.pick_shape();
        let mut guard = 0;
        while dest == st.shape && guard < 6 {
            dest = rng.pick_shape();
            guard += 1;
        }
        st.queue.push(dest);
        if st.queue.len() > QUEUE_LIMIT {
            game.phase = Phase::GameOver;
        }
        return;
    }
}

// ---- Input: building lines -------------------------------------------------

/// Handles line selection (keys 1/2/3) and click-drag from one station to
/// another to connect them on the active line.
pub fn line_input(
    mouse: Res<ButtonInput<MouseButton>>,
    keys: Res<ButtonInput<KeyCode>>,
    windows: Query<&Window>,
    cam: Query<(&Camera, &GlobalTransform)>,
    stations: Query<(Entity, &Transform), With<Station>>,
    mut drag: ResMut<DragState>,
    mut active: ResMut<ActiveLine>,
    mut lines: ResMut<Lines>,
    mut commands: Commands,
    game: Res<Game>,
) {
    if game.phase != Phase::Playing {
        return;
    }

    if keys.just_pressed(KeyCode::Digit1) {
        active.0 = 0;
    }
    if keys.just_pressed(KeyCode::Digit2) {
        active.0 = 1;
    }
    if keys.just_pressed(KeyCode::Digit3) {
        active.0 = 2;
    }

    let cursor = match cursor_world(&windows, &cam) {
        Some(c) => c,
        None => return,
    };

    if mouse.just_pressed(MouseButton::Left) {
        drag.from = station_at(&stations, cursor);
    }

    if mouse.just_released(MouseButton::Left) {
        if let Some(from) = drag.from.take() {
            if let Some(to) = station_at(&stations, cursor) {
                if to != from {
                    connect(&mut lines, active.0, from, to, &mut commands);
                }
            }
        }
    }
}

/// Adds the edge `from -> to` to the active line if it extends one of the
/// line's endpoints, and spawns the line's train the first time it has a path.
fn connect(lines: &mut Lines, line_idx: usize, from: Entity, to: Entity, commands: &mut Commands) {
    let Some(line) = lines.lines.get_mut(line_idx) else {
        return;
    };

    if line.stations.is_empty() {
        line.stations.push(from);
        line.stations.push(to);
    } else {
        let first = *line.stations.first().unwrap();
        let last = *line.stations.last().unwrap();
        if last == from && !line.stations.contains(&to) {
            line.stations.push(to);
        } else if first == from && !line.stations.contains(&to) {
            line.stations.insert(0, to);
        } else if last == to && !line.stations.contains(&from) {
            line.stations.push(from);
        } else if first == to && !line.stations.contains(&from) {
            line.stations.insert(0, from);
        } else {
            return; // not a valid extension
        }
    }

    if line.stations.len() >= 2 && !line.has_train {
        line.has_train = true;
        commands.spawn((
            Train {
                line: line_idx,
                from: 0,
                to: 1,
                t: 0.0,
                dir: 1,
                passengers: Vec::new(),
            },
            Transform::from_translation(Vec3::ZERO),
        ));
    }
}

// ---- Train movement + passenger logic --------------------------------------

/// Moves each train along its line, and on arrival at a station drops off
/// matching passengers and picks up deliverable ones.
pub fn move_trains(
    time: Res<Time>,
    lines: Res<Lines>,
    mut game: ResMut<Game>,
    mut trains: Query<(&mut Train, &mut Transform), Without<Station>>,
    mut stations: Query<(&Transform, &mut Station), Without<Train>>,
) {
    if game.phase != Phase::Playing {
        return;
    }
    let dt = time.delta_secs();

    for (mut train, mut tf) in trains.iter_mut() {
        let Some(line) = lines.lines.get(train.line) else {
            continue;
        };
        let n = line.stations.len();
        if n < 2 {
            continue;
        }

        // Keep indices valid even if the line was edited.
        if train.from >= n {
            train.from = 0;
        }
        if train.to >= n {
            train.to = (train.from + 1) % n;
        }

        let from_e = line.stations[train.from];
        let to_e = line.stations[train.to];
        let from_pos = stations
            .get(from_e)
            .map(|(t, _)| t.translation.truncate())
            .unwrap_or(Vec2::ZERO);
        let to_pos = stations
            .get(to_e)
            .map(|(t, _)| t.translation.truncate())
            .unwrap_or(Vec2::ZERO);

        let seg_len = from_pos.distance(to_pos).max(1.0);
        train.t += TRAIN_SPEED * dt / seg_len;

        if train.t >= 1.0 {
            train.t = 0.0;

            // Which shapes are reachable on this line (for pickup decisions)?
            let mut line_shapes: Vec<Shape> = Vec::new();
            for &e in line.stations.iter() {
                if let Ok((_, st)) = stations.get(e) {
                    if !line_shapes.contains(&st.shape) {
                        line_shapes.push(st.shape);
                    }
                }
            }

            if let Ok((_, mut st)) = stations.get_mut(to_e) {
                let here = st.shape;

                // Drop off everyone whose destination is this shape.
                let before = train.passengers.len();
                train.passengers.retain(|&dest| dest != here);
                game.score += (before - train.passengers.len()) as u32;

                // Pick up waiting passengers we can actually deliver.
                let mut i = 0;
                while i < st.queue.len() && train.passengers.len() < TRAIN_CAPACITY {
                    let dest = st.queue[i];
                    if dest != here && line_shapes.contains(&dest) {
                        train.passengers.push(dest);
                        st.queue.remove(i);
                    } else {
                        i += 1;
                    }
                }
            }

            // Advance to the next segment, reversing at the ends.
            train.from = train.to;
            if train.dir == 1 && train.to == n - 1 {
                train.dir = -1;
            } else if train.dir == -1 && train.to == 0 {
                train.dir = 1;
            }
            let next = train.from as i32 + train.dir;
            train.to = next.clamp(0, n as i32 - 1) as usize;
        }

        let pos = from_pos.lerp(to_pos, train.t.clamp(0.0, 1.0));
        tf.translation = pos.extend(1.0);
    }
}

// ---- Rendering (immediate-mode gizmos) -------------------------------------

/// Draws lines, the drag preview, stations + waiting passengers, and trains.
pub fn draw(
    mut gizmos: Gizmos,
    lines: Res<Lines>,
    active: Res<ActiveLine>,
    drag: Res<DragState>,
    windows: Query<&Window>,
    cam: Query<(&Camera, &GlobalTransform)>,
    stations: Query<(Entity, &Transform, &Station)>,
    trains: Query<(&Transform, &Train)>,
) {
    // Metro lines.
    for line in lines.lines.iter() {
        if line.stations.len() < 2 {
            continue;
        }
        let mut pts: Vec<Vec2> = Vec::new();
        for &e in line.stations.iter() {
            if let Ok((_, t, _)) = stations.get(e) {
                pts.push(t.translation.truncate());
            }
        }
        if pts.len() >= 2 {
            gizmos.linestrip_2d(pts, line.color);
        }
    }

    // Drag preview line from the grabbed station to the cursor.
    if let Some(from) = drag.from {
        if let Ok((_, t, _)) = stations.get(from) {
            if let Some(cursor) = cursor_world(&windows, &cam) {
                let col = lines
                    .lines
                    .get(active.0)
                    .map(|l| l.color)
                    .unwrap_or(Color::WHITE);
                gizmos.line_2d(t.translation.truncate(), cursor, col);
            }
        }
    }

    // Stations and their waiting passengers.
    for (_, t, st) in stations.iter() {
        let p = t.translation.truncate();
        draw_shape(&mut gizmos, st.shape, p, STATION_RADIUS, Color::WHITE);
        for (i, &dest) in st.queue.iter().enumerate() {
            let off = Vec2::new(-14.0 + (i as f32) * 7.0, STATION_RADIUS + 12.0);
            draw_shape(&mut gizmos, dest, p + off, 3.0, Color::srgb(0.9, 0.85, 0.25));
        }
    }

    // Trains and their onboard passengers.
    for (t, train) in trains.iter() {
        let p = t.translation.truncate();
        let col = lines
            .lines
            .get(train.line)
            .map(|l| l.color)
            .unwrap_or(Color::WHITE);
        gizmos.rect_2d(p, Vec2::new(22.0, 13.0), col);
        for (i, &dest) in train.passengers.iter().enumerate() {
            let off = Vec2::new(-8.0 + (i as f32) * 3.4, 0.0);
            draw_shape(&mut gizmos, dest, p + off, 2.0, Color::WHITE);
        }
    }
}

fn draw_shape(gizmos: &mut Gizmos, shape: Shape, pos: Vec2, r: f32, color: Color) {
    match shape {
        Shape::Circle => {
            gizmos.circle_2d(pos, r, color);
        }
        Shape::Square => {
            gizmos.rect_2d(pos, Vec2::splat(r * 1.8), color);
        }
        Shape::Triangle => {
            let a = pos + Vec2::new(0.0, r);
            let b = pos + Vec2::new(-r * 0.9, -r * 0.7);
            let c = pos + Vec2::new(r * 0.9, -r * 0.7);
            gizmos.linestrip_2d([a, b, c, a], color);
        }
    }
}

// ---- HUD -------------------------------------------------------------------

/// Updates the score / status text each frame.
pub fn update_ui(
    game: Res<Game>,
    active: Res<ActiveLine>,
    mut q: Query<&mut Text, With<ScoreText>>,
) {
    if let Ok(mut text) = q.single_mut() {
        if game.phase == Phase::GameOver {
            text.0 = format!("GAME OVER  —  final score: {}", game.score);
        } else {
            text.0 = format!(
                "Score: {}     Editing line {}  (press 1 / 2 / 3)",
                game.score,
                active.0 + 1
            );
        }
    }
}

// ---- Shared helpers --------------------------------------------------------

/// Converts the cursor position into world-space coordinates, or `None` if the
/// cursor is outside the window.
fn cursor_world(
    windows: &Query<&Window>,
    cam: &Query<(&Camera, &GlobalTransform)>,
) -> Option<Vec2> {
    let window = windows.single().ok()?;
    let cursor = window.cursor_position()?;
    let (camera, cam_t) = cam.single().ok()?;
    camera.viewport_to_world_2d(cam_t, cursor).ok()
}

/// Returns the station whose centre is within grabbing distance of `p`.
fn station_at(
    stations: &Query<(Entity, &Transform), With<Station>>,
    p: Vec2,
) -> Option<Entity> {
    for (e, t) in stations.iter() {
        if t.translation.truncate().distance(p) <= STATION_RADIUS + 8.0 {
            return Some(e);
        }
    }
    None
}
