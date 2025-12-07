"""Package entry point for python -m sleeper_league execution."""

import sys
from .cli import main

if __name__ == "__main__":
    sys.exit(main())
