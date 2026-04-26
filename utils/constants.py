"""
constants.py
------------
Global constants for the Camel Up digital board game.
"""

# ── Camel identities ──────────────────────────────────────────────────────────
CAMEL_COLORS = ["yellow", "blue", "green", "orange", "white"]

# ── Board layout ──────────────────────────────────────────────────────────────
TRACK_LENGTH = 16          # Spaces 1-16; reaching/passing 16 ends the game
START_POSITION = 0         # Camels begin off-board (position 0 = not yet moved)

# ── Dice ─────────────────────────────────────────────────────────────────────
DICE_VALUES = [1, 2, 3]    # Each camel die can show 1, 2, or 3

# ── Leg-bet payouts (index = position on leg-bet tile stack) ──────────────────
LEG_BET_PAYOUTS = {
    1: 5,   # First correct bet this leg
    2: 3,   # Second correct bet
    3: 2,   # Third correct bet
    4: 1,   # Fourth correct bet
    5: 1,   # Fifth+ correct bet
}
WRONG_LEG_BET_PENALTY = -1   # Penalty for picking the wrong camel

# ── Overall-race bet payouts ───────────────────────────────────────────────────
OVERALL_BET_PAYOUTS = [8, 5, 3, 2, 1]   # By order placed (first bet highest)
OVERALL_WRONG_PENALTY = -1

# ── Desert tiles ──────────────────────────────────────────────────────────────
OASIS_EFFECT = +1    # Advances camel by 1 extra; moves camel to top of stack
MIRAGE_EFFECT = -1   # Moves camel back 1; moves camel to bottom of stack

# ── Spectator-card payout ─────────────────────────────────────────────────────
SPECTATOR_CARD_PAYOUT = 1   # Coins earned each time a camel lands on your tile

# ── GUI ───────────────────────────────────────────────────────────────────────
WINDOW_TITLE = "🐪 Camel Up! – Digital Edition"
WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 800
FPS = 60

CAMEL_HEX_COLORS = {
    "yellow":  "#F5C518",
    "blue":    "#1E90FF",
    "green":   "#32CD32",
    "orange":  "#FF8C00",
    "white":   "#F0F0F0",
}

TRACK_COLOR       = "#D2A679"
BACKGROUND_COLOR  = "#2B1B0E"
PANEL_COLOR       = "#3C2A1A"
ACCENT_COLOR      = "#FFD700"
TEXT_COLOR        = "#FFFDE7"
BUTTON_COLOR      = "#5C3D1E"
BUTTON_HOVER      = "#7A5230"

# ── Database ──────────────────────────────────────────────────────────────────
DB_PATH = "database/camel_up.db"