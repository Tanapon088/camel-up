"""
app.py
------
Main Tkinter GUI application for Camel Up! Digital Edition.

Layout (1280 × 800):
  ┌─────────────────────────────────────┬───────────────────┐
  │           RACE TRACK (canvas)       │   INFO PANEL      │
  │                                     │   • Scores        │
  │                                     │   • Pyramid       │
  │                                     │   • Current turn  │
  ├─────────────────────────────────────┤   • Leg bets      │
  │           ACTION BAR                │   • Event log     │
  └─────────────────────────────────────┴───────────────────┘
"""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
from typing import Dict, List, Optional

from database.db_manager import DatabaseManager
from logic.camel import Camel
from logic.game_engine import GameEngine
from logic.player import Player
from utils.constants import (
    ACCENT_COLOR,
    BACKGROUND_COLOR,
    BUTTON_COLOR,
    BUTTON_HOVER,
    CAMEL_COLORS,
    CAMEL_HEX_COLORS,
    PANEL_COLOR,
    TEXT_COLOR,
    TRACK_COLOR,
    TRACK_LENGTH,
    WINDOW_HEIGHT,
    WINDOW_TITLE,
    WINDOW_WIDTH,
)
from utils.helpers import validate_player_count, validate_player_name


# ── Colour helpers ────────────────────────────────────────────────────────────

def _darken(hex_color: str, factor: float = 0.7) -> str:
    """Darken a hex colour by *factor* (0–1)."""
    r = int(hex_color[1:3], 16)
    g = int(hex_color[3:5], 16)
    b = int(hex_color[5:7], 16)
    return f"#{int(r*factor):02x}{int(g*factor):02x}{int(b*factor):02x}"


# ── Styled button ─────────────────────────────────────────────────────────────

class StyledButton(tk.Button):
    """A flat, rounded-looking button matching the desert theme."""

    def __init__(self, parent, **kwargs) -> None:
        kwargs.setdefault("bg", BUTTON_COLOR)
        kwargs.setdefault("fg", TEXT_COLOR)
        kwargs.setdefault("activebackground", BUTTON_HOVER)
        kwargs.setdefault("activeforeground", TEXT_COLOR)
        kwargs.setdefault("relief", "flat")
        kwargs.setdefault("cursor", "hand2")
        kwargs.setdefault("font", ("Georgia", 10, "bold"))
        kwargs.setdefault("padx", 12)
        kwargs.setdefault("pady", 6)
        super().__init__(parent, **kwargs)
        self.bind("<Enter>", lambda _: self.config(bg=BUTTON_HOVER))
        self.bind("<Leave>", lambda _: self.config(bg=BUTTON_COLOR))


# ── Setup dialog ──────────────────────────────────────────────────────────────

class SetupDialog(tk.Toplevel):
    """Modal dialog to collect player names before the game starts."""

    def __init__(self, parent: tk.Tk) -> None:
        super().__init__(parent)
        self.title("Camel Up! – New Game Setup")
        self.configure(bg=BACKGROUND_COLOR)
        self.resizable(False, False)
        self.grab_set()

        self.players: List[str] = []
        self._entries: List[tk.Entry] = []

        self._build_ui()
        self.wait_window()

    def _build_ui(self) -> None:
        tk.Label(
            self, text="🐪 CAMEL UP!", font=("Georgia", 20, "bold"),
            bg=BACKGROUND_COLOR, fg=ACCENT_COLOR,
        ).pack(pady=(20, 4))

        tk.Label(
            self, text="Enter player names (2–8 players)",
            font=("Georgia", 11), bg=BACKGROUND_COLOR, fg=TEXT_COLOR,
        ).pack(pady=(0, 12))

        frame = tk.Frame(self, bg=BACKGROUND_COLOR)
        frame.pack(padx=30)

        self._name_vars: List[tk.StringVar] = []
        for i in range(8):
            row = tk.Frame(frame, bg=BACKGROUND_COLOR)
            row.pack(fill="x", pady=2)
            tk.Label(
                row, text=f"Player {i+1}:", width=10,
                bg=BACKGROUND_COLOR, fg=TEXT_COLOR,
                font=("Courier", 10),
            ).pack(side="left")
            var = tk.StringVar()
            self._name_vars.append(var)
            entry = tk.Entry(
                row, textvariable=var, width=22,
                bg=PANEL_COLOR, fg=TEXT_COLOR,
                insertbackground=TEXT_COLOR, relief="flat",
                font=("Courier", 10),
            )
            entry.pack(side="left", padx=4)
            self._entries.append(entry)

        # Pre-fill defaults
        for i, default in enumerate(["Alice", "Bob"]):
            self._name_vars[i].set(default)

        StyledButton(self, text="▶  Start Game", command=self._confirm).pack(
            pady=16
        )

    def _confirm(self) -> None:
        names = [v.get().strip() for v in self._name_vars if v.get().strip()]
        try:
            validate_player_count(len(names))
            for name in names:
                validate_player_name(name)
            # Check uniqueness
            if len(set(names)) != len(names):
                raise ValueError("All player names must be unique.")
        except ValueError as exc:
            messagebox.showerror("Invalid Input", str(exc), parent=self)
            return
        self.players = names
        self.destroy()


# ── Hall of Fame window ───────────────────────────────────────────────────────

class HallOfFameWindow(tk.Toplevel):
    """Displays the persistent leaderboard from the database."""

    def __init__(self, parent: tk.Tk, db: DatabaseManager) -> None:
        super().__init__(parent)
        self.title("🏆 Hall of Fame")
        self.configure(bg=BACKGROUND_COLOR)
        self.resizable(True, True)
        self.geometry("600x400")

        rows = db.get_hall_of_fame(limit=20)
        self._build_ui(rows)

    def _build_ui(self, rows: list) -> None:
        tk.Label(
            self, text="🏆  Hall of Fame",
            font=("Georgia", 16, "bold"),
            bg=BACKGROUND_COLOR, fg=ACCENT_COLOR,
        ).pack(pady=(16, 8))

        cols = ("Rank", "Player", "Wins", "Games", "Win %", "Best Score")
        tree = ttk.Treeview(self, columns=cols, show="headings", height=14)

        style = ttk.Style()
        style.configure("Treeview",
                        background=PANEL_COLOR,
                        foreground=TEXT_COLOR,
                        fieldbackground=PANEL_COLOR,
                        rowheight=24)
        style.configure("Treeview.Heading",
                        background=BUTTON_COLOR,
                        foreground=ACCENT_COLOR,
                        font=("Georgia", 9, "bold"))

        widths = [50, 160, 60, 60, 70, 90]
        for col, w in zip(cols, widths):
            tree.heading(col, text=col)
            tree.column(col, width=w, anchor="center")

        for rank, row in enumerate(rows, 1):
            tree.insert("", "end", values=(
                rank,
                row["player_name"],
                row["games_won"],
                row["games_played"],
                f"{row['win_rate']}%",
                row["best_score"],
            ))

        tree.pack(fill="both", expand=True, padx=16, pady=(0, 16))

        if not rows:
            tk.Label(
                self, text="No games played yet!",
                bg=BACKGROUND_COLOR, fg=TEXT_COLOR,
                font=("Georgia", 12),
            ).pack()


# ── Main Application ──────────────────────────────────────────────────────────

class CamelUpApp(tk.Tk):
    """
    Root Tkinter window.  Hosts the race-track canvas, info panel, and
    action bar.  Delegates all game logic to GameEngine.
    """

    # Layout constants
    TRACK_CANVAS_W = 860
    TRACK_CANVAS_H = 540
    SPACE_W = 50
    SPACE_H = 90
    CAMEL_R = 16          # radius of camel circle
    PANEL_W = 380

    def __init__(self) -> None:
        super().__init__()
        self.title(WINDOW_TITLE)
        self.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.configure(bg=BACKGROUND_COLOR)
        self.resizable(False, False)

        self._db = DatabaseManager()
        self._engine: Optional[GameEngine] = None
        self._desert_tile_pending: Optional[str] = None  # 'oasis'|'mirage'

        self._build_menu()
        self._build_layout()
        self._show_welcome()

    # ── Menu bar ──────────────────────────────────────────────────────────────

    def _build_menu(self) -> None:
        menubar = tk.Menu(self, bg=PANEL_COLOR, fg=TEXT_COLOR,
                          activebackground=BUTTON_HOVER,
                          activeforeground=TEXT_COLOR)

        game_menu = tk.Menu(menubar, tearoff=0,
                            bg=PANEL_COLOR, fg=TEXT_COLOR,
                            activebackground=BUTTON_HOVER)
        game_menu.add_command(label="New Game", command=self._new_game)
        game_menu.add_separator()
        game_menu.add_command(label="Hall of Fame",
                              command=self._show_hall_of_fame)
        game_menu.add_separator()
        game_menu.add_command(label="Quit", command=self.quit)
        menubar.add_cascade(label="Game", menu=game_menu)

        help_menu = tk.Menu(menubar, tearoff=0,
                            bg=PANEL_COLOR, fg=TEXT_COLOR,
                            activebackground=BUTTON_HOVER)
        help_menu.add_command(label="How to Play", command=self._show_rules)
        menubar.add_cascade(label="Help", menu=help_menu)

        self.config(menu=menubar)

    # ── Layout ────────────────────────────────────────────────────────────────

    def _build_layout(self) -> None:
        # ── Left: track + action bar ──
        left = tk.Frame(self, bg=BACKGROUND_COLOR)
        left.pack(side="left", fill="both", expand=True)

        self._track_canvas = tk.Canvas(
            left,
            width=self.TRACK_CANVAS_W,
            height=self.TRACK_CANVAS_H,
            bg=BACKGROUND_COLOR,
            highlightthickness=0,
        )
        self._track_canvas.pack(padx=10, pady=10)

        self._action_bar = tk.Frame(left, bg=PANEL_COLOR, height=200)
        self._action_bar.pack(fill="x", padx=10, pady=(0, 10))
        self._action_bar.pack_propagate(False)
        self._build_action_bar()

        # ── Right: info panel ──
        right = tk.Frame(self, bg=PANEL_COLOR, width=self.PANEL_W)
        right.pack(side="right", fill="y")
        right.pack_propagate(False)
        self._build_info_panel(right)

    # ── Action bar ────────────────────────────────────────────────────────────

    def _build_action_bar(self) -> None:
        bar = self._action_bar

        header = tk.Label(
            bar, text="YOUR ACTIONS",
            font=("Georgia", 11, "bold"),
            bg=PANEL_COLOR, fg=ACCENT_COLOR,
        )
        header.pack(pady=(8, 4))

        btn_row = tk.Frame(bar, bg=PANEL_COLOR)
        btn_row.pack()

        self._btn_roll = StyledButton(
            btn_row, text="🎲  Roll Pyramid",
            command=self._action_roll,
        )
        self._btn_roll.pack(side="left", padx=6, pady=4)

        self._btn_oasis = StyledButton(
            btn_row, text="🌴  Place Oasis",
            command=lambda: self._start_desert_tile("oasis"),
        )
        self._btn_oasis.pack(side="left", padx=6)

        self._btn_mirage = StyledButton(
            btn_row, text="🏜️  Place Mirage",
            command=lambda: self._start_desert_tile("mirage"),
        )
        self._btn_mirage.pack(side="left", padx=6)

        self._btn_overall_win = StyledButton(
            btn_row, text="🏆  Bet Winner",
            command=lambda: self._action_overall_bet("winner"),
        )
        self._btn_overall_win.pack(side="left", padx=6)

        self._btn_overall_lose = StyledButton(
            btn_row, text="💀  Bet Loser",
            command=lambda: self._action_overall_bet("loser"),
        )
        self._btn_overall_lose.pack(side="left", padx=6)

        # Leg-bet row
        bet_row = tk.Frame(bar, bg=PANEL_COLOR)
        bet_row.pack(pady=(4, 8))

        tk.Label(
            bet_row, text="Leg Bet on:",
            bg=PANEL_COLOR, fg=TEXT_COLOR,
            font=("Georgia", 10),
        ).pack(side="left", padx=(4, 8))

        self._leg_bet_buttons: Dict[str, StyledButton] = {}
        for color in CAMEL_COLORS:
            btn = StyledButton(
                bet_row,
                text=color.upper(),
                bg=CAMEL_HEX_COLORS[color],
                fg="black" if color in ("yellow", "white") else "white",
                command=lambda c=color: self._action_leg_bet(c),
            )
            btn.pack(side="left", padx=4)
            self._leg_bet_buttons[color] = btn

        self._status_label = tk.Label(
            bar, text="",
            bg=PANEL_COLOR, fg=ACCENT_COLOR,
            font=("Courier", 9),
        )
        self._status_label.pack()

    # ── Info panel ────────────────────────────────────────────────────────────

    def _build_info_panel(self, parent: tk.Frame) -> None:
        tk.Label(
            parent, text="🐪 CAMEL UP!",
            font=("Georgia", 16, "bold"),
            bg=PANEL_COLOR, fg=ACCENT_COLOR,
        ).pack(pady=(16, 4))

        # Turn indicator
        self._turn_label = tk.Label(
            parent, text="",
            font=("Georgia", 11, "bold"),
            bg=PANEL_COLOR, fg=TEXT_COLOR,
            wraplength=340,
        )
        self._turn_label.pack(pady=(0, 8))

        # Pyramid indicator
        pyr_frame = tk.Frame(parent, bg=PANEL_COLOR)
        pyr_frame.pack()
        tk.Label(
            pyr_frame, text="Pyramid:",
            bg=PANEL_COLOR, fg=TEXT_COLOR,
            font=("Georgia", 10),
        ).pack(side="left")
        self._pyramid_labels: Dict[str, tk.Label] = {}
        for color in CAMEL_COLORS:
            lbl = tk.Label(
                pyr_frame, text="●",
                bg=PANEL_COLOR,
                fg=CAMEL_HEX_COLORS[color],
                font=("Arial", 16),
            )
            lbl.pack(side="left", padx=2)
            self._pyramid_labels[color] = lbl

        ttk.Separator(parent, orient="horizontal").pack(
            fill="x", padx=12, pady=8
        )

        # Scoreboard
        tk.Label(
            parent, text="SCORES",
            font=("Georgia", 11, "bold"),
            bg=PANEL_COLOR, fg=ACCENT_COLOR,
        ).pack()

        self._score_frame = tk.Frame(parent, bg=PANEL_COLOR)
        self._score_frame.pack(fill="x", padx=12, pady=4)

        ttk.Separator(parent, orient="horizontal").pack(
            fill="x", padx=12, pady=8
        )

        # Rankings
        tk.Label(
            parent, text="RACE STANDINGS",
            font=("Georgia", 11, "bold"),
            bg=PANEL_COLOR, fg=ACCENT_COLOR,
        ).pack()

        self._ranking_frame = tk.Frame(parent, bg=PANEL_COLOR)
        self._ranking_frame.pack(fill="x", padx=12, pady=4)

        ttk.Separator(parent, orient="horizontal").pack(
            fill="x", padx=12, pady=8
        )

        # Event log
        tk.Label(
            parent, text="EVENT LOG",
            font=("Georgia", 11, "bold"),
            bg=PANEL_COLOR, fg=ACCENT_COLOR,
        ).pack()

        log_frame = tk.Frame(parent, bg=PANEL_COLOR)
        log_frame.pack(fill="both", expand=True, padx=8, pady=(4, 12))

        self._log_text = tk.Text(
            log_frame,
            bg=BACKGROUND_COLOR, fg=TEXT_COLOR,
            font=("Courier", 8),
            state="disabled",
            width=40,
            relief="flat",
            wrap="word",
        )
        scrollbar = tk.Scrollbar(log_frame, command=self._log_text.yview)
        self._log_text.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self._log_text.pack(side="left", fill="both", expand=True)

    # ── Welcome screen ────────────────────────────────────────────────────────

    def _show_welcome(self) -> None:
        canvas = self._track_canvas
        canvas.delete("all")
        canvas.create_text(
            self.TRACK_CANVAS_W // 2,
            self.TRACK_CANVAS_H // 2 - 40,
            text="🐪  CAMEL UP!",
            font=("Georgia", 36, "bold"),
            fill=ACCENT_COLOR,
        )
        canvas.create_text(
            self.TRACK_CANVAS_W // 2,
            self.TRACK_CANVAS_H // 2 + 20,
            text="Go to  Game → New Game  to start",
            font=("Georgia", 14),
            fill=TEXT_COLOR,
        )
        self._set_actions_enabled(False)

    # ── New game ──────────────────────────────────────────────────────────────

    def _new_game(self) -> None:
        dialog = SetupDialog(self)
        if not dialog.players:
            return   # User cancelled

        players = [
            Player(name=n, player_id=i)
            for i, n in enumerate(dialog.players)
        ]
        self._engine = GameEngine(players)
        self._set_actions_enabled(True)
        self._desert_tile_pending = None
        self._refresh_ui()

    # ── Actions ───────────────────────────────────────────────────────────────

    def _action_roll(self) -> None:
        if self._engine is None or self._engine.is_game_over:
            return
        try:
            color, value, space = self._engine.action_roll_pyramid()
            self._refresh_ui()
            self._status(
                f"🎲 {color.upper()} rolled {value} → space {space}"
            )
            if self._engine.is_game_over:
                self._on_game_over()
        except Exception as exc:
            messagebox.showerror("Error", str(exc))

    def _action_leg_bet(self, color: str) -> None:
        if self._engine is None or self._engine.is_game_over:
            return
        try:
            token = self._engine.action_take_leg_bet(color)
            self._refresh_ui()
            self._status(
                f"Bet placed on {color.upper()} "
                f"(tile worth {token.payout_value})"
            )
        except ValueError as exc:
            messagebox.showwarning("Bet Unavailable", str(exc))

    def _action_overall_bet(self, bet_type: str) -> None:
        if self._engine is None or self._engine.is_game_over:
            return
        color = self._ask_camel_color(f"Bet on Overall {bet_type.title()}")
        if not color:
            return
        try:
            self._engine.action_place_overall_bet(color, bet_type)
            self._refresh_ui()
            self._status(f"Overall {bet_type} bet placed on {color.upper()}")
        except ValueError as exc:
            messagebox.showwarning("Bet Error", str(exc))

    def _start_desert_tile(self, tile_type: str) -> None:
        if self._engine is None or self._engine.is_game_over:
            return
        if self._engine.current_player.desert_tile_on_board:
            messagebox.showinfo(
                "Tile on Board",
                "Your desert tile is already on the board this leg.",
            )
            return
        self._desert_tile_pending = tile_type
        self._status(
            f"Click a space on the track to place your {tile_type} tile…"
        )
        self._track_canvas.config(cursor="crosshair")
        self._track_canvas.bind("<Button-1>", self._on_track_click_tile)

    def _on_track_click_tile(self, event: tk.Event) -> None:
        """Handle a click on the track canvas when placing a desert tile."""
        space = self._canvas_x_to_space(event.x)
        if space is None:
            return
        self._track_canvas.unbind("<Button-1>")
        self._track_canvas.config(cursor="")
        tile_type = self._desert_tile_pending
        self._desert_tile_pending = None
        try:
            self._engine.action_place_desert_tile(space, tile_type)
            self._refresh_ui()
            self._status(f"{tile_type.title()} placed on space {space}.")
        except ValueError as exc:
            messagebox.showwarning("Invalid Placement", str(exc))

    def _canvas_x_to_space(self, x: int) -> Optional[int]:
        """Convert a canvas x-coordinate to a board space number."""
        margin = 30
        space_w = (self.TRACK_CANVAS_W - margin * 2) // TRACK_LENGTH
        space = (x - margin) // space_w + 1
        if 1 <= space <= TRACK_LENGTH:
            return int(space)
        return None

    # ── UI refresh ────────────────────────────────────────────────────────────

    def _refresh_ui(self) -> None:
        if self._engine is None:
            return
        self._draw_track()
        self._refresh_info_panel()
        self._refresh_log()

    def _draw_track(self) -> None:
        """Re-draw the entire race track on the canvas."""
        canvas = self._track_canvas
        canvas.delete("all")

        engine = self._engine
        board = engine.board

        margin_x = 30
        margin_y = 60
        total_w = self.TRACK_CANVAS_W - margin_x * 2
        space_w = total_w // TRACK_LENGTH
        space_h = self.SPACE_H

        # Track background strip
        canvas.create_rectangle(
            margin_x, margin_y,
            margin_x + space_w * TRACK_LENGTH, margin_y + space_h,
            fill=TRACK_COLOR, outline=_darken(TRACK_COLOR), width=2,
        )

        for sp in range(1, TRACK_LENGTH + 1):
            x0 = margin_x + (sp - 1) * space_w
            x1 = x0 + space_w
            y0 = margin_y
            y1 = margin_y + space_h

            # Space border
            canvas.create_rectangle(
                x0, y0, x1, y1,
                fill="", outline=_darken(TRACK_COLOR), width=1,
            )

            # Space number
            canvas.create_text(
                x0 + space_w // 2, y0 + 8,
                text=str(sp),
                font=("Courier", 7),
                fill=_darken(TRACK_COLOR, 0.5),
            )

            # Finish line at space 16
            if sp == TRACK_LENGTH:
                canvas.create_line(
                    x1 - 2, y0, x1 - 2, y1,
                    fill=ACCENT_COLOR, width=3, dash=(4, 2),
                )

            # Desert tile marker
            tile = board.desert_tiles.get(sp)
            if tile:
                tile_type, owner_id = tile
                tile_color = "#2ECC40" if tile_type == "oasis" else "#FF4136"
                canvas.create_rectangle(
                    x0 + 2, y1 - 14, x1 - 2, y1 - 2,
                    fill=tile_color, outline="",
                )
                tile_sym = "🌴" if tile_type == "oasis" else "🏜️"
                canvas.create_text(
                    x0 + space_w // 2, y1 - 8,
                    text=tile_sym, font=("Arial", 8),
                )

            # Draw camels in this space
            stack = board.stack_at(sp)
            for stack_idx, camel in enumerate(stack):
                cx = x0 + space_w // 2
                cy = y1 - 20 - stack_idx * (self.CAMEL_R * 2 + 2)
                r = self.CAMEL_R
                canvas.create_oval(
                    cx - r, cy - r, cx + r, cy + r,
                    fill=camel.hex_color,
                    outline=_darken(camel.hex_color),
                    width=2,
                )
                # Camel initial
                initial = camel.color[0].upper()
                txt_color = "black" if camel.color in ("yellow", "white") else "white"
                canvas.create_text(
                    cx, cy,
                    text=initial,
                    font=("Georgia", 9, "bold"),
                    fill=txt_color,
                )

        # Leg counter
        canvas.create_text(
            self.TRACK_CANVAS_W // 2, margin_y - 20,
            text=f"LEG {engine.leg_number}   "
                 f"Pyramid: {len(engine.pyramid_remaining)} dice remaining",
            font=("Georgia", 11, "bold"),
            fill=ACCENT_COLOR,
        )

        # Finish flag emoji
        canvas.create_text(
            margin_x + space_w * TRACK_LENGTH + 16,
            margin_y + space_h // 2,
            text="🏁",
            font=("Arial", 18),
        )

    def _refresh_info_panel(self) -> None:
        engine = self._engine

        # Turn label
        self._turn_label.config(
            text=f"🎯 Current Turn: {engine.current_player.name}"
        )

        # Pyramid dots
        for color in CAMEL_COLORS:
            lbl = self._pyramid_labels[color]
            if color in engine.pyramid_remaining:
                lbl.config(fg=CAMEL_HEX_COLORS[color])
            else:
                lbl.config(fg="#333333")

        # Scores
        for widget in self._score_frame.winfo_children():
            widget.destroy()
        for player in sorted(engine.players, key=lambda p: p.coins, reverse=True):
            row = tk.Frame(self._score_frame, bg=PANEL_COLOR)
            row.pack(fill="x", pady=1)
            marker = "▶ " if player == engine.current_player else "   "
            tk.Label(
                row,
                text=f"{marker}{player.name}",
                bg=PANEL_COLOR, fg=TEXT_COLOR,
                font=("Courier", 10),
                width=20, anchor="w",
            ).pack(side="left")
            tk.Label(
                row,
                text=f"{player.coins} 🪙",
                bg=PANEL_COLOR, fg=ACCENT_COLOR,
                font=("Courier", 10, "bold"),
            ).pack(side="right")

        # Rankings
        for widget in self._ranking_frame.winfo_children():
            widget.destroy()
        for rank, camel in enumerate(engine.get_ranking(), 1):
            row = tk.Frame(self._ranking_frame, bg=PANEL_COLOR)
            row.pack(fill="x", pady=1)
            tk.Label(
                row,
                text=f"{rank}.",
                bg=PANEL_COLOR, fg=TEXT_COLOR,
                font=("Courier", 9), width=3,
            ).pack(side="left")
            tk.Label(
                row,
                text="●",
                bg=PANEL_COLOR, fg=CAMEL_HEX_COLORS[camel.color],
                font=("Arial", 14),
            ).pack(side="left")
            tk.Label(
                row,
                text=f"{camel.color.upper()}  (space {camel.position})",
                bg=PANEL_COLOR, fg=TEXT_COLOR,
                font=("Courier", 9),
            ).pack(side="left", padx=4)

    def _refresh_log(self) -> None:
        """Append new events to the log text widget."""
        engine = self._engine
        self._log_text.config(state="normal")
        self._log_text.delete("1.0", "end")
        for event in engine.event_log[-60:]:
            self._log_text.insert("end", event + "\n")
        self._log_text.see("end")
        self._log_text.config(state="disabled")

    # ── Game over ─────────────────────────────────────────────────────────────

    def _on_game_over(self) -> None:
        engine = self._engine
        sorted_players = sorted(
            engine.players, key=lambda p: p.coins, reverse=True
        )
        winner = sorted_players[0]

        # Persist result
        try:
            self._db.save_game(
                players_result=[p.to_dict() for p in sorted_players],
                leg_count=engine.leg_number,
                event_log=engine.event_log,
            )
        except Exception as exc:
            messagebox.showwarning("DB Error", f"Could not save game: {exc}")

        self._set_actions_enabled(False)

        summary = "\n".join(
            f"  {i+1}. {p.name}: {p.coins} coins"
            for i, p in enumerate(sorted_players)
        )
        messagebox.showinfo(
            "🏁  Race Over!",
            f"🥇 Winner: {winner.name} ({winner.coins} coins)\n\n"
            f"Final standings:\n{summary}\n\n"
            "Start a new game from the Game menu.",
        )

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _set_actions_enabled(self, enabled: bool) -> None:
        state = "normal" if enabled else "disabled"
        for btn in [
            self._btn_roll,
            self._btn_oasis,
            self._btn_mirage,
            self._btn_overall_win,
            self._btn_overall_lose,
            *self._leg_bet_buttons.values(),
        ]:
            btn.config(state=state)

    def _status(self, msg: str) -> None:
        self._status_label.config(text=msg)

    def _ask_camel_color(self, prompt: str) -> Optional[str]:
        """Show a dialog asking the user to pick a camel colour."""
        dialog = tk.Toplevel(self)
        dialog.title(prompt)
        dialog.configure(bg=BACKGROUND_COLOR)
        dialog.resizable(False, False)
        dialog.grab_set()

        chosen = tk.StringVar(value="")

        tk.Label(
            dialog, text=prompt,
            bg=BACKGROUND_COLOR, fg=TEXT_COLOR,
            font=("Georgia", 11),
        ).pack(pady=(12, 8))

        row = tk.Frame(dialog, bg=BACKGROUND_COLOR)
        row.pack(pady=(0, 12))
        for color in CAMEL_COLORS:
            StyledButton(
                row,
                text=color.upper(),
                bg=CAMEL_HEX_COLORS[color],
                fg="black" if color in ("yellow", "white") else "white",
                command=lambda c=color: [chosen.set(c), dialog.destroy()],
            ).pack(side="left", padx=4)

        StyledButton(
            dialog, text="Cancel",
            command=dialog.destroy,
        ).pack(pady=(0, 10))

        dialog.wait_window()
        return chosen.get() or None

    def _show_hall_of_fame(self) -> None:
        HallOfFameWindow(self, self._db)

    def _show_rules(self) -> None:
        rules = (
            "🐪  CAMEL UP – HOW TO PLAY\n\n"
            "On your turn, choose ONE action:\n\n"
            "🎲 Roll Pyramid – Draw a die, move that camel 1-3 spaces.\n"
            "   Earn 1 coin. Camels carry others on top of them.\n\n"
            "🌴 Place Oasis – Your tile pushes landing camels forward 1\n"
            "   extra space (to the top of the stack). Earn 1 coin.\n\n"
            "🏜️ Place Mirage – Your tile pushes landing camels back 1\n"
            "   space (to the bottom). Earn 1 coin.\n\n"
            "🎫 Leg Bet – Take a tile betting on the leg leader.\n"
            "   Winner tiles pay 5→3→2→1→1; wrong bets cost 1.\n\n"
            "🏆 Overall Winner/Loser Bet – Predict the race winner or\n"
            "   loser. Pay 8→5→3→2→1 (first bettors earn most).\n\n"
            "A leg ends when all 5 dice are pulled. The race ends\n"
            "when a camel reaches or passes space 16."
        )
        messagebox.showinfo("How to Play", rules)