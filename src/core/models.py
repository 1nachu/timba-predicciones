"""
Data Models and Enums for Timba Core
====================================
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class MatchStatus(Enum):
    """Estado del partido"""
    SCHEDULED = "Scheduled"
    LIVE = "Live"
    FINISHED = "Finished"
    POSTPONED = "Postponed"
    CANCELLED = "Cancelled"


class PredictionType(Enum):
    """Tipos de predicción disponibles"""
    FULL_TIME = "full_time"
    UNDER_OVER = "under_over"
    DOUBLE_CHANCE = "double_chance"


@dataclass
class APIQuotaStatus:
    """Estado de cuota diaria"""
    requests_used: int
    requests_available: int
    requests_remaining: int
    reset_date: str
    plan_name: str
    
    @property
    def is_exhausted(self) -> bool:
        """Verifica si la cuota está agotada"""
        return self.requests_available <= 0
    
    @property
    def can_request(self, cost: int = 1) -> bool:
        """Verifica si se puede hacer una solicitud"""
        return self.requests_available >= cost


@dataclass
class MatchPrediction:
    """Predicción de partido"""
    match_id: int
    home_team: str
    away_team: str
    match_date: str
    probability_home_win: float
    probability_draw: float
    probability_away_win: float
    under_2_5_probability: float
    over_2_5_probability: float
    expected_goals_home: float
    expected_goals_away: float
    prediction: str
    confidence: float
    comparison: str = ""
    timestamp: Optional[str] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc).isoformat()


@dataclass
class MatchFixture:
    """Fixture de partido"""
    match_id: int
    league_id: int
    season: int
    round: int
    date: str
    home_team_id: int
    home_team: str
    away_team_id: int
    away_team: str
    status: str
    venue: str
    referee: Optional[str]
    timestamp: Optional[str] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc).isoformat()


@dataclass
class MLFeatures:
    """Features para modelo ML"""
    match_id: int
    home_win_prob: float
    draw_prob: float
    away_win_prob: float
    over_2_5_prob: float
    under_2_5_prob: float
    xg_home: float
    xg_away: float
    xg_diff: float
    prediction_label: str
    prediction_confidence: float
    last_updated: str
