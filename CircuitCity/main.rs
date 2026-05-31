//! CircuitCities — PCB-inspired city builder built on Bevy ECS.
//!
//! Architecture:
//!   * `components.rs` — per-entity data (District, Trace, Via, …)
//!   * `resources.rs`  — global state (ActiveLayer, Credits, BuildState, Rng)
//!   * `systems.rs`    — all behaviour expressed as Bevy systems

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
        .insert_resource(ClearColor(Color::srgb(0.05, 0.06, 0.08)))
        .init_resource::<ActiveLayer>()
        .init_resource::<Credits>()
        .init_resource::<BuildState>()
        .init_resource::<Rng>()
        .add_systems(Startup, setup)
        .add_systems(
            Update,
            (
                layer_switch,
                build_input,
                service_score,
                city_growth,
                income,
                draw,
                update_ui,
            ),
        )
        .run();
}
