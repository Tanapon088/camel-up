"""
helpers.py
----------
Utility / helper functions used across the Camel Up application.
"""

from __future__ import annotations

import random
import logging
from typing import List

from utils.constants import DICE_VALUES, CAMEL_COLORS

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


# ── Dice helpers ──────────────────────────────────────────────────────────────

def roll_single_die() -> int:
    """Return a random result from [1, 2, 3]."""
    return random.choice(DICE_VALUES)


def roll_pyramid(remaining_colors: List[str]) -> tuple[str, int]:
    """
    Simulate pulling one die from the Camel Up pyramid.

    Args:
        remaining_colors: Colors whose dice are still in the pyramid.

    Returns:
        (color, value) tuple.

    Raises:
        ValueError: If no dice remain in the pyramid.
    """
    if not remaining_colors:
        raise ValueError("Pyramid is empty – all dice have been rolled this leg.")
    color = random.choice(remaining_colors)
    value = roll_single_die()
    logger.debug("Pyramid rolled: %s moves %d", color, value)
    return color, value


# ── Formatting helpers ────────────────────────────────────────────────────────

def coins_str(amount: int) -> str:
    """Format a coin amount with sign, e.g. '+3' or '-1'."""
    return f"+{amount}" if amount >= 0 else str(amount)


def ordinal(n: int) -> str:
    """Return the ordinal string for *n* (1→'1st', 2→'2nd', etc.)."""
    suffix = {1: "st", 2: "nd", 3: "rd"}
    return f"{n}{suffix.get(n if n < 20 else n % 10, 'th')}"


# ── Validation helpers ────────────────────────────────────────────────────────

def validate_player_name(name: str) -> str:
    """
    Strip and validate a player name.

    Raises:
        ValueError: If the name is empty or too long.
    """
    name = name.strip()
    if not name:
        raise ValueError("Player name cannot be empty.")
    if len(name) > 30:
        raise ValueError("Player name must be 30 characters or fewer.")
    return name


def validate_player_count(count: int) -> int:
    """
    Validate the number of players.

    Raises:
        ValueError: If count is outside [2, 8].
    """
    if not (2 <= count <= 8):
        raise ValueError("Camel Up supports 2–8 players.")
    return count