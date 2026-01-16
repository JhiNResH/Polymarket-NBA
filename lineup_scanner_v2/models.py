"""
Data models using Pydantic for validation
"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime


@dataclass
class Player:
    """NBA Player with status"""
    name: str
    status: str = "Starting"  # Starting, Out, GTD, Doubtful, Questionable
    
    @property
    def is_available(self) -> bool:
        return self.status in ("Starting", "GTD", "Questionable")


@dataclass
class Team:
    """NBA Team lineup"""
    name: str
    abbreviation: str
    players: List[Player] = field(default_factory=list)
    injuries: List[Player] = field(default_factory=list)
    
    @property
    def lineup_strength(self) -> float:
        """Calculate lineup completeness (0-1)"""
        available = sum(1 for p in self.players[:5] if p.is_available)
        return available / 5


@dataclass
class OddsData:
    """Betting odds from Polymarket or other sources"""
    team: str
    moneyline_prob: Optional[float] = None
    moneyline_american: Optional[str] = None
    spread_line: Optional[float] = None
    spread_odds: Optional[int] = None
    url: Optional[str] = None


@dataclass
class GameData:
    """Complete game data"""
    matchup: str  # e.g., "MEM @ ORL"
    game_time: str
    away_team: Team
    home_team: Team
    away_odds: Optional[OddsData] = None
    home_odds: Optional[OddsData] = None
    scraped_at: datetime = field(default_factory=datetime.now)


@dataclass
class EVResult:
    """Expected Value analysis result"""
    game: GameData
    ev: float
    best_bet: str  # e.g., "Lakers ML", "Magic SPREAD +3.5"
    best_bet_raw: str  # e.g., "HOME_ML", "AWAY_SPREAD"
    confidence: str  # HIGH, MEDIUM, LOW
    analysis: str
    has_signal: bool
    
    @property
    def ev_percent(self) -> str:
        return f"{self.ev * 100:+.1f}%"


@dataclass
class ScanReport:
    """Complete scan report"""
    scan_time: datetime
    games: List[GameData]
    results: List[EVResult]
    top_picks: int = 3
    
    @property
    def sorted_by_ev(self) -> List[EVResult]:
        return sorted(self.results, key=lambda x: x.ev, reverse=True)
    
    @property
    def top_recommendations(self) -> List[EVResult]:
        return self.sorted_by_ev[:self.top_picks]
