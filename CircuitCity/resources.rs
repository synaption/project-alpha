//! ECS **resources** — global, single-instance game state.
//!
//! Resources are world-unique data (as opposed to per-entity components).
//! Here they hold the score, the metro lines, transient input state, spawn
//! timers, and a tiny self-contained random number generator.

use crate::components::Shape;
use bevy::prelude::*;

/// Whether the game is still running or has ended (a station overflowed).
#[derive(Default, Clone, Copy, PartialEq, Eq)]
pub enum Phase {
    #[default]
    Playing,
    GameOver,
}

/// Top-level game state.
#[derive(Resource)]
pub struct Game {
    pub score: u32,
    pub phase: Phase,
}

impl Default for Game {
    fn default() -> Self {
        Self {
            score: 0,
            phase: Phase::Playing,
        }
    }
}

/// One metro line: an ordered list of station entities plus a display colour.
/// `has_train` ensures we only ever spawn a single train per line.
pub struct MetroLine {
    pub stations: Vec<Entity>,
    pub color: Color,
    pub has_train: bool,
}

/// All metro lines in the game.
#[derive(Resource, Default)]
pub struct Lines {
    pub lines: Vec<MetroLine>,
}

/// Which line the player is currently editing (selected with keys 1/2/3).
#[derive(Resource)]
pub struct ActiveLine(pub usize);

impl Default for ActiveLine {
    fn default() -> Self {
        Self(0)
    }
}

/// Transient state for the click-drag that builds a connection between two
/// stations.
#[derive(Resource, Default)]
pub struct DragState {
    pub from: Option<Entity>,
}

/// Timers controlling how often new stations and passengers appear.
#[derive(Resource)]
pub struct SpawnTimers {
    pub station: Timer,
    pub passenger: Timer,
}

impl Default for SpawnTimers {
    fn default() -> Self {
        Self {
            station: Timer::from_seconds(9.0, TimerMode::Repeating),
            passenger: Timer::from_seconds(1.6, TimerMode::Repeating),
        }
    }
}

/// A tiny xorshift64 PRNG kept in-house so the project pulls in **no** extra
/// crates beyond Bevy itself.
#[derive(Resource)]
pub struct Rng(pub u64);

impl Default for Rng {
    fn default() -> Self {
        // Any non-zero seed works.
        Self(0x9E37_79B9_7F4A_7C15)
    }
}

impl Rng {
    pub fn next_u64(&mut self) -> u64 {
        let mut x = self.0;
        x ^= x << 13;
        x ^= x >> 7;
        x ^= x << 17;
        self.0 = x;
        x
    }

    /// Uniform float in [0, 1).
    pub fn f32(&mut self) -> f32 {
        // Use the top 24 bits for a well-distributed mantissa.
        (self.next_u64() >> 40) as f32 / (1u64 << 24) as f32
    }

    pub fn range(&mut self, lo: f32, hi: f32) -> f32 {
        lo + (hi - lo) * self.f32()
    }

    pub fn pick_shape(&mut self) -> Shape {
        Shape::all()[(self.next_u64() % 3) as usize]
    }
}
