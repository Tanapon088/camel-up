"""
board.py
--------
Manages the physical race track, camel positions/stacks, and desert tiles.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Optional, Tuple

from logic.camel import Camel
from utils.constants import (
    TRACK_LENGTH,
    CAMEL_COLORS,
    OASIS_EFFECT,
    MIRAGE_EFFECT,
    START_POSITION,
)


class Board:
    """
    The Camel Up race track (spaces 1–16).

    Internally, each space holds an *ordered list* of camels,
    index 0 = bottom of stack, last index = top.

    Desert tiles are stored in a dict: {space: ('oasis'|'mirage', player_id)}
    """

    def __init__(self) -> None:
        # {space_number: [Camel, ...]} ordered bottom→top
        self.spaces: Dict[int, List[Camel]] = defaultdict(list)

        # All camels keyed by colour
        self.camels: Dict[str, Camel] = {
            color: Camel(color=color) for color in CAMEL_COLORS
        }

        # {space_number: (tile_type, player_id)}
        self.desert_tiles: Dict[int, Tuple[str, int]] = {}

        # Pre-place camels randomly on spaces 1-3 (standard Camel Up setup)
        self._setup_camels()

    # ── Setup ─────────────────────────────────────────────────────────────────

    def _setup_camels(self) -> None:
        """Place each camel on a starting space (1, 2, or 3) at random."""
        import random
        for camel in self.camels.values():
            start = random.randint(1, 3)
            camel.position = start
            camel.stack_order = len(self.spaces[start])
            self.spaces[start].append(camel)

    # ── Stack helpers ─────────────────────────────────────────────────────────

    def stack_at(self, space: int) -> List[Camel]:
        """Return the ordered camel stack at *space* (bottom → top)."""
        return self.spaces.get(space, [])

    def top_camel(self, space: int) -> Optional[Camel]:
        """Return the camel on top of the stack at *space*, or None."""
        stack = self.stack_at(space)
        return stack[-1] if stack else None

    def leading_camel(self) -> Optional[Camel]:
        """Return the camel currently in first place (furthest + highest)."""
        for space in range(TRACK_LENGTH, 0, -1):
            stack = self.stack_at(space)
            if stack:
                return stack[-1]
        return None

    def camel_ranking(self) -> List[Camel]:
        """
        Return all camels ordered 1st → last.
        Within a space the camel higher in the stack ranks better.
        """
        ranked: List[Camel] = []
        for space in range(TRACK_LENGTH, 0, -1):
            ranked.extend(reversed(self.stack_at(space)))  # top→bottom per space
        # Add any camels still at position 0 (not yet on track) at the end
        on_track = {c.color for c in ranked}
        for color, camel in self.camels.items():
            if color not in on_track:
                ranked.append(camel)
        return ranked

    # ── Movement ─────────────────────────────────────────────────────────────

    def move_camel(self, color: str, steps: int) -> Optional[int]:
        """
        Move a camel and every camel above it by *steps* spaces forward.

        Desert-tile effects are applied when landing.

        Args:
            color:  The camel colour to move.
            steps:  Number of spaces to advance (1–3).

        Returns:
            The space the moved camel landed on, or None if already finished.
        """
        camel = self.camels[color]
        current_space = camel.position
        stack = self.spaces[current_space]

        # Collect this camel and everything above it
        try:
            idx = stack.index(camel)
        except ValueError:
            idx = 0
        moving_group: List[Camel] = stack[idx:]

        # Remove them from current space
        self.spaces[current_space] = stack[:idx]
        self._refresh_stack_orders(current_space)

        # Calculate destination
        destination = current_space + steps

        # --- Desert-tile check ---
        extra_steps, tile_bottom = self._apply_desert_tile(destination)
        destination += extra_steps

        # Clamp to track end (game ends, landing past 16 still counts)
        destination = min(destination, TRACK_LENGTH)

        # Place moving group at destination
        dest_stack = self.spaces[destination]
        if tile_bottom:
            # Mirage: insert below existing stack
            insert_pos = 0
            dest_stack[insert_pos:insert_pos] = moving_group
        else:
            # Normal / Oasis: append on top
            dest_stack.extend(moving_group)

        # Update camel objects
        for c in moving_group:
            c.position = destination
        self._refresh_stack_orders(destination)

        return destination

    def _apply_desert_tile(self, space: int) -> Tuple[int, bool]:
        """
        Check for a desert tile at *space*.

        Returns:
            (extra_steps, place_at_bottom)
            extra_steps: +1 (oasis), -1 (mirage), or 0
            place_at_bottom: True when the camel should go to the bottom
        """
        tile = self.desert_tiles.get(space)
        if tile is None:
            return 0, False
        tile_type, _owner = tile
        if tile_type == "oasis":
            return OASIS_EFFECT, False   # top of new stack
        else:  # mirage
            return MIRAGE_EFFECT, True  # bottom of stack

    def _refresh_stack_orders(self, space: int) -> None:
        """Synchronise stack_order attributes for every camel at *space*."""
        for i, camel in enumerate(self.spaces[space]):
            camel.stack_order = i

    # ── Desert tile placement ─────────────────────────────────────────────────

    def place_desert_tile(
        self, space: int, tile_type: str, player_id: int
    ) -> None:
        """
        Place a desert tile on the board.

        Args:
            space:     Target space (must be 2–15, not occupied, not adjacent).
            tile_type: 'oasis' or 'mirage'.
            player_id: ID of the owning player.

        Raises:
            ValueError: If placement is invalid.
        """
        self._validate_tile_placement(space, player_id)
        self.desert_tiles[space] = (tile_type, player_id)

    def remove_desert_tile(self, player_id: int) -> None:
        """Remove any desert tile belonging to *player_id*."""
        self.desert_tiles = {
            sp: t for sp, t in self.desert_tiles.items() if t[1] != player_id
        }

    def _validate_tile_placement(self, space: int, player_id: int) -> None:
        """Raise ValueError if the proposed tile placement breaks the rules."""
        if not (2 <= space <= TRACK_LENGTH - 1):
            raise ValueError(f"Desert tiles can only be placed on spaces 2–{TRACK_LENGTH - 1}.")
        if space in self.desert_tiles:
            raise ValueError(f"Space {space} already has a desert tile.")
        # Adjacent tile check
        if (space - 1) in self.desert_tiles or (space + 1) in self.desert_tiles:
            raise ValueError("Desert tiles cannot be placed adjacent to another tile.")
        # Cannot place on occupied space
        if self.spaces.get(space):
            raise ValueError(f"Space {space} is occupied by camels.")

    # ── Win detection ─────────────────────────────────────────────────────────

    def is_game_over(self) -> bool:
        """Return True if any camel has reached or passed space 16."""
        return any(
            c.position >= TRACK_LENGTH for c in self.camels.values()
        )

    # ── Representation ────────────────────────────────────────────────────────

    def __repr__(self) -> str:
        lines = ["Board state:"]
        for sp in range(1, TRACK_LENGTH + 1):
            stack = self.stack_at(sp)
            if stack:
                names = [c.color for c in stack]
                tile = self.desert_tiles.get(sp)
                tile_str = f" [{tile[0]}]" if tile else ""
                lines.append(f"  Space {sp:2d}: {names}{tile_str}")
        return "\n".join(lines)