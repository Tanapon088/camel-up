"""
player.py
---------
Defines the Player entity, their hand of betting tokens, and coin balance.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Dict

from utils.constants import CAMEL_COLORS


@dataclass
class LegBetToken:
    """
    A single leg-bet token placed by a player.

    Attributes:
        camel_color: The camel the player is betting will lead this leg.
        payout_value: The payout this token promises if correct.
    """

    camel_color: str
    payout_value: int


@dataclass
class OverallBetToken:
    """
    An overall-race bet (Winner or Loser) placed by a player.

    Attributes:
        camel_color: Camel bet on as overall winner or loser.
        bet_type: 'winner' or 'loser'.
        order_placed: 1-based position (first to bet gets highest payout).
    """

    camel_color: str
    bet_type: str        # 'winner' | 'loser'
    order_placed: int


class Player:
    """
    Represents a human player in Camel Up.

    Each player starts with 3 coins and can:
    - Place leg bets (using leg-bet tiles drawn from each camel's stack)
    - Place overall winner / loser bets (once per game per camel per type)
    - Place a desert tile on the track (once per leg)
    - Roll the pyramid die (earns 1 coin + move a camel)
    """

    STARTING_COINS = 3

    def __init__(self, name: str, player_id: int) -> None:
        self.name: str = name
        self.player_id: int = player_id
        self.coins: int = self.STARTING_COINS

        # Betting state
        self.leg_bets: List[LegBetToken] = []
        self.overall_bets: List[OverallBetToken] = []

        # Desert-tile tracking
        self.desert_tile_on_board: bool = False
        self.desert_tile_position: Optional[int] = None   # space number
        self.desert_tile_type: Optional[str] = None       # 'oasis' | 'mirage'

    # ── Coin management ───────────────────────────────────────────────────────

    def earn(self, amount: int, reason: str = "") -> None:
        """Add *amount* coins (may be negative for penalties)."""
        self.coins += amount

    def pay(self, amount: int) -> None:
        """Deduct *amount* coins (amount should be positive)."""
        self.coins -= amount

    # ── Betting actions ───────────────────────────────────────────────────────

    def place_leg_bet(self, token: LegBetToken) -> None:
        """Record a leg-bet token taken from the supply."""
        self.leg_bets.append(token)

    def place_overall_bet(self, token: OverallBetToken) -> None:
        """Record an overall (winner/loser) bet."""
        self.overall_bets.append(token)

    def clear_leg_bets(self) -> List[LegBetToken]:
        """Remove and return all leg-bet tokens (called after each leg resolves)."""
        bets, self.leg_bets = self.leg_bets, []
        return bets

    # ── Desert tile ───────────────────────────────────────────────────────────

    def place_desert_tile(self, position: int, tile_type: str) -> None:
        """
        Mark that this player placed their desert tile at *position*.

        Args:
            position:  Board space (2-15 are valid).
            tile_type: 'oasis' or 'mirage'.
        """
        self.desert_tile_on_board = True
        self.desert_tile_position = position
        self.desert_tile_type = tile_type

    def retrieve_desert_tile(self) -> None:
        """Called at the start of a new leg to return the tile to the player."""
        self.desert_tile_on_board = False
        self.desert_tile_position = None
        self.desert_tile_type = None

    # ── Representation ────────────────────────────────────────────────────────

    def __repr__(self) -> str:
        return f"Player(name={self.name!r}, coins={self.coins})"

    def to_dict(self) -> Dict:
        """Serialise player state for persistence."""
        return {
            "name": self.name,
            "player_id": self.player_id,
            "coins": self.coins,
        }