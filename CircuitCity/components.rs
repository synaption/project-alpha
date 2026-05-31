//! ECS **components** — the per-entity data of the game.
//!
//! In Bevy's ECS, components are plain data attached to entities. Systems
//! (see `systems.rs`) query for entities that have particular combinations of
//! components and operate on them.

use bevy::prelude::*;

/// The kind of a station. A passenger's destination is expressed as the shape
/// of station they want to reach.
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum Shape {
    Circle,
    Triangle,
    Square,
}

impl Shape {
    pub fn all() -> [Shape; 3] {
        [Shape::Circle, Shape::Triangle, Shape::Square]
    }
}

/// A station on the map. Its [`Transform`] (added alongside it) holds its
/// position. `queue` is the list of passengers waiting here, each identified by
/// the shape they want to travel to.
#[derive(Component)]
pub struct Station {
    pub shape: Shape,
    pub queue: Vec<Shape>,
}

/// A train that shuttles back and forth along one metro line.
///
/// `from`/`to` are indices into that line's ordered station list, `t` is the
/// 0..1 progress along the current segment, and `dir` is +1 (forward along the
/// line) or -1 (back toward the start).
#[derive(Component)]
pub struct Train {
    pub line: usize,
    pub from: usize,
    pub to: usize,
    pub t: f32,
    pub dir: i32,
    pub passengers: Vec<Shape>,
}

/// Marker for the on-screen score/status UI text so a system can find and
/// update it each frame.
#[derive(Component)]
pub struct ScoreText;
