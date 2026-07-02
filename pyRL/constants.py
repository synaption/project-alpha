SCREEN_WIDTH = 80
SCREEN_HEIGHT = 50

MAP_WIDTH = 80
MAP_HEIGHT = 43

PANEL_HEIGHT = 7
PANEL_Y = SCREEN_HEIGHT - PANEL_HEIGHT

BAR_WIDTH = 20
MSG_X = BAR_WIDTH + 2
MSG_WIDTH = SCREEN_WIDTH - BAR_WIDTH - 2
MSG_HEIGHT = PANEL_HEIGHT

MAX_ROOMS = 30
ROOM_MIN_SIZE = 6
ROOM_MAX_SIZE = 10

FOV_RADIUS = 8

# ── overworld / surface ────────────────────────────────────────────────────
# The surface is a bounded grid of walkable zone-screens. Each world-map cell
# (the coarse map you fast-travel on) expands into a ZONES_PER_CELL square block
# of zones — Caves of Qud's "parasang" model. Absolute zone coords run
# 0..WORLD_CELLS_*·ZONES_PER_CELL-1; world cell = zone // ZONES_PER_CELL.
WORLD_CELLS_W = 8
WORLD_CELLS_H = 8
ZONES_PER_CELL = 3
SURFACE_ZONES_W = WORLD_CELLS_W * ZONES_PER_CELL   # 24
SURFACE_ZONES_H = WORLD_CELLS_H * ZONES_PER_CELL
SURFACE_WINDOW_RADIUS = 1   # surface zones within this Chebyshev radius stay actively simulated
ZONE_CROSS_HOURS = 6        # calendar-hours of game-time to fast-travel across one world cell
                            # (converted to economy-minutes via game_clock.DAY_STRETCH in the engine)

FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
TILE_SIZE = 16

SAVE_PATH = "savegame.dat"
