//! CircuitCities — network-routing puzzle game built on Bevy's ECS.
//!
//! Architecture:
//!   * `components.rs` — per-entity data (Station, Train, …)
//!   * `resources.rs`  — global state (score, lines, timers, RNG)
//!   * `systems.rs`    — all behaviour, expressed as Bevy systems
//!
//! `main` just assembles the `App`: it registers the resources and schedules
//! the systems. Bevy runs the `Update` systems every frame, parallelising the
//! ones whose data accesses don't conflict.

mod components;
mod resources;
mod systems;

use bevy::prelude::*;
use resources::*;
use systems::*;

fn main() {
    App::new()
        .add_plugins(DefaultPlugins.set(WindowPlugin {
            primary_window: Some(Window {
                title: "Circuit Cities".into(),
                resolution: (1024_u32, 720_u32).into(),
                ..default()
            }),
            ..default()
        }))
        .insert_resource(ClearColor(Color::srgb(0.07, 0.07, 0.10)))
        .init_resource::<Game>()
        .init_resource::<Lines>()
        .init_resource::<ActiveLine>()
        .init_resource::<DragState>()
        .init_resource::<SpawnTimers>()
        .init_resource::<Rng>()
        .add_systems(Startup, setup)
        .add_systems(
            Update,
            (
                line_input,
                spawn_stations,
                spawn_passengers,
                move_trains,
                draw,
                update_ui,
            ),
        )
        .run();
}
