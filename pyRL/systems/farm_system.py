"""
Farming: till the soil, plant a seed, water it daily until it ripens.

A FarmPlot progresses UNTILLED -> TILLED -> PLANTED -> SPROUT -> GROWING -> RIPE.
Growth only advances once per day, and only if the plot was watered that day
(see on_new_day, called by the engine when GameClock.advance() rolls a new day).
"""
from __future__ import annotations
from typing import TYPE_CHECKING
import tiles as tile_types
import color
from components import Position, Renderable, FarmPlot

if TYPE_CHECKING:
    from world import World
    from game_map import GameMap
    from message_log import MessageLog

UNTILLED, TILLED, PLANTED, SPROUT, GROWING, RIPE = range(6)

_CROP_LOOK = {
    PLANTED: ".",
    SPROUT: ",",
    GROWING: '"',
    RIPE: "Y",
}
_CROP_COLOR = {
    PLANTED: color.CROP_SEED_FG,
    SPROUT: color.CROP_SPROUT_FG,
    GROWING: color.CROP_GROWING_FG,
    RIPE: color.CROP_RIPE_FG,
}

VERBS = {
    "till": "tills the soil",
    "plant": "plants a seed",
    "water": "waters the crop",
    "harvest": "harvests the ripe crop",
}


def till(world: World, game_map: GameMap, plot_id: int) -> bool:
    plot = world.get(plot_id, FarmPlot)
    pos = world.get(plot_id, Position)
    if plot is None or pos is None or plot.stage != UNTILLED:
        return False
    plot.stage = TILLED
    game_map.tiles[pos.y, pos.x] = tile_types.DIRT
    return True


def plant(world: World, plot_id: int) -> bool:
    plot = world.get(plot_id, FarmPlot)
    if plot is None or plot.stage != TILLED:
        return False
    plot.stage = PLANTED
    world.add_component(plot_id, Renderable(_CROP_LOOK[PLANTED], _CROP_COLOR[PLANTED], render_order=1))
    return True


def water(world: World, game_map: GameMap, plot_id: int) -> bool:
    plot = world.get(plot_id, FarmPlot)
    pos = world.get(plot_id, Position)
    if plot is None or pos is None or plot.stage < PLANTED or plot.watered_today:
        return False
    plot.watered_today = True
    game_map.tiles[pos.y, pos.x] = tile_types.DIRT_WET
    return True


def harvest(world: World, plot_id: int) -> bool:
    plot = world.get(plot_id, FarmPlot)
    if plot is None or plot.stage != RIPE:
        return False
    plot.stage = TILLED
    plot.watered_today = False
    world.remove_component(plot_id, Renderable)
    return True


def needs_attention(world: World, plot_id: int) -> bool:
    """True if there is a farm action available at this plot right now."""
    plot = world.get(plot_id, FarmPlot)
    if plot is None:
        return False
    if plot.stage in (UNTILLED, TILLED, RIPE):
        return True
    return plot.stage in (PLANTED, SPROUT, GROWING) and not plot.watered_today


def tend(world: World, game_map: GameMap, plot_id: int) -> str | None:
    """Perform whichever farm action is due at this plot. Returns the action name."""
    plot = world.get(plot_id, FarmPlot)
    if plot is None:
        return None
    if plot.stage == UNTILLED:
        till(world, game_map, plot_id)
        return "till"
    if plot.stage == RIPE:
        harvest(world, plot_id)
        return "harvest"
    if plot.stage == TILLED:
        plant(world, plot_id)
        return "plant"
    if not plot.watered_today:
        water(world, game_map, plot_id)
        return "water"
    return None


def on_new_day(world: World, game_map: GameMap) -> None:
    """Advance watered crops one growth stage, then reset the day's watering."""
    for plot_id, (plot, pos) in list(world.query(FarmPlot, Position)):
        if plot.stage in (PLANTED, SPROUT, GROWING) and plot.watered_today:
            plot.stage += 1
            rend = world.get(plot_id, Renderable)
            if rend:
                rend.char = _CROP_LOOK[plot.stage]
                rend.fg = _CROP_COLOR[plot.stage]
        plot.watered_today = False
        if plot.stage >= TILLED:
            game_map.tiles[pos.y, pos.x] = tile_types.DIRT
