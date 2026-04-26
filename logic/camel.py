"""
camel.py
--------
Defines the Camel entity and its stacking semantics.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional

from utils.constants import CAMEL_HEX_COLORS, START_POSITION


@dataclass
class Camel:
    """
    Represents a single camel on the race track.

    Attributes:
        color:      Unique color identifier.
        position:   Current board space (1-16; 0 = not yet on track).
        stack_order: Vertical order within a space (0 = bottom, higher = top).
        is_crazy:   True for the White camel (moves in reverse in some variants).
    """

    color: str
    position: int = START_POSITION
    stack_order: int = 0
    is_crazy: bool = False

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def hex_color(self) -> str:
        """Return the hex colour string for GUI rendering."""
        return CAMEL_HEX_COLORS.get(self.color, "#AAAAAA")

    @property
    def on_track(self) -> bool:
        """True when the camel has moved at least once."""
        return self.position > START_POSITION

    # ── Representation ────────────────────────────────────────────────────────

    def __repr__(self) -> str:
        return (
            f"Camel(color={self.color!r}, pos={self.position}, "
            f"stack={self.stack_order})"
        )

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Camel):
            return self.color == other.color
        return NotImplemented

    def __hash__(self) -> int:
        return hash(self.color)