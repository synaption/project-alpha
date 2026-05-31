//! ECS **resources** — global, single-instance game state.

use crate::components::{DistrictKind, Layer};
use bevy::prelude::*;

// ---- Active layer -------------------------------------------------------

#[derive(Resource, Default)]
pub struct ActiveLayer(pub Layer);

// ---- Credits ------------------------------------------------------------

#[derive(Resource)]
pub struct Credits(pub f32);

impl Default for Credits {
    fn default() -> Self { Self(120.0) }
}

// ---- Build mode ---------------------------------------------------------

#[derive(Clone, Copy, PartialEq, Eq, Debug, Default)]
pub enum BuildMode {
    /// Click-drag between two endpoints to lay a trace on the active layer.
    #[default]
    Routing,
    /// Click empty canvas space to place a district of this type.
    PlacingDistrict(DistrictKind),
    /// Click canvas to place a full (3-layer) via. Phase 1 adds type picker.
    PlacingVia,
}

/// Transient build/drag state.
#[derive(Resource, Default)]
pub struct BuildState {
    pub mode: BuildMode,
    /// Entity grabbed at the start of a routing drag, if any.
    pub drag_from: Option<Entity>,
}

// ---- RNG ----------------------------------------------------------------

/// Xorshift64 PRNG — no extra crates needed.
#[derive(Resource)]
pub struct Rng(pub u64);

impl Default for Rng {
    fn default() -> Self { Self(0x9E37_79B9_7F4A_7C15) }
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

    pub fn f32(&mut self) -> f32 {
        (self.next_u64() >> 40) as f32 / (1u64 << 24) as f32
    }

    pub fn range(&mut self, lo: f32, hi: f32) -> f32 {
        lo + (hi - lo) * self.f32()
    }
}
