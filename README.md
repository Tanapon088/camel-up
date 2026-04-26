# 🐪 Camel Up! – Digital Edition

A fully featured, modular Python implementation of the award-winning board game **Camel Up**, featuring a Tkinter GUI, complete game logic, and SQLite-backed persistence.

---

## Table of Contents

1. [Features](#features)
2. [Project Structure](#project-structure)
3. [Prerequisites](#prerequisites)
4. [Quick Start](#quick-start)
5. [How to Play](#how-to-play)
6. [Architecture](#architecture)
7. [Database & Hall of Fame](#database--hall-of-fame)
8. [Running Tests](#running-tests)
9. [Troubleshooting](#troubleshooting)

---

## Features

| Feature | Details |
|---|---|
| **Full Rule Set** | Camel stacking, desert tiles (oasis/mirage), pyramid dice, leg bets, overall winner/loser bets |
| **2–8 Players** | Fully supports the official player range |
| **Tkinter GUI** | Race-track canvas, real-time rankings, event log, action buttons |
| **Hall of Fame** | Persistent SQLite leaderboard across sessions |
| **Player Stats** | Games played, wins, total coins, best score |
| **Robust Errors** | try/except throughout; user-friendly dialogs for invalid actions |
| **PEP 8** | Fully linted, type-annotated, with docstrings throughout |

---

## Project Structure

```
camel_up/
├── main.py                  # ← Entry point
│
├── logic/                   # Game engine & rules
│   ├── __init__.py
│   ├── camel.py             # Camel dataclass
│   ├── player.py            # Player, LegBetToken, OverallBetToken
│   ├── board.py             # Track, stacking, desert tiles
│   └── game_engine.py       # Turn management, scoring, leg/race resolution
│
├── gui/                     # Tkinter user interface
│   ├── __init__.py
│   └── app.py               # CamelUpApp, SetupDialog, HallOfFameWindow
│
├── database/                # Persistence layer
│   ├── __init__.py
│   └── db_manager.py        # SQLite CRUD via DatabaseManager
│
├── utils/                   # Shared helpers & constants
│   ├── __init__.py
│   ├── constants.py          # Game constants, colours, layout
│   └── helpers.py            # Dice rolling, formatting, validation
│
├── requirements.txt
└── README.md
```

---

## Prerequisites

- **Python 3.9+** (3.11 or 3.12 recommended)
- **Tkinter** – bundled with CPython on Windows and macOS.
  On Ubuntu/Debian, install separately:
  ```bash
  sudo apt-get install python3-tk
  ```

No third-party pip packages are required – everything uses the Python standard library.

---

## Quick Start

### 1. Clone / download the project

```bash
git clone https://github.com/yourname/camel-up-digital.git
cd camel-up-digital
```

### 2. Create and activate a virtual environment

**macOS / Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

**Windows (PowerShell):**
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

> All dependencies are standard-library; this step is a no-op but confirms your environment is correct.

### 4. Run the game

```bash
python main.py
```

The GUI window will open. Go to **Game → New Game** to set up players and start racing!

---

## How to Play

Camel Up is a betting/racing game played over several *legs*.

### Turn Actions (choose ONE per turn)

| Action | Effect |
|---|---|
| 🎲 **Roll Pyramid** | Draw one die, move that camel (and any above it) 1–3 spaces forward. Earn **1 coin**. |
| 🌴 **Place Oasis** | Put your oasis tile on a free space. When a camel lands there, it moves **+1** extra and goes to the **top** of the stack. You earn **1 coin** each time. |
| 🏜️ **Place Mirage** | Your mirage tile sends the landing camel **−1** space to the **bottom** of that stack. Earn **1 coin** each time. |
| 🎫 **Leg Bet** | Take the next available tile for a camel, betting it leads at leg end. Correct: earn **5 / 3 / 2 / 1 / 1**. Wrong: **−1 coin**. |
| 🏆 **Overall Winner Bet** | Predict the race winner. Pays **8 / 5 / 3 / 2 / 1** (first bettor earns most). Wrong: **−1 coin**. |
| 💀 **Overall Loser Bet** | Predict the race loser. Same payout structure. |

### Leg End
When all 5 pyramid dice have been rolled, the leg ends. Leg bets are scored, desert tiles are returned, and a new leg begins.

### Race End
The race ends the moment any camel reaches or passes **space 16**. Overall bets are scored and the player with the most coins wins!

---

## Architecture

### OOP Class Hierarchy

```
Camel           – dataclass: color, position, stack_order
Player          – name, coins, leg/overall bets, desert tile
  LegBetToken   – camel_color, payout_value
  OverallBetToken – camel_color, bet_type, order_placed
Board           – spaces dict, camels dict, desert_tiles dict
  move_camel()  – handles stacking + desert-tile effects
GameEngine      – orchestrates turns, scoring, leg/race resolution
  LegBetSupply  – per-camel tile stacks (5, 3, 2, 1, 1)
  OverallBetTracker – tracks order-placed per camel/bet-type
DatabaseManager – SQLite CRUD (games, player_stats, game_events)
CamelUpApp      – Tkinter root; delegates to GameEngine
```

### Data Flow

```
User clicks button
  → CamelUpApp action handler
    → GameEngine.action_*()
      → Board.move_camel() / LegBetSupply / ...
        → _resolve_leg() / _resolve_race() when triggered
    → CamelUpApp._refresh_ui()
      → _draw_track() + _refresh_info_panel() + _refresh_log()
```

---

## Database & Hall of Fame

The SQLite database is created automatically at `database/camel_up.db`.

**Tables:**
- `games` – one row per completed game (timestamp, winner, players JSON, leg count)
- `player_stats` – cumulative wins, coins, best score per player name
- `game_events` – full event log linked to each game

**Viewing the Hall of Fame:**  
Go to **Game → Hall of Fame** in the menu.

To reset all statistics, delete `database/camel_up.db` and restart the game.

---

## Running Tests

```bash
# Install pytest (optional, for development)
pip install pytest

# Run all tests
pytest tests/ -v
```

> A `tests/` directory can be created with unit tests for `GameEngine`, `Board`, and `DatabaseManager`.  
> The modular architecture makes each component independently testable.

---

## Troubleshooting

| Problem | Solution |
|---|---|
| `ModuleNotFoundError: No module named 'tkinter'` | Install tkinter: `sudo apt-get install python3-tk` |
| Window doesn't open on macOS | Try `python3 main.py` (ensure you're using the right interpreter) |
| Database errors | Delete `database/camel_up.db` to reset |
| Camels start at the same position | This is by design – the random setup can stack camels |

---

## License

MIT – feel free to extend, fork, or use as a learning resource.

---

*Built with ❤️ and pure Python stdlib – no bloated dependencies!*
