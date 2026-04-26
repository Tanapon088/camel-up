"""
main.py
-------
Entry point for the Camel Up! Digital Edition.

Usage:
    python main.py
"""

import sys
import logging

# Ensure the project root is on sys.path when run directly
import os
sys.path.insert(0, os.path.dirname(__file__))

from gui.app import CamelUpApp

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


def main() -> None:
    """Launch the Camel Up! GUI application."""
    try:
        app = CamelUpApp()
        app.mainloop()
    except KeyboardInterrupt:
        print("\nGame interrupted. Goodbye!")
    except Exception as exc:
        logging.critical("Unexpected error: %s", exc, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()