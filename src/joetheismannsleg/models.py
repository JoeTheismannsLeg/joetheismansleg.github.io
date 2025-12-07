"""Data models for fantasy league data."""

from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class TeamRecord:
    """Team standings record."""
    team: str
    wins: int = 0
    losses: int = 0
    points_for: float = 0.0
    points_against: float = 0.0
    
    @property
    def win_percentage(self) -> float:
        """Calculate win percentage."""
        total = self.wins + self.losses
        return self.wins / total if total > 0 else 0.0
    
    def to_dict(self) -> Dict[str, object]:
        """Convert to dictionary."""
        return {
            'Team': self.team,
            'W': self.wins,
            'L': self.losses,
            'W%': round(self.win_percentage, 3),
            'PF': round(self.points_for, 2),
            'PA': round(self.points_against, 2)
        }


@dataclass
class SeasonStats:
    """Overall season statistics."""
    total_matchups: int = 0
    avg_points: float = 0.0
    highest_score: float = 0.0
    lowest_score: float = 0.0
    
    def to_dict(self) -> Dict[str, object]:
        """Convert to dictionary."""
        return {
            'total_matchups': self.total_matchups,
            'avg_points': self.avg_points,
            'highest_score': self.highest_score,
            'lowest_score': self.lowest_score,
        }


@dataclass
class Matchup:
    """Single matchup result."""
    matchup_id: Optional[int]
    week: int
    team_1: str
    score_1: float
    team_2: str
    score_2: float
    
    def is_bye(self) -> bool:
        """Check if this is a bye week."""
        return self.team_2 == 'BYE'
    
    def is_incomplete(self) -> bool:
        """Check if this matchup is incomplete."""
        return self.team_2 == 'UNPLAYED/INCOMPLETE'
    
    def winner(self) -> Optional[int]:
        """
        Determine winner.
        
        Returns:
            1 if team_1 wins, 2 if team_2 wins, 0 if tie, None if invalid
        """
        if self.is_bye() or self.is_incomplete():
            return None
        if self.score_1 > self.score_2:
            return 1
        elif self.score_2 > self.score_1:
            return 2
        return 0  # Tie


@dataclass
class LuckStats:
    """Behind the Cue Ball - Luck Statistics."""
    team: str
    week: int
    actual_wins: int
    actual_losses: int
    true_wins: int
    true_losses: int
    
    @property
    def win_percentage(self) -> float:
        """Team's actual win percentage."""
        total = self.actual_wins + self.actual_losses
        return self.actual_wins / total if total > 0 else 0.0
    
    @property
    def true_percentage(self) -> float:
        """Win percentage if played all teams."""
        total = self.true_wins + self.true_losses
        return self.true_wins / total if total > 0 else 0.0
    
    @property
    def luck(self) -> float:
        """Luck factor: Win % - True %."""
        return self.win_percentage - self.true_percentage
    
    def to_dict(self) -> Dict[str, object]:
        """Convert to dictionary."""
        return {
            'Team': self.team,
            'Week': self.week,
            'Actual W': self.actual_wins,
            'Actual L': self.actual_losses,
            'Win %': round(self.win_percentage, 3),
            'True W': self.true_wins,
            'True L': self.true_losses,
            'True %': round(self.true_percentage, 3),
            'Luck': round(self.luck, 3),
        }


@dataclass
class LeagueInfo:
    """League information."""
    league_id: str
    name: Optional[str] = None
    season: Optional[int] = None
    status: str = 'unknown'
    current_week: Optional[int] = None
    users: Dict[str, str] = field(default_factory=dict)  # user_id -> display_name
