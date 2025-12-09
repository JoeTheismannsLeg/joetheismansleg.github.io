"""Data acquisition layer - Fantasy league API integration."""

from .client import LeagueClient
from .league import League

__all__ = [
    "LeagueClient",
    "League",
]
