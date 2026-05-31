//! ECS **components** — per-entity data for CircuitCities.

use bevy::prelude::*;

// ---- Layer ---------------------------------------------------------------

#[derive(Clone, Copy, PartialEq, Eq, Debug, Default)]
pub enum Layer {
    #[default]
    Power,
    Data,
    Transit,
}

impl Layer {
    pub fn color(self) -> Color {
        match self {
            Layer::Power   => Color::srgb(0.96, 0.65, 0.14), // amber
            Layer::Data    => Color::srgb(0.00, 0.78, 0.91), // cyan
            Layer::Transit => Color::srgb(0.22, 0.83, 0.33), // green
        }
    }

    pub fn dim_color(self) -> Color {
        match self {
            Layer::Power   => Color::srgb(0.24, 0.16, 0.03),
            Layer::Data    => Color::srgb(0.00, 0.20, 0.23),
            Layer::Transit => Color::srgb(0.05, 0.21, 0.08),
        }
    }

    pub fn cycle(self) -> Self {
        match self {
            Layer::Power   => Layer::Data,
            Layer::Data    => Layer::Transit,
            Layer::Transit => Layer::Power,
        }
    }

    pub fn name(self) -> &'static str {
        match self {
            Layer::Power   => "Power (amber)",
            Layer::Data    => "Data (cyan)",
            Layer::Transit => "Transit (green)",
        }
    }
}

// ---- LayerSet -----------------------------------------------------------

/// Bitfield of which layers a Via connects. Bit 0 = Power, 1 = Data, 2 = Transit.
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub struct LayerSet(pub u8);

impl LayerSet {
    pub const POWER:   u8 = 0b001;
    pub const DATA:    u8 = 0b010;
    pub const TRANSIT: u8 = 0b100;

    pub fn all() -> Self { Self(0b111) }

    pub fn two(a: Layer, b: Layer) -> Self {
        let bit = |l: Layer| match l {
            Layer::Power   => Self::POWER,
            Layer::Data    => Self::DATA,
            Layer::Transit => Self::TRANSIT,
        };
        Self(bit(a) | bit(b))
    }

    pub fn contains(self, layer: Layer) -> bool {
        match layer {
            Layer::Power   => self.0 & Self::POWER   != 0,
            Layer::Data    => self.0 & Self::DATA    != 0,
            Layer::Transit => self.0 & Self::TRANSIT != 0,
        }
    }
}

// ---- CircuitNode marker -------------------------------------------------

/// Marker: this entity can serve as a trace endpoint (District, Via, PowerSource, Ground, Led).
/// Used as a unified filter for routing and spacing checks.
#[derive(Component)]
pub struct CircuitNode;

// ---- District -----------------------------------------------------------

#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum DistrictKind {
    Residential,
    PowerPlant,
    DataCenter,
    TransitHub,
    Commercial,
    Industrial,
}

impl DistrictKind {
    pub fn placement_cost(self) -> u32 {
        match self {
            DistrictKind::Residential => 20,
            DistrictKind::PowerPlant  => 35,
            DistrictKind::DataCenter  => 45,
            DistrictKind::TransitHub  => 30,
            DistrictKind::Commercial  => 50,
            DistrictKind::Industrial  => 60,
        }
    }

    pub fn color(self) -> Color {
        match self {
            DistrictKind::Residential => Color::srgb(0.45, 0.75, 0.45),
            DistrictKind::PowerPlant  => Color::srgb(0.96, 0.65, 0.14),
            DistrictKind::DataCenter  => Color::srgb(0.00, 0.78, 0.91),
            DistrictKind::TransitHub  => Color::srgb(0.22, 0.83, 0.33),
            DistrictKind::Commercial  => Color::srgb(0.80, 0.50, 0.85),
            DistrictKind::Industrial  => Color::srgb(0.85, 0.65, 0.30),
        }
    }
}

#[derive(Component)]
pub struct District {
    pub kind: DistrictKind,
    pub tier: u8,
    pub service_score: f32,
    pub tier_timer: f32,
    pub population: u32,
}

impl District {
    pub fn new(kind: DistrictKind) -> Self {
        Self { kind, tier: 1, service_score: 0.0, tier_timer: 0.0, population: 0 }
    }
}

// ---- Trace --------------------------------------------------------------

/// A single infrastructure connection between two endpoint entities on one layer.
/// Copy so it can be collected into a Vec snapshot inside systems.
#[derive(Component, Clone, Copy)]
pub struct Trace {
    pub layer: Layer,
    pub from: Entity,
    pub to: Entity,
    pub capacity: u32,
    pub load: u32,
    pub congested: bool,
}

// ---- Via ----------------------------------------------------------------

/// A cross-layer junction point. Traces on any of `connects` layers can
/// terminate here and transfer signal across layers.
#[derive(Component)]
pub struct Via {
    pub connects: LayerSet,
}

// ---- Circuit components -------------------------------------------------

/// Spawns electrons onto connected Power-layer traces at a fixed rate.
#[derive(Component)]
pub struct PowerSource {
    pub timer: f32,   // seconds until next electron emission
}

impl PowerSource {
    pub fn new() -> Self { Self { timer: 0.0 } }
}

/// Absorbs electrons — the sink of every circuit path.
#[derive(Component)]
pub struct Ground;

/// Emits a photon each time an electron passes through.
#[derive(Component)]
pub struct Led {
    pub lit_timer: f32,   // seconds remaining of the lit visual state
}

impl Led {
    pub fn new() -> Self { Self { lit_timer: 0.0 } }
}

// ---- Moving particles ---------------------------------------------------

/// A particle travelling along a Power-layer trace from a PowerSource toward Ground.
#[derive(Component)]
pub struct Electron {
    pub trace: Entity,     // which trace this electron is currently on
    pub t: f32,            // progress 0..1 along that trace
    pub forward: bool,     // true = from→to direction, false = to→from
    pub prev_node: Entity, // the node we just left (prevents immediate reversal)
}

/// A collectible photon emitted by an LED when an electron passes through.
#[derive(Component)]
pub struct Photon {
    pub velocity: Vec2,
    pub lifetime: f32,     // seconds remaining
}

// ---- HUD marker ---------------------------------------------------------

#[derive(Component)]
pub struct ScoreText;
