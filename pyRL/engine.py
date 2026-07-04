from __future__ import annotations
import os
import pickle
import random
import hashlib
from dataclasses import dataclass
from enum import Enum, auto
import tcod.event
import tcod.console
from world import World
from game_map import GameMap
from game_clock import GameClock, action_cost, to_calendar_minutes, MINUTES_PER_DAY, MINUTES_PER_HOUR, DAY_STRETCH
from message_log import MessageLog
from components import (
    Position, Fighter, Name, AI, Inventory, Item, Consumable, Level,
    Stairs, Friendly, Dialog, VillagerAI, FactionAgent, Speed, Location,
)
from systems.combat_system import attack
import systems.ai_system as ai_system
import systems.villager_system as villager_system
import systems.faction_system as faction_system
from systems.fov_system import update_fov
from systems.render_system import (
    render_all,
    render_inventory,
    render_level_up,
    render_dialog,
    render_world_map,
    render_opening_screen,
    render_home_menu,
    render_pause_menu,
    render_options_menu,
    render_controls_menu,
    render_ingame_menu,
)
import systems.farm_system as farm_system
from entity_factories import make_player_components, spawn_caravan
from map_gen import generate_dungeon
from town_gen import generate_town
from town_gen_procedural import generate_town as generate_procedural_town
from surface_gen import generate_surface_zone
import color
import constants as C
import palette_registry
import visual_registry


DEPTH_WINDOW_RADIUS = 1   # dungeon depths within this many levels of the current one stay active

# Thornveil is the one hand-crafted town; these are procedurally generated
# (see town_gen_procedural.py) but persist and get their own dungeons exactly
# like Thornveil does, once visited.
OTHER_TOWN_SITES = ["greywater", "oakhollow", "saltmarsh"]
DEFAULT_SETTINGS = {
    "display_mode": "Windowed",
    "brightness": 100,
    "master_volume": 80,
    "music_volume": 70,
    "sfx_volume": 75,
    "active_tileset": "hexany_visual",
    "tileset_fallback_preset": "registry_default",
    "text_scale": 100,
    "tile_scale": 100,
    "active_palette": "classic",
    "control_scheme": "Keyboard+Mouse",
}

# Every act_one() below shares the same (world, game_map, player, clock,
# message_log, eid) signature, so the scheduler can dispatch on whichever tag
# component an entity has without a growing if/elif chain — a new entity
# "kind" is a one-line addition here.
_ACT_ONE_BY_TAG = {
    AI: ai_system.act_one,
    VillagerAI: villager_system.act_one,
    FactionAgent: faction_system.act_one,
}


def _derive_seed(*parts) -> int:
    """A process-stable seed from the master seed + location parts.

    Python's builtin hash() randomizes string hashing per-process
    (PYTHONHASHSEED), so hash((seed, "dungeon", site, depth)) is NOT
    reproducible across runs — which would break the "same seed, same world"
    guarantee and make save/reload regenerate never-visited floors differently.
    SHA-256 over the joined parts is stable everywhere.
    """
    key = "|".join(str(p) for p in parts).encode()
    return int.from_bytes(hashlib.sha256(key).digest()[:8], "big")


def _build_surface_towns(seed: int) -> dict[tuple[int, int], str]:
    """Deterministically place towns on the surface zone grid from the seed.

    Thornveil sits at the center world cell's center zone (fixed, so the start is
    stable). Each other town is dropped on a distinct random world cell's center
    zone. Returns {(zx, zy): site}.
    """
    rng = random.Random(_derive_seed(seed, "surface_towns"))
    center_cell = (C.WORLD_CELLS_W // 2, C.WORLD_CELLS_H // 2)
    towns: dict[tuple[int, int], str] = {}

    def cell_center_zone(cx: int, cy: int) -> tuple[int, int]:
        return (cx * C.ZONES_PER_CELL + C.ZONES_PER_CELL // 2,
                cy * C.ZONES_PER_CELL + C.ZONES_PER_CELL // 2)

    towns[cell_center_zone(*center_cell)] = "thornveil"
    used_cells = {center_cell}
    for site in OTHER_TOWN_SITES:
        for _ in range(200):
            cx = rng.randrange(C.WORLD_CELLS_W)
            cy = rng.randrange(C.WORLD_CELLS_H)
            if (cx, cy) not in used_cells:
                used_cells.add((cx, cy))
                towns[cell_center_zone(cx, cy)] = site
                break
    return towns


class GameState(Enum):
    OPENING = auto()
    HOME_MENU = auto()
    PLAYER_TURN = auto()
    ENEMY_TURN = auto()
    PLAYER_DEAD = auto()
    SHOW_INVENTORY = auto()
    DROP_INVENTORY = auto()
    LEVEL_UP = auto()
    TALKING = auto()
    WORLD_MAP = auto()
    PAUSE_MENU = auto()
    OPTIONS_MENU = auto()
    CONTROLS_MENU = auto()
    INGAME_MENU = auto()


MOVE_KEYS: dict[tcod.event.KeySym, tuple[int, int]] = {
    tcod.event.KeySym.UP:    (0, -1),
    tcod.event.KeySym.DOWN:  (0, 1),
    tcod.event.KeySym.LEFT:  (-1, 0),
    tcod.event.KeySym.RIGHT: (1, 0),
    tcod.event.KeySym.H: (-1,  0),
    tcod.event.KeySym.J: ( 0,  1),
    tcod.event.KeySym.K: ( 0, -1),
    tcod.event.KeySym.L: ( 1,  0),
    tcod.event.KeySym.Y: (-1, -1),
    tcod.event.KeySym.U: ( 1, -1),
    tcod.event.KeySym.B: (-1,  1),
    tcod.event.KeySym.N: ( 1,  1),
    tcod.event.KeySym.KP_8: (0, -1),
    tcod.event.KeySym.KP_2: (0,  1),
    tcod.event.KeySym.KP_4: (-1, 0),
    tcod.event.KeySym.KP_6: ( 1, 0),
    tcod.event.KeySym.KP_7: (-1, -1),
    tcod.event.KeySym.KP_9: ( 1, -1),
    tcod.event.KeySym.KP_1: (-1,  1),
    tcod.event.KeySym.KP_3: ( 1,  1),
    tcod.event.KeySym.KP_5:  (0, 0),
    tcod.event.KeySym.PERIOD:(0, 0),
}


@dataclass
class FloorState:
    """One floor's persistent state: its own World (entities) and GameMap (tiles).

    Each floor gets a fully separate World instance rather than a shared one —
    that's what makes "off-screen" simulation cheap and safe: AI/needs/rendering
    code only ever queries a specific floor's `world` (see Engine._active_locations
    for which floors that includes each turn), so a floor outside that set is
    structurally invisible to every system, not just conventionally ignored.
    See docs/architecture.md's Persistence section.
    """
    world: World
    game_map: GameMap
    last_active_calendar: float | None = None   # town-kind floors only; see Engine._catch_up_floor


class Engine:
    def __init__(self, seed: int | None = None) -> None:
        self.seed = seed if seed is not None else random.randrange(2**31)

        self.floors: dict[Location, FloorState] = {}
        self.inventory_world = World()   # carried items; independent of any floor's World
        self._player_components = make_player_components(0, 0)

        # Where every town sits on the surface zone grid (deterministic from seed),
        # plus the reverse index used to canonicalize dungeon→town ascent.
        self.surface_towns: dict[tuple[int, int], str] = _build_surface_towns(self.seed)
        self.town_zone: dict[str, tuple[int, int]] = {s: z for z, s in self.surface_towns.items()}
        self.discovered_cells: set[tuple[int, int]] = set()
        self.world_map_cursor: tuple[int, int] = (0, 0)

        self.world: World = None
        self.game_map: GameMap | None = None
        self.player: int = None

        self.message_log = MessageLog()
        self.clock = GameClock()
        self.state = GameState.OPENING
        self.location: Location = self._surface_location_at(*self.town_zone["thornveil"])
        self.home_menu_index = 0
        self.pause_menu_index = 0
        self.options_menu_index = 0
        self.ingame_menu_index = 0
        self.options_return_state = GameState.HOME_MENU
        self.ingame_sections = ["Inventory", "Active Quests", "Maps", "Stats"]
        self.active_quests = ["Find the dungeon entrance south of Thornveil."]
        self.has_save_file = os.path.exists(C.SAVE_PATH)
        self.settings = dict(DEFAULT_SETTINGS)

        self.talking_to: int | None = None
        self.dialog_line: int = 0

        self._enter_floor(self.location)

        # A trading caravan roams the surface, circuiting between the towns; it
        # starts in Thornveil's zone (the World the player just entered).
        caravan = spawn_caravan(
            self.world, 39, 25, zone=self.town_zone["thornveil"],
            circuit=sorted(self.surface_towns.keys()),
        )
        self.world.get(caravan, Speed).next_turn = self.clock.total_minutes   # don't bank a backlog

        self.message_log.add(
            "You arrive in Thornveil. The dungeon entrance lies to the south.",
            color.MSG_WELCOME,
        )
        self._ensure_runtime_defaults()

    def _ensure_runtime_defaults(self) -> None:
        if not hasattr(self, "home_menu_index"):
            self.home_menu_index = 0
        if not hasattr(self, "pause_menu_index"):
            self.pause_menu_index = 0
        if not hasattr(self, "options_menu_index"):
            self.options_menu_index = 0
        if not hasattr(self, "ingame_menu_index"):
            self.ingame_menu_index = 0
        if not hasattr(self, "options_return_state"):
            self.options_return_state = GameState.HOME_MENU
        if not hasattr(self, "ingame_sections"):
            self.ingame_sections = ["Inventory", "Active Quests", "Maps", "Stats"]
        if not hasattr(self, "active_quests"):
            self.active_quests = ["Find the dungeon entrance south of Thornveil."]
        if not hasattr(self, "settings"):
            self.settings = dict(DEFAULT_SETTINGS)
        else:
            if "tileset_style" in self.settings and "active_tileset" not in self.settings:
                legacy = str(self.settings.pop("tileset_style"))
                # Legacy saves only had ascii/enhanced. We map enhanced to the
                # new preferred visual profile while still exposing enhanced_legacy.
                if legacy == "enhanced":
                    self.settings["active_tileset"] = "hexany_visual"
                elif legacy == "ascii":
                    self.settings["active_tileset"] = "ascii"
                else:
                    self.settings["active_tileset"] = visual_registry.normalize_tileset_name(legacy)
            for key, value in DEFAULT_SETTINGS.items():
                self.settings.setdefault(key, value)
        self.settings["active_tileset"] = visual_registry.normalize_tileset_name(
            str(self.settings["active_tileset"])
        )
        if self.settings["active_tileset"] not in visual_registry.tileset_names():
            self.settings["active_tileset"] = "hexany_visual"
        if self.settings["tileset_fallback_preset"] not in visual_registry.fallback_preset_names():
            self.settings["tileset_fallback_preset"] = "registry_default"
        text_min, text_max, tile_min, tile_max = visual_registry.scale_bounds(
            str(self.settings["active_tileset"])
        )
        self.settings["text_scale"] = max(text_min, min(text_max, int(self.settings["text_scale"])))
        self.settings["tile_scale"] = max(tile_min, min(tile_max, int(self.settings["tile_scale"])))
        self.settings["active_palette"] = palette_registry.apply_palette(str(self.settings["active_palette"]))
        if not hasattr(self, "has_save_file"):
            self.has_save_file = os.path.exists(C.SAVE_PATH)

    def _home_menu_items(self) -> list[str]:
        start = "Continue Adventure" if self.has_save_file else "Begin Adventure"
        return [start, "Options", "Quit to Desktop"]

    def _pause_menu_items(self) -> list[str]:
        return ["Resume", "In-Game Menu", "Options", "Save Game", "Quit to Desktop"]

    # ------------------------------------------------------------------
    def _surface_location_at(self, zx: int, zy: int) -> Location:
        """The Location for a surface zone — a town zone if one is registered at
        these coords, else plain wilderness."""
        return Location(kind="surface", site=self.surface_towns.get((zx, zy), ""), zx=zx, zy=zy)

    def _is_town_zone(self, location: Location) -> bool:
        """Whether a location is a surface zone that contains a town (drives the
        villager/farm life-sim, which wilderness zones and dungeons don't have)."""
        return location.kind == "surface" and bool(location.site)

    def _canonical_location(self, location: Location) -> Location:
        """Resolve a Stairs destination into the exact key used in self.floors.

        A dungeon's depth-1 up-stairs names its town by `site` but can't know the
        town's surface coords at generation time — it emits placeholder zx/zy=0.
        Reconcile that to the registered zone before it's used as a dict key."""
        if location.kind == "surface" and location.site and (location.zx, location.zy) == (0, 0):
            zx, zy = self.town_zone[location.site]
            return self._surface_location_at(zx, zy)
        return location

    # ------------------------------------------------------------------
    def _generate_floor(self, location: Location) -> FloorState:
        world = World()
        if location.kind == "surface":
            if location.site:
                # A town zone. Its interior map (buildings/villagers/farm) is the
                # content of this surface zone; seeded by site so Thornveil stays
                # hand-crafted and procedural towns stay stable wherever they sit.
                if location.site == "thornveil":
                    game_map = generate_town(
                        world=world,
                        map_width=C.MAP_WIDTH,
                        map_height=C.MAP_HEIGHT,
                    )
                else:
                    rng = random.Random(_derive_seed(self.seed, "town", location.site))
                    game_map = generate_procedural_town(
                        world=world,
                        site=location.site,
                        map_width=C.MAP_WIDTH,
                        map_height=C.MAP_HEIGHT,
                        rng=rng,
                    )
            else:
                rng = random.Random(_derive_seed(self.seed, "surface", location.zx, location.zy))
                game_map = generate_surface_zone(world, location.zx, location.zy, rng)
        else:
            # Deterministic per floor: the same seed always generates the same
            # layout the first time that floor is visited. Once generated, this
            # FloorState (and everything that happens to it) persists — the seed
            # is never consulted again for a floor that's already been created.
            rng = random.Random(_derive_seed(self.seed, "dungeon", location.site, location.depth))
            game_map = generate_dungeon(
                world=world,
                site=location.site,
                depth=location.depth,
                map_width=C.MAP_WIDTH,
                map_height=C.MAP_HEIGHT,
                max_rooms=C.MAX_ROOMS,
                room_min_size=C.ROOM_MIN_SIZE,
                room_max_size=C.ROOM_MAX_SIZE,
                rng=rng,
            )
        return FloorState(world=world, game_map=game_map)

    def _enter_floor(
        self, location: Location, arrive_at: tuple[int, int] | None = None,
        arrive_at_downstairs: bool = False,
    ) -> None:
        location = self._canonical_location(location)
        is_new = location not in self.floors
        if is_new:
            self.floors[location] = self._generate_floor(location)
        fs = self.floors[location]

        self.location = location
        self.world = fs.world
        self.game_map = fs.game_map
        self.player = self.world.create_entity(*self._player_components)

        pos = self.world.get(self.player, Position)
        if arrive_at is not None:
            # Explicit landing spot — e.g. the opposite edge when walking off a
            # zone edge, or a fast-travel arrival point.
            pos.x, pos.y = arrive_at
        elif arrive_at_downstairs:
            # Climbing up: emerge at this floor's down stairs, the same
            # stairwell that leads back down to where we came from.
            pos.x, pos.y = self.game_map.downstairs_location
        else:
            pos.x, pos.y = self.game_map.player_start

        if location.kind == "surface":
            self.discovered_cells.add((location.zx // C.ZONES_PER_CELL, location.zy // C.ZONES_PER_CELL))
        if self._is_town_zone(location):
            self._catch_up_floor(fs, is_new)

        update_fov(self.world, self.game_map, self.player)

        # Every other Speed entity here was either just spawned (new floor) or
        # was frozen since we last left (revisit) — either way, sync its
        # schedule to "now" so it doesn't burst through a backlog of owed turns.
        for eid, (speed,) in self.world.query(Speed):
            if eid != self.player:
                speed.next_turn = self.clock.total_minutes

    def _catch_up_floor(self, fs: FloorState, is_new: bool) -> None:
        """Advance villager needs and farm growth for however much calendar
        time passed while the player was away from this town.

        Deliberately *not* a turn-by-turn replay — nobody was watching Gus walk
        to his plots, so farm_system.catch_up_day abstracts a whole day's
        tending into one step; see its docstring. Only meaningful for town-kind
        floors — dungeon floors that fall outside the active depth window
        (see _active_locations) are simply frozen with no catch-up at all,
        exactly as an off-FOV hostile is on the current floor.
        """
        current_calendar = to_calendar_minutes(self.clock.total_minutes)
        if is_new or fs.last_active_calendar is None:
            fs.last_active_calendar = current_calendar
            return
        elapsed = current_calendar - fs.last_active_calendar
        if elapsed <= 0:
            return
        villager_system.update_needs(fs.world, elapsed)
        days_passed = int(current_calendar // MINUTES_PER_DAY) - int(fs.last_active_calendar // MINUTES_PER_DAY)
        for _ in range(days_passed):
            farm_system.catch_up_day(fs.world, fs.game_map)
        fs.last_active_calendar = current_calendar

    # ------------------------------------------------------------------
    def handle_events(self, events: list) -> None:
        for event in events:
            if isinstance(event, tcod.event.Quit):
                raise SystemExit(0)

            if self.state == GameState.OPENING:
                self._handle_opening_event(event)
                continue

            if self.state == GameState.HOME_MENU:
                self._handle_home_menu_event(event)
                continue

            if self.state == GameState.PLAYER_DEAD:
                if isinstance(event, tcod.event.KeyDown) and event.sym == tcod.event.KeySym.ESCAPE:
                    raise SystemExit(0)
                continue

            if self.state == GameState.PAUSE_MENU:
                self._handle_pause_menu_event(event)
                continue

            if self.state == GameState.OPTIONS_MENU:
                self._handle_options_menu_event(event)
                continue

            if self.state == GameState.CONTROLS_MENU:
                self._handle_controls_menu_event(event)
                continue

            if self.state == GameState.INGAME_MENU:
                self._handle_ingame_menu_event(event)
                continue

            if self.state == GameState.TALKING:
                self._handle_talking_event(event)
                continue

            if self.state == GameState.SHOW_INVENTORY:
                self._handle_inventory_event(event, drop=False)
                continue

            if self.state == GameState.DROP_INVENTORY:
                self._handle_inventory_event(event, drop=True)
                continue

            if self.state == GameState.LEVEL_UP:
                self._handle_level_up_event(event)
                continue

            if self.state == GameState.WORLD_MAP:
                self._handle_world_map_event(event)
                continue

            if self.state == GameState.PLAYER_TURN and isinstance(event, tcod.event.KeyDown):
                self._handle_player_key(event)

        if self.state == GameState.ENEMY_TURN:
            self._do_enemy_turn()

    # ------------------------------------------------------------------
    def _handle_opening_event(self, event: tcod.event.Event) -> None:
        if isinstance(event, (tcod.event.KeyDown, tcod.event.MouseButtonDown)):
            self.state = GameState.HOME_MENU

    def _handle_home_menu_event(self, event: tcod.event.Event) -> None:
        if not isinstance(event, tcod.event.KeyDown):
            return
        items = self._home_menu_items()
        if event.sym == tcod.event.KeySym.UP:
            self.home_menu_index = (self.home_menu_index - 1) % len(items)
            return
        if event.sym == tcod.event.KeySym.DOWN:
            self.home_menu_index = (self.home_menu_index + 1) % len(items)
            return
        if event.sym not in (tcod.event.KeySym.RETURN, tcod.event.KeySym.KP_ENTER):
            return
        if self.home_menu_index == 0:
            self.state = GameState.PLAYER_TURN
        elif self.home_menu_index == 1:
            self.options_return_state = GameState.HOME_MENU
            self.state = GameState.OPTIONS_MENU
        else:
            raise SystemExit(0)

    def _handle_pause_menu_event(self, event: tcod.event.Event) -> None:
        if not isinstance(event, tcod.event.KeyDown):
            return
        items = self._pause_menu_items()
        if event.sym == tcod.event.KeySym.ESCAPE:
            self.state = GameState.PLAYER_TURN
            return
        if event.sym == tcod.event.KeySym.UP:
            self.pause_menu_index = (self.pause_menu_index - 1) % len(items)
            return
        if event.sym == tcod.event.KeySym.DOWN:
            self.pause_menu_index = (self.pause_menu_index + 1) % len(items)
            return
        if event.sym not in (tcod.event.KeySym.RETURN, tcod.event.KeySym.KP_ENTER):
            return
        if self.pause_menu_index == 0:
            self.state = GameState.PLAYER_TURN
        elif self.pause_menu_index == 1:
            self.state = GameState.INGAME_MENU
        elif self.pause_menu_index == 2:
            self.options_return_state = GameState.PAUSE_MENU
            self.state = GameState.OPTIONS_MENU
        elif self.pause_menu_index == 3:
            self.save_game(C.SAVE_PATH)
            self.message_log.add("Game saved.", color.MSG_STATUS)
        else:
            raise SystemExit(0)

    def _adjust_setting(self, key: str, delta: int) -> None:
        if key == "display_mode":
            self.settings[key] = "Fullscreen" if self.settings[key] == "Windowed" else "Windowed"
        elif key == "brightness":
            self.settings[key] = max(50, min(150, int(self.settings[key]) + delta * 10))
        elif key in ("master_volume", "music_volume", "sfx_volume"):
            self.settings[key] = max(0, min(100, int(self.settings[key]) + delta * 10))
        elif key == "active_tileset":
            names = visual_registry.tileset_names()
            idx = names.index(self.settings[key])
            self.settings[key] = names[(idx + delta) % len(names)]
            self.message_log.add(f"Tileset switched to {self.settings[key]}.", color.MSG_STATUS)
            text_min, text_max, tile_min, tile_max = visual_registry.scale_bounds(str(self.settings[key]))
            self.settings["text_scale"] = max(text_min, min(text_max, int(self.settings["text_scale"])))
            self.settings["tile_scale"] = max(tile_min, min(tile_max, int(self.settings["tile_scale"])))
        elif key == "tileset_fallback_preset":
            presets = visual_registry.fallback_preset_names()
            idx = presets.index(self.settings[key])
            self.settings[key] = presets[(idx + delta) % len(presets)]
        elif key == "text_scale":
            text_min, text_max, _, _ = visual_registry.scale_bounds(str(self.settings["active_tileset"]))
            self.settings[key] = max(text_min, min(text_max, int(self.settings[key]) + delta * 25))
            self.message_log.add("Text scale will apply after restart.", color.MSG_STATUS)
        elif key == "tile_scale":
            _, _, tile_min, tile_max = visual_registry.scale_bounds(str(self.settings["active_tileset"]))
            self.settings[key] = max(tile_min, min(tile_max, int(self.settings[key]) + delta * 25))
        elif key == "active_palette":
            palettes = palette_registry.palette_names()
            idx = palettes.index(self.settings[key])
            self.settings[key] = palettes[(idx + delta) % len(palettes)]
            palette_registry.apply_palette(self.settings[key])
            self.message_log.add(f"Palette switched to {self.settings[key]}.", color.MSG_STATUS)
        elif key == "control_scheme":
            self.settings[key] = "Controller" if self.settings[key] == "Keyboard+Mouse" else "Keyboard+Mouse"

    def _handle_options_menu_event(self, event: tcod.event.Event) -> None:
        if not isinstance(event, tcod.event.KeyDown):
            return
        option_keys = [
            "display_mode",
            "brightness",
            "master_volume",
            "music_volume",
            "sfx_volume",
            "active_tileset",
            "tileset_fallback_preset",
            "text_scale",
            "tile_scale",
            "active_palette",
            "controls_menu",
            "control_scheme",
        ]
        if event.sym == tcod.event.KeySym.ESCAPE:
            self.state = self.options_return_state
            return
        if event.sym == tcod.event.KeySym.UP:
            self.options_menu_index = (self.options_menu_index - 1) % len(option_keys)
            return
        if event.sym == tcod.event.KeySym.DOWN:
            self.options_menu_index = (self.options_menu_index + 1) % len(option_keys)
            return
        selected_key = option_keys[self.options_menu_index]
        if selected_key == "controls_menu" and event.sym in (tcod.event.KeySym.RETURN, tcod.event.KeySym.KP_ENTER):
            self.state = GameState.CONTROLS_MENU
            return
        if event.sym in (tcod.event.KeySym.LEFT, tcod.event.KeySym.RIGHT):
            if selected_key != "controls_menu":
                delta = -1 if event.sym == tcod.event.KeySym.LEFT else 1
                self._adjust_setting(selected_key, delta)

    def _handle_controls_menu_event(self, event: tcod.event.Event) -> None:
        if isinstance(event, tcod.event.KeyDown) and event.sym == tcod.event.KeySym.ESCAPE:
            self.state = GameState.OPTIONS_MENU

    def _handle_ingame_menu_event(self, event: tcod.event.Event) -> None:
        if not isinstance(event, tcod.event.KeyDown):
            return
        if event.sym in (tcod.event.KeySym.ESCAPE, tcod.event.KeySym.TAB):
            self.state = GameState.PLAYER_TURN
            return
        if event.sym == tcod.event.KeySym.UP:
            self.ingame_menu_index = (self.ingame_menu_index - 1) % len(self.ingame_sections)
        elif event.sym == tcod.event.KeySym.DOWN:
            self.ingame_menu_index = (self.ingame_menu_index + 1) % len(self.ingame_sections)

    # ------------------------------------------------------------------
    def _handle_player_key(self, event: tcod.event.KeyDown) -> None:
        pos = self.world.get(self.player, Position)
        sym = event.sym

        if sym == tcod.event.KeySym.ESCAPE:
            self.pause_menu_index = 0
            self.state = GameState.PAUSE_MENU
            return

        if sym == tcod.event.KeySym.TAB:
            self.state = GameState.INGAME_MENU
            return

        if sym == tcod.event.KeySym.I:
            self.state = GameState.SHOW_INVENTORY
            return

        if sym == tcod.event.KeySym.D:
            self.state = GameState.DROP_INVENTORY
            return

        if sym == tcod.event.KeySym.G:
            self._pickup()
            return

        if sym == tcod.event.KeySym.S:
            self.save_game(C.SAVE_PATH)
            self.message_log.add("Game saved.", color.MSG_STATUS)
            return

        if sym == tcod.event.KeySym.GREATER or (
            sym == tcod.event.KeySym.PERIOD and bool(event.mod & tcod.event.Modifier.SHIFT)
        ):
            self._use_stairs(pos, "down")
            return

        if sym == tcod.event.KeySym.LESS or (
            sym == tcod.event.KeySym.COMMA and bool(event.mod & tcod.event.Modifier.SHIFT)
        ):
            self._use_stairs(pos, "up")
            return

        if sym == tcod.event.KeySym.SLASH and bool(event.mod & tcod.event.Modifier.SHIFT):
            self._show_help()
            return

        if sym == tcod.event.KeySym.M:
            self._open_world_map()
            return

        if sym in MOVE_KEYS:
            dx, dy = MOVE_KEYS[sym]
            if dx == 0 and dy == 0:
                self._spend_player_turn()
                self.state = GameState.ENEMY_TURN
                return
            self._move_or_attack(pos, dx, dy)

    def _spend_player_turn(self) -> None:
        """Advance the player's own Speed schedule by one action's worth of game-time."""
        speed = self.world.get(self.player, Speed)
        speed.next_turn = self.clock.total_minutes + action_cost(speed.value)

    def _neighbor_zone(self, dx: int, dy: int) -> tuple[Location, tuple[int, int]] | None:
        """The surface zone reached by stepping off the current zone's edge in
        direction (dx,dy), plus the opposite-edge arrival (x,y). None if the step
        doesn't leave the map or lands outside the bounded world grid."""
        pos = self.world.get(self.player, Position)
        w, h = self.game_map.width, self.game_map.height
        nzx, nzy = self.location.zx, self.location.zy
        ax, ay = pos.x, pos.y
        # Resolve one axis (x first on a diagonal) so a corner step doesn't teleport.
        if pos.x + dx >= w:      nzx += 1; ax = 0
        elif pos.x + dx < 0:     nzx -= 1; ax = w - 1
        elif pos.y + dy >= h:    nzy += 1; ay = 0
        elif pos.y + dy < 0:     nzy -= 1; ay = h - 1
        else:                    return None   # didn't step off an edge
        if not (0 <= nzx < C.SURFACE_ZONES_W and 0 <= nzy < C.SURFACE_ZONES_H):
            return None   # edge of the world
        return self._surface_location_at(nzx, nzy), (ax, ay)

    def _try_edge_walk(self, pos: Position, dx: int, dy: int) -> bool:
        """If a move steps off a surface zone's edge, cross into the neighbouring
        zone (costing one turn). Returns True if it handled the input."""
        if self.location.kind != "surface":
            return False
        if self.game_map.in_bounds(pos.x + dx, pos.y + dy):
            return False
        step = self._neighbor_zone(dx, dy)
        if step is None:
            self.message_log.add("You have reached the edge of the world.", color.INVALID)
            return True   # consumed the keypress, but no turn spent
        dest, arrive_at = step
        if self._is_town_zone(self.location):
            self.floors[self.location].last_active_calendar = to_calendar_minutes(self.clock.total_minutes)
        self.world.delete_entity(self.player)
        self.world.flush_dead()
        self._enter_floor(dest, arrive_at=arrive_at)
        self._spend_player_turn()   # reads the NEW floor's player; costs one action
        self.state = GameState.ENEMY_TURN
        return True

    def _move_or_attack(self, pos: Position, dx: int, dy: int) -> None:
        if self._try_edge_walk(pos, dx, dy):
            return
        nx, ny = pos.x + dx, pos.y + dy
        if not self.game_map.in_bounds(nx, ny) or not self.game_map.is_walkable(nx, ny):
            self.message_log.add("That way is blocked.", color.INVALID)
            return
        target = self.game_map.get_blocking_entity(nx, ny)
        if target is not None:
            if self.world.has(target, Friendly):
                self._start_dialog(target)
                return          # talking does not spend a turn
            if self.world.has(target, Fighter):
                attack(self.world, self.player, target, self.player, self.message_log, True)
                self._check_level_up()
        else:
            pos.x, pos.y = nx, ny
            update_fov(self.world, self.game_map, self.player)
        self._spend_player_turn()
        if self.state != GameState.LEVEL_UP:
            self.state = GameState.ENEMY_TURN

    def _start_dialog(self, entity: int) -> None:
        self.talking_to = entity
        self.dialog_line = 0
        self.state = GameState.TALKING

    def _handle_talking_event(self, event: tcod.event.Event) -> None:
        if not isinstance(event, tcod.event.KeyDown):
            return
        dialog = self.world.get(self.talking_to, Dialog) if self.talking_to is not None else None
        if dialog is None or event.sym == tcod.event.KeySym.ESCAPE:
            self.talking_to = None
            self.state = GameState.PLAYER_TURN
            return
        self.dialog_line += 1
        if self.dialog_line >= len(dialog.lines):
            self.talking_to = None
            self.state = GameState.PLAYER_TURN

    def _move_entity(self, src: World, dst: World, eid: int, drop_position: bool = False) -> int:
        """Move an entity's components from one World to another, returning its new id.

        Used to hand items between a floor's World and self.inventory_world —
        entity ids are only meaningful within the World that created them, so a
        picked-up item can't just keep referencing its old floor-local id once
        the player has moved to a different floor's World.
        """
        components = src.all_components(eid)
        if drop_position:
            components = [c for c in components if not isinstance(c, Position)]
        new_id = dst.create_entity(*components)
        src.delete_entity(eid)
        src.flush_dead()
        return new_id

    def _pickup(self) -> None:
        pos = self.world.get(self.player, Position)
        items = self.game_map.get_items_at(pos.x, pos.y)
        if not items:
            self.message_log.add("There is nothing here to pick up.", color.INVALID)
            return
        inv = self.world.get(self.player, Inventory)
        if len(inv.items) >= inv.capacity:
            self.message_log.add("Your inventory is full.", color.INVALID)
            return
        item_id = items[0]
        name = self.world.get(item_id, Name)
        carried_id = self._move_entity(self.world, self.inventory_world, item_id, drop_position=True)
        inv.items.append(carried_id)
        self.message_log.add(f"You pick up the {name.name if name else 'item'}.", color.WHITE)
        self._spend_player_turn()
        self.state = GameState.ENEMY_TURN

    def _use_stairs(self, pos: Position, direction: str) -> None:
        stairs = self.game_map.get_stairs_at(pos.x, pos.y)
        stair_comp = self.world.get(stairs, Stairs) if stairs is not None else None
        if stair_comp is None or stair_comp.direction != direction:
            self.message_log.add("There are no stairs here.", color.INVALID)
            return

        source = self.location
        if self._is_town_zone(source):
            self.floors[source].last_active_calendar = to_calendar_minutes(self.clock.total_minutes)

        destination = stair_comp.destination
        self.world.delete_entity(self.player)
        self.world.flush_dead()

        self._enter_floor(destination, arrive_at_downstairs=(direction == "up"))

        if self._is_town_zone(self.location):
            self.message_log.add(f"You climb back up to {self.location.site.title()}.", color.DESCEND)
        elif direction == "up":
            self.message_log.add(f"You climb up to dungeon level {self.location.depth}.", color.DESCEND)
        else:
            self.message_log.add(f"You descend to dungeon level {self.location.depth}.", color.DESCEND)
        self.state = GameState.PLAYER_TURN

    def _show_help(self) -> None:
        self.message_log.add(
            "move/attack g=get i=inv d=drop tab=in-game menu m=world map s=save esc=pause",
            color.WHITE,
        )

    # ------------------------------------------------------------------
    def _enemies_near_player(self, radius: int = C.FOV_RADIUS) -> bool:
        ppos = self.world.get(self.player, Position)
        for eid, (pos, _ai) in self.world.query(Position, AI):
            if abs(pos.x - ppos.x) + abs(pos.y - ppos.y) <= radius:
                return True
        return False

    def _open_world_map(self) -> None:
        if self.location.kind != "surface":
            self.message_log.add("You can only read the map above ground.", color.INVALID)
            return
        self.world_map_cursor = (self.location.zx // C.ZONES_PER_CELL, self.location.zy // C.ZONES_PER_CELL)
        self.state = GameState.WORLD_MAP

    def _handle_world_map_event(self, event: tcod.event.Event) -> None:
        if not isinstance(event, tcod.event.KeyDown):
            return
        sym = event.sym
        if sym in (tcod.event.KeySym.ESCAPE, tcod.event.KeySym.M):
            self.state = GameState.PLAYER_TURN
            return
        if sym in (tcod.event.KeySym.RETURN, tcod.event.KeySym.KP_ENTER):
            self._fast_travel_to(self.world_map_cursor)
            return
        if sym in MOVE_KEYS:
            dx, dy = MOVE_KEYS[sym]
            cx = max(0, min(C.WORLD_CELLS_W - 1, self.world_map_cursor[0] + dx))
            cy = max(0, min(C.WORLD_CELLS_H - 1, self.world_map_cursor[1] + dy))
            self.world_map_cursor = (cx, cy)

    def _fast_travel_to(self, cell: tuple[int, int]) -> None:
        if cell not in self.discovered_cells:
            self.message_log.add("You haven't discovered that region yet.", color.INVALID)
            return
        if self._enemies_near_player():
            self.message_log.add("Not while enemies are near.", color.INVALID)
            return
        cur_cell = (self.location.zx // C.ZONES_PER_CELL, self.location.zy // C.ZONES_PER_CELL)
        if cell == cur_cell:
            self.state = GameState.PLAYER_TURN
            return

        # Representative zone of the target cell: its town zone if one sits in the
        # cell, otherwise the cell's center zone.
        dest_zx = dest_zy = None
        for (tzx, tzy) in self.surface_towns:
            if (tzx // C.ZONES_PER_CELL, tzy // C.ZONES_PER_CELL) == cell:
                dest_zx, dest_zy = tzx, tzy
                break
        if dest_zx is None:
            dest_zx = cell[0] * C.ZONES_PER_CELL + C.ZONES_PER_CELL // 2
            dest_zy = cell[1] * C.ZONES_PER_CELL + C.ZONES_PER_CELL // 2

        if self._is_town_zone(self.location):
            self.floors[self.location].last_active_calendar = to_calendar_minutes(self.clock.total_minutes)

        distance = max(abs(cell[0] - cur_cell[0]), abs(cell[1] - cur_cell[1]))
        cost = distance * C.ZONE_CROSS_HOURS * MINUTES_PER_HOUR * DAY_STRETCH

        self.world.delete_entity(self.player)
        self.world.flush_dead()
        self._enter_floor(self._surface_location_at(dest_zx, dest_zy))
        # A big schedule jump instead of one action — the normal enemy turn then
        # advances the clock by `cost`, so day/night, town catch-up, and faction
        # projection all fall out of the standard path.
        self.world.get(self.player, Speed).next_turn = self.clock.total_minutes + cost
        self.message_log.add("You travel across the land.", color.DESCEND)
        self.state = GameState.ENEMY_TURN

    # ------------------------------------------------------------------
    def _handle_inventory_event(self, event: tcod.event.Event, drop: bool) -> None:
        if not isinstance(event, tcod.event.KeyDown):
            return
        if event.sym == tcod.event.KeySym.ESCAPE:
            self.state = GameState.PLAYER_TURN
            return
        inv = self.world.get(self.player, Inventory)
        idx = event.sym - tcod.event.KeySym.A
        if 0 <= idx < len(inv.items):
            if drop:
                self._drop_item(inv.items[idx])
            else:
                self._use_item(inv.items[idx])

    def _use_item(self, item_id: int) -> None:
        item = self.inventory_world.get(item_id, Item)
        name = self.inventory_world.get(item_id, Name)
        if item and item.use_function:
            success = item.use_function(
                self.world, self.player, None, self.game_map, self.message_log
            )
            if success and self.inventory_world.has(item_id, Consumable):
                inv = self.world.get(self.player, Inventory)
                inv.items.remove(item_id)
                self.inventory_world.delete_entity(item_id)
                self.inventory_world.flush_dead()
            self._check_level_up()
        else:
            self.message_log.add(
                f"You can't use the {name.name if name else 'item'}.", color.INVALID
            )
        if self.state not in (GameState.LEVEL_UP,):
            self._spend_player_turn()
            self.state = GameState.ENEMY_TURN

    def _drop_item(self, item_id: int) -> None:
        pos = self.world.get(self.player, Position)
        inv = self.world.get(self.player, Inventory)
        name = self.inventory_world.get(item_id, Name)
        inv.items.remove(item_id)
        new_id = self._move_entity(self.inventory_world, self.world, item_id)
        self.world.add_component(new_id, Position(pos.x, pos.y))
        self.message_log.add(f"You drop the {name.name if name else 'item'}.", color.WHITE)
        self._spend_player_turn()
        self.state = GameState.ENEMY_TURN

    # ------------------------------------------------------------------
    def _active_locations(self) -> list[Location]:
        """Every Location whose FloorState gets ticked this turn.

        The current floor is always active, plus a window of *already-visited*
        nearby floors — the dungeon depth window (1D, along depth) or the
        surface zone window (2D Chebyshev, along zx/zy). Floors the player has
        never reached are never eagerly generated just to keep them warm.
        """
        if self.location.kind == "dungeon":
            site, depth = self.location.site, self.location.depth
            return [
                loc for loc in self.floors
                if loc.kind == "dungeon" and loc.site == site
                and abs(loc.depth - depth) <= DEPTH_WINDOW_RADIUS
            ]
        if self.location.kind == "surface":
            zx, zy = self.location.zx, self.location.zy
            return [
                loc for loc in self.floors
                if loc.kind == "surface"
                and abs(loc.zx - zx) <= C.SURFACE_WINDOW_RADIUS
                and abs(loc.zy - zy) <= C.SURFACE_WINDOW_RADIUS
            ]
        return [self.location]

    def _do_enemy_turn(self) -> None:
        player_speed = self.world.get(self.player, Speed)
        target_time = player_speed.next_turn
        elapsed = target_time - self.clock.total_minutes

        new_day = self.clock.advance(elapsed)
        now_calendar = to_calendar_minutes(self.clock.total_minutes)

        for location in self._active_locations():
            fs = self.floors[location]
            if self._is_town_zone(location):
                if new_day:
                    farm_system.on_new_day(fs.world, fs.game_map)
                # Drive needs off the town's own last-simulated stamp (kept up to
                # date here and by _catch_up_floor) rather than the raw player
                # elapsed — so a fast-travel arrival, already caught up on entry,
                # isn't double-counted.
                base = fs.last_active_calendar if fs.last_active_calendar is not None else now_calendar
                delta = now_calendar - base
                if delta > 0:
                    villager_system.update_needs(fs.world, delta)
                fs.last_active_calendar = now_calendar
            self._resolve_npc_turns_for(fs, target_time)

        self._transfer_boundary_factions()

        if new_day and self._is_town_zone(self.location):
            self.message_log.add(f"A new day dawns. {self.clock.date_string()}", color.MSG_STATUS)

        self.world.flush_dead()
        fighter = self.world.get(self.player, Fighter)
        if fighter and fighter.hp <= 0:
            self.state = GameState.PLAYER_DEAD
            if os.path.exists(C.SAVE_PATH):
                os.remove(C.SAVE_PATH)
        else:
            self.state = GameState.PLAYER_TURN

    def _transfer_boundary_factions(self) -> None:
        """Ferry any faction agent sitting on a zone edge into the neighbouring
        zone's World (mirrors the player's edge-walk). Collected first, applied
        after, so we don't mutate a World mid-iteration."""
        moves = []   # (src_fs, eid, dest_location, arrive_at, new_zone)
        for location in self._active_locations():
            if location.kind != "surface":
                continue
            fs = self.floors[location]
            w, h = fs.game_map.width, fs.game_map.height
            for eid, (pos, agent) in fs.world.query(Position, FactionAgent):
                nzx, nzy = agent.zone
                ax, ay = pos.x, pos.y
                if pos.x >= w - 1:   nzx += 1; ax = 0
                elif pos.x <= 0:     nzx -= 1; ax = w - 1
                elif pos.y >= h - 1: nzy += 1; ay = 0
                elif pos.y <= 0:     nzy -= 1; ay = h - 1
                else:                continue   # not on an edge
                if not (0 <= nzx < C.SURFACE_ZONES_W and 0 <= nzy < C.SURFACE_ZONES_H):
                    continue   # would leave the world — stay put
                moves.append((fs, eid, self._surface_location_at(nzx, nzy), (ax, ay), (nzx, nzy)))

        for src_fs, eid, dest_loc, arrive_at, new_zone in moves:
            if dest_loc not in self.floors:
                self.floors[dest_loc] = self._generate_floor(dest_loc)
            dest_fs = self.floors[dest_loc]
            new_eid = self._move_entity(src_fs.world, dest_fs.world, eid, drop_position=True)
            dest_fs.world.add_component(new_eid, Position(*arrive_at))
            agent = dest_fs.world.get(new_eid, FactionAgent)
            agent.zone = new_zone
            dest_fs.world.get(new_eid, Speed).next_turn = self.clock.total_minutes

    def _resolve_npc_turns_for(self, fs: FloorState, target_time: float) -> None:
        """Let every hostile/villager/faction agent on this floor act as many
        times as their Speed earns them, up to the moment the player is next
        ready to act (a Qud-style energy queue, expressed directly in
        game_clock minutes instead of an abstract energy pool).

        Called once per floor in _active_locations() — every floor outside
        that set is a separate World that simply isn't queried here, which is
        what keeps it frozen without any extra bookkeeping."""
        is_current = fs is self.floors[self.location]
        while True:
            eid = self._next_scheduled_npc(fs, target_time, is_current)
            if eid is None:
                return
            speed = fs.world.get(eid, Speed)
            # No player entity exists on a nearby-but-not-current floor (see
            # Engine._enter_floor) — hostiles there have nothing to chase.
            player = self.player if is_current else None

            for tag, act_one in _ACT_ONE_BY_TAG.items():
                if fs.world.has(eid, tag):
                    act_one(fs.world, fs.game_map, player, self.clock, self.message_log, eid)
                    break
            speed.next_turn += action_cost(speed.value)

    def _next_scheduled_npc(self, fs: FloorState, target_time: float, is_current: bool) -> int | None:
        best_eid, best_time = None, None
        for eid, (speed,) in fs.world.query(Speed):
            if is_current and eid == self.player:
                continue

            ai = fs.world.get(eid, AI)
            if ai is not None:
                if is_current:
                    # FOV only exists for the current floor (fov_system.update_fov
                    # is never called for the others) — on a nearby active-but-not-
                    # current floor, hostiles are simply always eligible to act.
                    pos = fs.world.get(eid, Position)
                    if not ai_system.is_active(fs.game_map, pos, ai):
                        # Frozen off-screen: stay synced to "now" instead of banking turns.
                        speed.next_turn = max(speed.next_turn, self.clock.total_minutes)
                        continue
            elif fs.world.has(eid, VillagerAI) or fs.world.has(eid, FactionAgent):
                # Villagers and faction agents are always eligible whenever their
                # zone is active; distance gating happens at the floor/zone level
                # (_active_locations), not per entity.
                pass
            else:
                continue   # not an entity kind the scheduler knows about

            if speed.next_turn <= target_time and (best_time is None or speed.next_turn < best_time):
                best_eid, best_time = eid, speed.next_turn
        return best_eid

    def _check_level_up(self) -> None:
        lvl = self.world.get(self.player, Level)
        if lvl and lvl.needs_level_up:
            self.state = GameState.LEVEL_UP

    def _handle_level_up_event(self, event: tcod.event.Event) -> None:
        if not isinstance(event, tcod.event.KeyDown):
            return
        fighter = self.world.get(self.player, Fighter)
        lvl = self.world.get(self.player, Level)
        if not fighter or not lvl:
            self.state = GameState.PLAYER_TURN
            return
        if event.sym == tcod.event.KeySym.A:
            fighter.max_hp += 20
            fighter.hp += 20
            self.message_log.add("Your health improves!", color.MSG_HEAL)
        elif event.sym == tcod.event.KeySym.B:
            fighter.power += 1
            self.message_log.add("Your attacks grow stronger!", color.MSG_LEVEL_UP)
        elif event.sym == tcod.event.KeySym.C:
            fighter.defense += 1
            self.message_log.add("Your defense hardens!", color.MSG_LEVEL_UP)
        else:
            return
        lvl.current_xp -= lvl.xp_to_next
        lvl.current_level += 1
        self.state = GameState.ENEMY_TURN

    # ------------------------------------------------------------------
    def save_game(self, path: str) -> None:
        with open(path, "wb") as f:
            pickle.dump(self, f)
        self.has_save_file = True

    @staticmethod
    def load_game(path: str) -> Engine:
        with open(path, "rb") as f:
            engine = pickle.load(f)
        engine._ensure_runtime_defaults()
        engine.has_save_file = True
        engine.state = GameState.OPENING
        return engine

    # ------------------------------------------------------------------
    def render(self, console: tcod.console.Console) -> None:
        if self.state == GameState.OPENING:
            render_opening_screen(console)
            return

        if self.state == GameState.HOME_MENU:
            render_home_menu(console, self._home_menu_items(), self.home_menu_index)
            return

        if self.state == GameState.WORLD_MAP:
            player_cell = (self.location.zx // C.ZONES_PER_CELL, self.location.zy // C.ZONES_PER_CELL)
            town_cells = {
                (zx // C.ZONES_PER_CELL, zy // C.ZONES_PER_CELL): site
                for (zx, zy), site in self.surface_towns.items()
            }
            render_world_map(console, player_cell, self.world_map_cursor, self.discovered_cells, town_cells)
            return

        render_all(
            console,
            self.world,
            self.game_map,
            self.player,
            self.message_log,
            self.location,
            self.clock,
            active_tileset=self.settings["active_tileset"],
            fallback_preset=self.settings["tileset_fallback_preset"],
            tile_scale=int(self.settings["tile_scale"]),
        )

        if self.state == GameState.TALKING and self.talking_to is not None:
            dialog = self.world.get(self.talking_to, Dialog)
            name = self.world.get(self.talking_to, Name)
            villager_ai = self.world.get(self.talking_to, VillagerAI)
            if dialog:
                render_dialog(
                    console,
                    speaker_name=name.name if name else "???",
                    lines=dialog.lines,
                    current_line=self.dialog_line,
                    activity=villager_ai.activity if villager_ai else None,
                )
        elif self.state == GameState.SHOW_INVENTORY:
            render_inventory(console, self.world, self.inventory_world, self.player, "Select an item to use  (ESC to cancel)")
        elif self.state == GameState.DROP_INVENTORY:
            render_inventory(console, self.world, self.inventory_world, self.player, "Select an item to drop  (ESC to cancel)")
        elif self.state == GameState.LEVEL_UP:
            render_level_up(console, self.world, self.player)
        elif self.state == GameState.PAUSE_MENU:
            render_pause_menu(console, self._pause_menu_items(), self.pause_menu_index)
        elif self.state == GameState.OPTIONS_MENU:
            render_options_menu(console, self.settings, self.options_menu_index)
        elif self.state == GameState.CONTROLS_MENU:
            render_controls_menu(console, self.settings["control_scheme"])
        elif self.state == GameState.INGAME_MENU:
            render_ingame_menu(
                console,
                self.ingame_menu_index,
                self.ingame_sections,
                self.world,
                self.inventory_world,
                self.player,
                self.location,
                self.discovered_cells,
                self.active_quests,
            )
        elif self.state == GameState.PLAYER_DEAD:
            cx = C.SCREEN_WIDTH // 2
            cy = C.SCREEN_HEIGHT // 2
            console.print(x=cx - 4, y=cy,      string="YOU DIED",          fg=color.MSG_PLAYER_DIE)
            console.print(x=cx - 10, y=cy + 2, string="Press ESC to quit.", fg=color.WHITE)
