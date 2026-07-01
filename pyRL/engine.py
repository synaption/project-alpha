from __future__ import annotations
from enum import Enum, auto
import tcod.event
import tcod.console
from world import World
from game_map import GameMap
from message_log import MessageLog
from components import Position, Fighter, Name, AI, Inventory, Item, Consumable, Level, Stairs, Friendly, Dialog
from systems.combat_system import attack
from systems.ai_system import run_ai
from systems.fov_system import update_fov
from systems.render_system import render_all, render_inventory, render_level_up, render_dialog
from entity_factories import spawn_player
from map_gen import generate_dungeon
from town_gen import generate_town
import color
import constants as C


class GameState(Enum):
    PLAYER_TURN = auto()
    ENEMY_TURN = auto()
    PLAYER_DEAD = auto()
    SHOW_INVENTORY = auto()
    DROP_INVENTORY = auto()
    LEVEL_UP = auto()
    TALKING = auto()


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


class Engine:
    def __init__(self) -> None:
        self.world = World()
        self.message_log = MessageLog()
        self.state = GameState.PLAYER_TURN
        self.floor = 0          # 0 = town, 1+ = dungeon
        self.game_map: GameMap | None = None

        self.talking_to: int | None = None
        self.dialog_line: int = 0

        self.player = spawn_player(self.world, 0, 0)
        self._new_floor()

        self.message_log.add(
            "You arrive in Thornveil. The dungeon entrance lies to the south.",
            color.MSG_WELCOME,
        )

    # ------------------------------------------------------------------
    def _new_floor(self) -> None:
        if self.floor == 0:
            self.game_map = generate_town(
                world=self.world,
                player=self.player,
                map_width=C.MAP_WIDTH,
                map_height=C.MAP_HEIGHT,
            )
        else:
            self.game_map = generate_dungeon(
                world=self.world,
                player=self.player,
                floor=self.floor,
                map_width=C.MAP_WIDTH,
                map_height=C.MAP_HEIGHT,
                max_rooms=C.MAX_ROOMS,
                room_min_size=C.ROOM_MIN_SIZE,
                room_max_size=C.ROOM_MAX_SIZE,
            )
        update_fov(self.world, self.game_map, self.player)

    # ------------------------------------------------------------------
    def handle_events(self, events: list) -> None:
        for event in events:
            if isinstance(event, tcod.event.Quit):
                raise SystemExit(0)

            if self.state == GameState.PLAYER_DEAD:
                if isinstance(event, tcod.event.KeyDown) and event.sym == tcod.event.KeySym.ESCAPE:
                    raise SystemExit(0)
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

            if self.state == GameState.PLAYER_TURN and isinstance(event, tcod.event.KeyDown):
                self._handle_player_key(event)

        if self.state == GameState.ENEMY_TURN:
            self._do_enemy_turn()

    # ------------------------------------------------------------------
    def _handle_player_key(self, event: tcod.event.KeyDown) -> None:
        pos = self.world.get(self.player, Position)
        sym = event.sym

        if sym == tcod.event.KeySym.ESCAPE:
            raise SystemExit(0)

        if sym == tcod.event.KeySym.I:
            self.state = GameState.SHOW_INVENTORY
            return

        if sym == tcod.event.KeySym.D:
            self.state = GameState.DROP_INVENTORY
            return

        if sym == tcod.event.KeySym.G:
            self._pickup()
            return

        if sym == tcod.event.KeySym.GREATER or (
            sym == tcod.event.KeySym.PERIOD and bool(event.mod & tcod.event.Modifier.SHIFT)
        ):
            self._descend(pos)
            return

        if sym == tcod.event.KeySym.SLASH and bool(event.mod & tcod.event.Modifier.SHIFT):
            self._show_help()
            return

        if sym in MOVE_KEYS:
            dx, dy = MOVE_KEYS[sym]
            if dx == 0 and dy == 0:
                self.state = GameState.ENEMY_TURN
                return
            self._move_or_attack(pos, dx, dy)

    def _move_or_attack(self, pos: Position, dx: int, dy: int) -> None:
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
        inv.items.append(item_id)
        self.world.remove_component(item_id, Position)
        self.message_log.add(f"You pick up the {name.name if name else 'item'}.", color.WHITE)
        self.state = GameState.ENEMY_TURN

    def _descend(self, pos: Position) -> None:
        stairs = self.game_map.get_stairs_at(pos.x, pos.y)
        if stairs is None:
            self.message_log.add("There are no stairs here.", color.INVALID)
            return
        stair_comp = self.world.get(stairs, Stairs)
        self.floor = stair_comp.floor if stair_comp else self.floor + 1
        if self.floor == 1:
            self.message_log.add("You descend into the dungeon. There's no going back.", color.DESCEND)
        else:
            self.message_log.add(f"You descend to dungeon level {self.floor}.", color.DESCEND)
        inv = self.world.get(self.player, Inventory)
        keep = {self.player} | set(inv.items if inv else [])
        for eid in list(self.world.entities):
            if eid not in keep:
                self.world.delete_entity(eid)
        self.world.flush_dead()
        self._new_floor()
        self.state = GameState.PLAYER_TURN

    def _show_help(self) -> None:
        self.message_log.add(
            "Arrows/hjklyubn=move  bump=talk/attack  g=get  i=inventory  d=drop  >=stairs  ESC=quit",
            color.WHITE,
        )

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
        item = self.world.get(item_id, Item)
        name = self.world.get(item_id, Name)
        if item and item.use_function:
            success = item.use_function(
                self.world, self.player, None, self.game_map, self.message_log
            )
            if success and self.world.has(item_id, Consumable):
                inv = self.world.get(self.player, Inventory)
                inv.items.remove(item_id)
                self.world.delete_entity(item_id)
                self.world.flush_dead()
            self._check_level_up()
        else:
            self.message_log.add(
                f"You can't use the {name.name if name else 'item'}.", color.INVALID
            )
        if self.state not in (GameState.LEVEL_UP,):
            self.state = GameState.ENEMY_TURN

    def _drop_item(self, item_id: int) -> None:
        pos = self.world.get(self.player, Position)
        inv = self.world.get(self.player, Inventory)
        name = self.world.get(item_id, Name)
        inv.items.remove(item_id)
        self.world.add_component(item_id, Position(pos.x, pos.y))
        self.message_log.add(f"You drop the {name.name if name else 'item'}.", color.WHITE)
        self.state = GameState.ENEMY_TURN

    # ------------------------------------------------------------------
    def _do_enemy_turn(self) -> None:
        run_ai(self.world, self.game_map, self.player, self.message_log)
        self.world.flush_dead()
        fighter = self.world.get(self.player, Fighter)
        if fighter and fighter.hp <= 0:
            self.state = GameState.PLAYER_DEAD
        else:
            self.state = GameState.PLAYER_TURN

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
    def render(self, console: tcod.console.Console) -> None:
        render_all(console, self.world, self.game_map, self.player, self.message_log, self.floor)

        if self.state == GameState.TALKING and self.talking_to is not None:
            dialog = self.world.get(self.talking_to, Dialog)
            name = self.world.get(self.talking_to, Name)
            if dialog:
                render_dialog(
                    console,
                    speaker_name=name.name if name else "???",
                    lines=dialog.lines,
                    current_line=self.dialog_line,
                )
        elif self.state == GameState.SHOW_INVENTORY:
            render_inventory(console, self.world, self.player, "Select an item to use  (ESC to cancel)")
        elif self.state == GameState.DROP_INVENTORY:
            render_inventory(console, self.world, self.player, "Select an item to drop  (ESC to cancel)")
        elif self.state == GameState.LEVEL_UP:
            render_level_up(console, self.world, self.player)
        elif self.state == GameState.PLAYER_DEAD:
            cx = C.SCREEN_WIDTH // 2
            cy = C.SCREEN_HEIGHT // 2
            console.print(x=cx - 4, y=cy,      string="YOU DIED",          fg=color.MSG_PLAYER_DIE)
            console.print(x=cx - 10, y=cy + 2, string="Press ESC to quit.", fg=color.WHITE)
