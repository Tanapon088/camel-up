"""
game_engine.py
--------------
Core game engine: orchestrates turns, betting, scoring, and leg/race resolution.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Tuple

from logic.board import Board
from logic.camel import Camel
from logic.player import LegBetToken, OverallBetToken, Player
from utils.constants import (
    CAMEL_COLORS,
    LEG_BET_PAYOUTS,
    WRONG_LEG_BET_PENALTY,
    OVERALL_BET_PAYOUTS,
    OVERALL_WRONG_PENALTY,
    SPECTATOR_CARD_PAYOUT,
    TRACK_LENGTH,
)
from utils.helpers import roll_pyramid

logger = logging.getLogger(__name__)


# ── Leg-bet tile supply ───────────────────────────────────────────────────────

class LegBetSupply:
    """
    Holds the leg-bet tile stacks for each camel.
    Each camel has tiles worth 5, 3, 2, 1, 1 coins (taken in order).
    """

    TILE_VALUES = [5, 3, 2, 1, 1]

    def __init__(self) -> None:
        self._stacks: Dict[str, List[int]] = {
            color: list(self.TILE_VALUES) for color in CAMEL_COLORS
        }

    def take_tile(self, color: str) -> Optional[int]:
        """
        Remove and return the top tile value for *color*.
        Returns None if the stack is exhausted.
        """
        stack = self._stacks.get(color, [])
        return stack.pop(0) if stack else None

    def reset(self) -> None:
        """Restore all tile stacks (called at the start of each new leg)."""
        self._stacks = {
            color: list(self.TILE_VALUES) for color in CAMEL_COLORS
        }

    def available_value(self, color: str) -> Optional[int]:
        """Peek at the next tile value without taking it."""
        stack = self._stacks.get(color, [])
        return stack[0] if stack else None


# ── Overall-bet order tracking ────────────────────────────────────────────────

class OverallBetTracker:
    """Tracks how many bets of each type have been placed per camel."""

    def __init__(self) -> None:
        self._counts: Dict[Tuple[str, str], int] = {}

    def record(self, color: str, bet_type: str) -> int:
        """Increment counter and return the new order_placed value."""
        key = (color, bet_type)
        self._counts[key] = self._counts.get(key, 0) + 1
        return self._counts[key]


# ── Main Game Engine ─────────────────────────────────────────────────────────

class GameEngine:
    """
    Orchestrates a complete game of Camel Up.

    Responsibilities:
    - Manage turns (roll, leg-bet, overall-bet, desert-tile).
    - Trigger leg-end and race-end scoring.
    - Expose state to the GUI layer.
    """

    class Phase:
        SETUP = "setup"
        PLAYER_TURN = "player_turn"
        LEG_SCORING = "leg_scoring"
        GAME_OVER = "game_over"

    def __init__(self, players: List[Player]) -> None:
        if not (2 <= len(players) <= 8):
            raise ValueError("Camel Up requires 2–8 players.")

        self.players: List[Player] = players
        self.board: Board = Board()
        self.leg_bet_supply: LegBetSupply = LegBetSupply()
        self.overall_tracker: OverallBetTracker = OverallBetTracker()

        self.current_player_index: int = 0
        self.leg_number: int = 1
        self.phase: str = self.Phase.PLAYER_TURN

        # Pyramid state: which colours haven't been rolled yet this leg
        self.pyramid_remaining: List[str] = list(CAMEL_COLORS)

        # Event log for GUI display
        self.event_log: List[str] = []

        # Winning & losing overall bets: {camel_color: [(player_id, order_placed)]}
        self.overall_winner_bets: Dict[str, List[Tuple[int, int]]] = {
            c: [] for c in CAMEL_COLORS
        }
        self.overall_loser_bets: Dict[str, List[Tuple[int, int]]] = {
            c: [] for c in CAMEL_COLORS
        }

        self._log(f"Game started with {len(players)} players. Leg 1 begins!")

    # ── Accessors ─────────────────────────────────────────────────────────────

    @property
    def current_player(self) -> Player:
        return self.players[self.current_player_index]

    @property
    def is_game_over(self) -> bool:
        return self.phase == self.Phase.GAME_OVER

    def get_ranking(self) -> List[Camel]:
        """Return camels ordered 1st → last."""
        return self.board.camel_ranking()

    def get_leader(self) -> Optional[Camel]:
        """Return the currently leading camel."""
        return self.board.leading_camel()

    # ── Player actions ────────────────────────────────────────────────────────

    def action_roll_pyramid(self) -> Tuple[str, int, int]:
        """
        Current player rolls the pyramid die.

        - Earns 1 coin.
        - Moves the drawn camel (and anything above it).
        - Ends the leg if all dice rolled.

        Returns:
            (color, value, landing_space)

        Raises:
            RuntimeError: If pyramid is already empty.
        """
        if not self.pyramid_remaining:
            raise RuntimeError("All dice have been rolled this leg.")

        color, value = roll_pyramid(self.pyramid_remaining)
        self.pyramid_remaining.remove(color)

        # Pay the roller
        self.current_player.earn(1, reason="pyramid roll")

        # Move camel on board
        landing_space = self.board.move_camel(color, value)

        # Pay any spectator-tile owners
        self._pay_spectator_tiles(landing_space)

        self._log(
            f"{self.current_player.name} rolled: {color.upper()} moves "
            f"{value} → space {landing_space}."
        )

        # Check leg end
        if not self.pyramid_remaining:
            self._resolve_leg()
        elif self.board.is_game_over():
            self._resolve_race()
        else:
            self._next_player()

        return color, value, landing_space

    def action_take_leg_bet(self, camel_color: str) -> LegBetToken:
        """
        Current player takes the next available leg-bet tile for *camel_color*.

        Returns:
            The LegBetToken taken.

        Raises:
            ValueError: If no tiles remain for that camel.
        """
        value = self.leg_bet_supply.take_tile(camel_color)
        if value is None:
            raise ValueError(f"No leg-bet tiles left for {camel_color}.")

        token = LegBetToken(camel_color=camel_color, payout_value=value)
        self.current_player.place_leg_bet(token)

        self._log(
            f"{self.current_player.name} bet on {camel_color.upper()} "
            f"this leg (tile worth {value})."
        )
        self._next_player()
        return token

    def action_place_overall_bet(self, camel_color: str, bet_type: str) -> OverallBetToken:
        """
        Current player places an overall winner or loser bet.

        Args:
            camel_color: Camel to bet on.
            bet_type:    'winner' or 'loser'.

        Returns:
            The OverallBetToken placed.

        Raises:
            ValueError: On invalid inputs.
        """
        if bet_type not in ("winner", "loser"):
            raise ValueError("bet_type must be 'winner' or 'loser'.")

        order = self.overall_tracker.record(camel_color, bet_type)
        token = OverallBetToken(
            camel_color=camel_color,
            bet_type=bet_type,
            order_placed=order,
        )
        self.current_player.place_overall_bet(token)

        # Store in engine tracker
        if bet_type == "winner":
            self.overall_winner_bets[camel_color].append(
                (self.current_player.player_id, order)
            )
        else:
            self.overall_loser_bets[camel_color].append(
                (self.current_player.player_id, order)
            )

        self._log(
            f"{self.current_player.name} placed overall {bet_type} bet on "
            f"{camel_color.upper()}."
        )
        self._next_player()
        return token

    def action_place_desert_tile(
        self, space: int, tile_type: str
    ) -> None:
        """
        Current player places their desert tile on *space*.

        Args:
            space:     Target board space.
            tile_type: 'oasis' or 'mirage'.

        Raises:
            ValueError: If the player already has a tile on the board,
                        or placement is invalid.
        """
        player = self.current_player
        if player.desert_tile_on_board:
            raise ValueError("You already have a desert tile on the board.")

        # Delegate validation to board
        self.board.place_desert_tile(space, tile_type, player.player_id)
        player.place_desert_tile(space, tile_type)

        self._log(
            f"{player.name} placed a {tile_type} tile on space {space}."
        )
        self._next_player()

    # ── Internal resolution ───────────────────────────────────────────────────

    def _resolve_leg(self) -> None:
        """Score the just-completed leg, then start the next leg."""
        self.phase = self.Phase.LEG_SCORING
        ranking = self.board.camel_ranking()
        leader = ranking[0]
        second = ranking[1] if len(ranking) > 1 else None

        self._log(
            f"── Leg {self.leg_number} ends! Leader: {leader.color.upper()} ──"
        )

        # Score each player's leg-bet tokens
        for player in self.players:
            for token in player.clear_leg_bets():
                if token.camel_color == leader.color:
                    player.earn(token.payout_value, "leg bet – winner")
                    self._log(
                        f"  {player.name} wins {token.payout_value} coins "
                        f"(leg bet on {token.camel_color.upper()})."
                    )
                elif second and token.camel_color == second.color:
                    player.earn(1, "leg bet – second")
                    self._log(
                        f"  {player.name} wins 1 coin "
                        f"(leg bet on {token.camel_color.upper()} – 2nd place)."
                    )
                else:
                    player.earn(WRONG_LEG_BET_PENALTY, "leg bet – wrong")
                    self._log(
                        f"  {player.name} loses 1 coin "
                        f"(wrong leg bet on {token.camel_color.upper()})."
                    )

        # Check for game end before starting new leg
        if self.board.is_game_over():
            self._resolve_race()
            return

        # Start new leg
        self.leg_number += 1
        self.pyramid_remaining = list(CAMEL_COLORS)
        self.leg_bet_supply.reset()

        # Return desert tiles to players
        for player in self.players:
            if player.desert_tile_on_board:
                self.board.remove_desert_tile(player.player_id)
                player.retrieve_desert_tile()

        self.phase = self.Phase.PLAYER_TURN
        self._log(f"── Leg {self.leg_number} begins! ──")
        self._next_player()

    def _resolve_race(self) -> None:
        """Score overall bets and declare the game winner."""
        self.phase = self.Phase.GAME_OVER
        ranking = self.board.camel_ranking()
        overall_winner = ranking[0]
        overall_loser = ranking[-1]

        self._log(
            f"═══ RACE OVER! ═══\n"
            f"  🥇 Winner: {overall_winner.color.upper()}\n"
            f"  🪦 Loser:  {overall_loser.color.upper()}"
        )

        # Score overall winner bets
        for player in self.players:
            for token in player.overall_bets:
                self._score_overall_token(
                    player, token, overall_winner.color, overall_loser.color
                )

        # Announce coin totals
        sorted_players = sorted(
            self.players, key=lambda p: p.coins, reverse=True
        )
        self._log("\n── Final Standings ──")
        for rank, p in enumerate(sorted_players, 1):
            self._log(f"  {rank}. {p.name}: {p.coins} coins")

    def _score_overall_token(
        self,
        player: Player,
        token: OverallBetToken,
        winner_color: str,
        loser_color: str,
    ) -> None:
        target = winner_color if token.bet_type == "winner" else loser_color
        correct = token.camel_color == target

        if correct:
            idx = min(token.order_placed - 1, len(OVERALL_BET_PAYOUTS) - 1)
            payout = OVERALL_BET_PAYOUTS[idx]
            player.earn(payout, f"overall {token.bet_type} bet – correct")
            self._log(
                f"  {player.name} wins {payout} coins "
                f"(overall {token.bet_type} bet on {token.camel_color.upper()})."
            )
        else:
            player.earn(OVERALL_WRONG_PENALTY, f"overall {token.bet_type} bet – wrong")
            self._log(
                f"  {player.name} loses 1 coin "
                f"(wrong overall {token.bet_type} bet on {token.camel_color.upper()})."
            )

    def _pay_spectator_tiles(self, landing_space: int) -> None:
        """If a camel lands on a desert tile, pay the tile's owner 1 coin."""
        tile = self.board.desert_tiles.get(landing_space)
        if tile is None:
            return
        _tile_type, owner_id = tile
        for player in self.players:
            if player.player_id == owner_id:
                player.earn(SPECTATOR_CARD_PAYOUT, "spectator tile")
                self._log(
                    f"  {player.name} earns 1 coin (desert tile on space "
                    f"{landing_space})."
                )
                break

    # ── Turn order ────────────────────────────────────────────────────────────

    def _next_player(self) -> None:
        """Advance to the next player in turn order."""
        self.current_player_index = (
            self.current_player_index + 1
        ) % len(self.players)

    # ── Logging ───────────────────────────────────────────────────────────────

    def _log(self, message: str) -> None:
        self.event_log.append(message)
        logger.info(message)

    # ── Serialisation ─────────────────────────────────────────────────────────

    def get_state_snapshot(self) -> dict:
        """Return a JSON-serialisable snapshot of the game state."""
        ranking = self.board.camel_ranking()
        return {
            "leg": self.leg_number,
            "phase": self.phase,
            "current_player": self.current_player.name,
            "pyramid_remaining": self.pyramid_remaining,
            "players": [
                {
                    "name": p.name,
                    "coins": p.coins,
                    "leg_bets": [
                        {"color": t.camel_color, "value": t.payout_value}
                        for t in p.leg_bets
                    ],
                }
                for p in self.players
            ],
            "camel_positions": {
                color: {"space": c.position, "stack_order": c.stack_order}
                for color, c in self.board.camels.items()
            },
            "ranking": [c.color for c in ranking],
            "desert_tiles": {
                str(sp): {"type": t, "owner": pid}
                for sp, (t, pid) in self.board.desert_tiles.items()
            },
        }