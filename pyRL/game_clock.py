"""
The Reckoning — Thornveil's calendar.

Named deliberately to avoid shadowing the stdlib `calendar` module.
Time only passes when the player acts, per the Berlin-interpretation rule.

Two independent knobs govern pacing, kept deliberately separate:
- TURN_MINUTES / action_cost() — the action-economy cost of a standard action at
  Speed 100. This drives the turn *scheduler* (Speed.next_turn in engine.py) and is
  the only thing Speed affects: a faster actor pays fewer economy-minutes per action,
  so it gets scheduled more often, regardless of how long a calendar day is.
- DAY_STRETCH — how many economy-minutes make up one calendar minute. This is the
  knob for "how long is a day/night cycle", and doesn't touch action costs at all.
  Raising it means everyone (any Speed) needs proportionally more of their own turns
  to get through one calendar day — but the *ratio* of turns-per-day between a fast
  and a slow actor is untouched, since that ratio comes only from Speed/action_cost.
"""
from __future__ import annotations

TURN_MINUTES = 10     # action-economy cost of a standard action for a Speed-100 actor
DAY_STRETCH = 240     # economy-minutes per calendar-minute; the day/night cycle's length

MINUTES_PER_HOUR = 60
HOURS_PER_DAY = 24
MINUTES_PER_DAY = MINUTES_PER_HOUR * HOURS_PER_DAY

# Four "tides" stand in for seasons/months — 30 days each.
TIDES = ["Thaw", "Sunhigh", "Harvest", "Frostveil"]
DAYS_PER_TIDE = 30
TIDES_PER_YEAR = len(TIDES)
DAYS_PER_YEAR = DAYS_PER_TIDE * TIDES_PER_YEAR

WEEKDAYS = ["Emberday", "Stoneday", "Wellday", "Marketday", "Huntday", "Restday", "Duskday"]

# Thornveil was built over the ruins "centuries ago" (Elder Maren) — start deep into the era.
EPOCH_YEAR = 214

DAWN_HOUR = 6
DUSK_HOUR = 20
NIGHT_MIN_LIGHT = 0.25

_ORDINAL_SUFFIXES = {1: "st", 2: "nd", 3: "rd"}


def action_cost(speed: int) -> float:
    """Economy-minutes a standard action costs at the given Speed (100 = baseline).

    A Speed-200 actor pays half the economy-minutes per action of a Speed-100 actor,
    so it gets scheduled roughly twice as often — see engine.Engine._resolve_npc_turns.
    Independent of DAY_STRETCH: Speed's effect on turn frequency never changes just
    because the day/night cycle is stretched longer or shorter.
    """
    return TURN_MINUTES * 100 / max(1, speed)


def to_calendar_minutes(economy_minutes: float) -> float:
    """Convert action-economy time (as tracked by Speed.next_turn) into calendar time."""
    return economy_minutes / DAY_STRETCH


def _ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = _ORDINAL_SUFFIXES.get(n % 10, "th")
    return f"{n}{suffix}"


class GameClock:
    def __init__(self) -> None:
        # total_minutes is the master scheduling clock, in economy-minutes (same unit
        # as Speed.next_turn) — NOT calendar minutes. Calendar properties below convert
        # via DAY_STRETCH. Start at dawn on day 0.
        self.total_minutes = DAWN_HOUR * MINUTES_PER_HOUR * DAY_STRETCH

    def advance(self, minutes: float = TURN_MINUTES) -> bool:
        """Advance the clock by economy-minutes. Returns True if a new day just began."""
        prev_day = self.day_count
        self.total_minutes += minutes
        return self.day_count != prev_day

    @property
    def _calendar_minutes(self) -> float:
        return to_calendar_minutes(self.total_minutes)

    @property
    def day_count(self) -> int:
        return int(self._calendar_minutes // MINUTES_PER_DAY)

    @property
    def hour(self) -> int:
        return int((self._calendar_minutes // MINUTES_PER_HOUR) % HOURS_PER_DAY)

    @property
    def minute(self) -> int:
        return int(self._calendar_minutes % MINUTES_PER_HOUR)

    @property
    def day_of_tide(self) -> int:
        return (self.day_count % DAYS_PER_TIDE) + 1

    @property
    def tide(self) -> str:
        return TIDES[(self.day_count // DAYS_PER_TIDE) % TIDES_PER_YEAR]

    @property
    def year(self) -> int:
        return EPOCH_YEAR + self.day_count // DAYS_PER_YEAR

    @property
    def weekday(self) -> str:
        return WEEKDAYS[self.day_count % len(WEEKDAYS)]

    @property
    def is_night(self) -> bool:
        return self.hour < DAWN_HOUR or self.hour >= DUSK_HOUR

    def light_level(self) -> float:
        """0.25 (deep night) .. 1.0 (full day), with 1-hour dawn/dusk ramps."""
        h = self.hour + self.minute / MINUTES_PER_HOUR
        if h < DAWN_HOUR - 1 or h >= DUSK_HOUR + 1:
            return NIGHT_MIN_LIGHT
        if h < DAWN_HOUR:
            t = h - (DAWN_HOUR - 1)
        elif h > DUSK_HOUR:
            t = 1.0 - (h - DUSK_HOUR)
        else:
            return 1.0
        return NIGHT_MIN_LIGHT + (1.0 - NIGHT_MIN_LIGHT) * t

    def time_string(self) -> str:
        return f"{self.hour:02d}:{self.minute:02d}"

    def date_string(self) -> str:
        return (
            f"{self.weekday}, the {_ordinal(self.day_of_tide)} of {self.tide}, "
            f"Year {self.year} of the Reckoning"
        )
