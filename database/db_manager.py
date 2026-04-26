"""
db_manager.py
-------------
SQLite-backed persistence for game history, player statistics, and Hall of Fame.
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional

from utils.constants import DB_PATH

logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Manages all database interactions for Camel Up.

    Tables:
    - games         : One row per completed game.
    - player_stats  : Cumulative stats per player name.
    - game_events   : Event-log rows linked to a game.
    """

    SCHEMA = """
    CREATE TABLE IF NOT EXISTS games (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        played_at   TEXT    NOT NULL,
        winner_name TEXT    NOT NULL,
        players     TEXT    NOT NULL,   -- JSON list of {name, coins}
        leg_count   INTEGER NOT NULL
    );

    CREATE TABLE IF NOT EXISTS player_stats (
        player_name     TEXT PRIMARY KEY,
        games_played    INTEGER DEFAULT 0,
        games_won       INTEGER DEFAULT 0,
        total_coins     INTEGER DEFAULT 0,
        best_score      INTEGER DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS game_events (
        id      INTEGER PRIMARY KEY AUTOINCREMENT,
        game_id INTEGER NOT NULL REFERENCES games(id),
        event   TEXT    NOT NULL
    );
    """

    def __init__(self, db_path: str = DB_PATH) -> None:
        self.db_path = db_path
        self._ensure_directory()
        self._connection: Optional[sqlite3.Connection] = None
        self._initialise()

    # ── Connection management ─────────────────────────────────────────────────

    def _ensure_directory(self) -> None:
        """Create the database directory if it doesn't exist."""
        directory = os.path.dirname(self.db_path)
        if directory:
            os.makedirs(directory, exist_ok=True)

    def _connect(self) -> sqlite3.Connection:
        """Return a database connection, creating one if needed."""
        if self._connection is None:
            self._connection = sqlite3.connect(self.db_path)
            self._connection.row_factory = sqlite3.Row
        return self._connection

    def _initialise(self) -> None:
        """Create tables if they don't already exist."""
        try:
            conn = self._connect()
            conn.executescript(self.SCHEMA)
            conn.commit()
            logger.info("Database initialised at %s", self.db_path)
        except sqlite3.Error as exc:
            logger.error("Failed to initialise database: %s", exc)
            raise

    def close(self) -> None:
        """Close the database connection."""
        if self._connection:
            self._connection.close()
            self._connection = None

    # ── Write operations ──────────────────────────────────────────────────────

    def save_game(
        self,
        players_result: List[Dict],
        leg_count: int,
        event_log: List[str],
    ) -> int:
        """
        Persist a completed game and update player statistics.

        Args:
            players_result: List of {name, coins} dicts, sorted by coin count desc.
            leg_count:      Number of legs played.
            event_log:      Full event log from GameEngine.

        Returns:
            The new game's database ID.
        """
        try:
            conn = self._connect()
            winner = players_result[0]["name"]
            played_at = datetime.utcnow().isoformat()

            cursor = conn.execute(
                "INSERT INTO games (played_at, winner_name, players, leg_count) "
                "VALUES (?, ?, ?, ?)",
                (played_at, winner, json.dumps(players_result), leg_count),
            )
            game_id = cursor.lastrowid

            # Store event log
            conn.executemany(
                "INSERT INTO game_events (game_id, event) VALUES (?, ?)",
                [(game_id, e) for e in event_log],
            )

            # Update player statistics
            for result in players_result:
                self._upsert_player_stats(conn, result, winner)

            conn.commit()
            logger.info("Game #%d saved. Winner: %s", game_id, winner)
            return game_id

        except sqlite3.Error as exc:
            logger.error("Failed to save game: %s", exc)
            raise

    def _upsert_player_stats(
        self,
        conn: sqlite3.Connection,
        result: Dict,
        winner_name: str,
    ) -> None:
        """Insert or update cumulative stats for one player."""
        name = result["name"]
        coins = result["coins"]
        won = 1 if name == winner_name else 0

        conn.execute(
            """
            INSERT INTO player_stats (player_name, games_played, games_won,
                                      total_coins, best_score)
            VALUES (?, 1, ?, ?, ?)
            ON CONFLICT(player_name) DO UPDATE SET
                games_played = games_played + 1,
                games_won    = games_won    + excluded.games_won,
                total_coins  = total_coins  + excluded.total_coins,
                best_score   = MAX(best_score, excluded.best_score)
            """,
            (name, won, coins, coins),
        )

    # ── Read operations ───────────────────────────────────────────────────────

    def get_hall_of_fame(self, limit: int = 10) -> List[Dict]:
        """
        Return the top players by games won, then by best score.

        Args:
            limit: Maximum number of rows to return.

        Returns:
            List of dicts with keys: player_name, games_played, games_won,
            total_coins, best_score, win_rate.
        """
        try:
            conn = self._connect()
            rows = conn.execute(
                """
                SELECT player_name, games_played, games_won,
                       total_coins, best_score,
                       ROUND(100.0 * games_won / games_played, 1) AS win_rate
                FROM   player_stats
                ORDER  BY games_won DESC, best_score DESC
                LIMIT  ?
                """,
                (limit,),
            ).fetchall()
            return [dict(row) for row in rows]
        except sqlite3.Error as exc:
            logger.error("Failed to fetch Hall of Fame: %s", exc)
            return []

    def get_recent_games(self, limit: int = 10) -> List[Dict]:
        """Return the most recent completed games."""
        try:
            conn = self._connect()
            rows = conn.execute(
                "SELECT id, played_at, winner_name, leg_count "
                "FROM games ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [dict(row) for row in rows]
        except sqlite3.Error as exc:
            logger.error("Failed to fetch recent games: %s", exc)
            return []

    def get_game_events(self, game_id: int) -> List[str]:
        """Return the event log for a specific game."""
        try:
            conn = self._connect()
            rows = conn.execute(
                "SELECT event FROM game_events WHERE game_id = ? ORDER BY id",
                (game_id,),
            ).fetchall()
            return [row["event"] for row in rows]
        except sqlite3.Error as exc:
            logger.error("Failed to fetch game events: %s", exc)
            return []

    def get_player_stats(self, player_name: str) -> Optional[Dict]:
        """Return stats for a specific player, or None if not found."""
        try:
            conn = self._connect()
            row = conn.execute(
                "SELECT * FROM player_stats WHERE player_name = ?",
                (player_name,),
            ).fetchone()
            return dict(row) if row else None
        except sqlite3.Error as exc:
            logger.error("Failed to fetch player stats: %s", exc)
            return None