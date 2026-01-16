"""
Polymarket NBA Odds Scraper - Async implementation
"""
import logging
from typing import Dict, List, Optional
import httpx

from .base import BaseScraper
from ..config import config
from ..models import OddsData, GameData, Team

logger = logging.getLogger("nba_scanner.scrapers.polymarket")

# NBA series_id from Polymarket Sports API
NBA_SERIES_ID = "10345"
NBA_GAME_TAG_ID = "100639"

# Team name mapping
TEAM_NAME_MAP = {
    "MEM": "Grizzlies", "ORL": "Magic", "PHX": "Suns", "DET": "Pistons",
    "OKC": "Thunder", "HOU": "Rockets", "BOS": "Celtics", "MIA": "Heat",
    "MIL": "Bucks", "SAS": "Spurs", "UTA": "Jazz", "DAL": "Mavericks",
    "NYK": "Knicks", "GSW": "Warriors", "ATL": "Hawks", "POR": "Blazers",
    "CHA": "Hornets", "LAL": "Lakers", "LAC": "Clippers", "DEN": "Nuggets",
    "MIN": "Timberwolves", "SAC": "Kings", "PHI": "76ers", "TOR": "Raptors",
    "BKN": "Nets", "CHI": "Bulls", "CLE": "Cavaliers", "IND": "Pacers",
    "WAS": "Wizards", "NOP": "Pelicans",
}


class PolymarketScraper(BaseScraper):
    """Scrapes NBA odds from Polymarket Sports API"""
    
    def __init__(self):
        super().__init__()
        self.base_url = config.polymarket_api
    
    async def scrape(self, client: httpx.AsyncClient) -> Dict[str, OddsData]:
        """Fetch all NBA game odds"""
        logger.info("Fetching Polymarket NBA odds...")
        
        try:
            events = await self._fetch_nba_events(client)
            odds_map = self._parse_events(events)
            logger.info(f"Found odds for {len(odds_map)} teams")
            return odds_map
        except Exception as e:
            logger.error(f"Failed to fetch Polymarket odds: {e}")
            return {}
    
    async def _fetch_nba_events(self, client: httpx.AsyncClient) -> List[dict]:
        """Fetch NBA events from Polymarket API"""
        url = f"{self.base_url}/events"
        params = {
            "series_id": NBA_SERIES_ID,
            "tag_id": NBA_GAME_TAG_ID,
            # "active": "true",
            "closed": "false",
            "order": "startTime",
            "ascending": "true",
            "limit": 200
        }
        
        response = await self.fetch(client, url, params=params)
        return response.json()
    
    def _parse_events(self, events: List[dict]) -> Dict[str, OddsData]:
        """Parse events into OddsData objects keyed by team abbreviation"""
        odds_map = {}
        
        for event in events:
            title = event.get("title", "").upper()
            slug = event.get("slug", "")
            url = f"https://polymarket.com/event/{slug}"
            
            # Track moneyline and spread data per team for this event
            event_ml = {}  # {abbr: prob}
            event_spread = {}  # {abbr: spread_line}
            
            for market in event.get("markets", []):
                try:
                    question = market.get("question", "")
                    outcomes = eval(market.get("outcomes", "[]"))
                    prices = eval(market.get("outcomePrices", "[]"))
                    
                    if len(outcomes) < 2 or len(prices) < 2:
                        continue
                    
                    team1, team2 = outcomes[0], outcomes[1]
                    price1, price2 = float(prices[0]), float(prices[1])
                    
                    # Check if this is a spread market
                    # Format: "Spread: Lakers (-3.5)" or "1H Spread: Lakers (-2.5)"
                    if "spread:" in question.lower():
                        # Extract spread line from question
                        spread_info = self._parse_spread_question(question)
                        if spread_info:
                            fav_team, spread_val = spread_info
                            # Favorite team has negative spread, underdog has positive
                            for team_name, prob in [(team1, price1), (team2, price2)]:
                                abbr = self._find_abbreviation(team_name)
                                if abbr:
                                    # Check if this team is the favorite
                                    if self._find_abbreviation(fav_team) == abbr:
                                        # Favorite gets the original (negative) spread
                                        if abbr not in event_spread:
                                            event_spread[abbr] = spread_val
                                    else:
                                        # Underdog gets opposite spread
                                        if abbr not in event_spread:
                                            event_spread[abbr] = -spread_val
                    elif "vs." in question.lower() and "o/u" not in question.lower() and "spread" not in question.lower():
                        # Moneyline market (e.g., "Grizzlies vs. Lakers")
                        for team, prob in [(team1, price1), (team2, price2)]:
                            abbr = self._find_abbreviation(team)
                            if abbr and abbr not in event_ml:
                                event_ml[abbr] = prob
                
                except Exception as e:
                    logger.debug(f"Failed to parse market: {e}")
                    continue
            
            # Combine moneyline and spread data into OddsData
            for abbr, prob in event_ml.items():
                spread_line = event_spread.get(abbr)
                odds_map[abbr] = OddsData(
                    team=TEAM_NAME_MAP.get(abbr, abbr),
                    moneyline_prob=prob,
                    moneyline_american=self._prob_to_american(prob),
                    spread_line=spread_line,
                    url=url
                )
        
        return odds_map
    
    def _parse_spread_question(self, question: str) -> Optional[tuple]:
        """
        Parse question string like 'Spread: Lakers (-3.5)' or '1H Spread: Lakers (-2.5)'
        Returns (team_name, spread_value) or None
        """
        import re
        # Regex to find "Spread: Team Name (Value)"
        # Case insensitive match for "Spread:" followed by team and (value)
        # Matches: "Spread: Lakers (-3.5)", "1H Spread: Lakers (-2.5)"
        match = re.search(r"Spread:\s*(.+?)\s*\((\+?-?\d+\.?\d*)\)", question, re.IGNORECASE)
        if match:
            team_name = match.group(1).strip()
            try:
                spread_val = float(match.group(2))
                return (team_name, spread_val)
            except ValueError:
                pass
        return None
    
    def _find_abbreviation(self, team_name: str) -> Optional[str]:
        """Find team abbreviation from full name"""
        team_upper = team_name.upper()
        for abbr, name in TEAM_NAME_MAP.items():
            if name.upper() in team_upper or team_upper in name.upper():
                return abbr
        return None
    
    @staticmethod
    def _prob_to_american(prob: float) -> str:
        """Convert probability to American odds"""
        if prob <= 0 or prob >= 1:
            return "N/A"
        if prob > 0.5:
            return f"-{int(prob / (1 - prob) * 100)}"
        else:
            return f"+{int((1 - prob) / prob * 100)}"
            
    async def scrape_games(self, client: httpx.AsyncClient, date: Optional[str] = None) -> List[GameData]:
        """Scrape games from Polymarket events for fallback schedule"""
        try:
            events = await self._fetch_nba_events(client)
            games = []
            
            target_date = None
            if date:
                from datetime import datetime
                target_date = datetime.strptime(date, "%Y-%m-%d").date()
            
            for event in events:
                # Filter by date if needed
                start_iso = event.get("startDate")
                if not start_iso:
                    continue
                    
                from datetime import datetime
                # Parse ISO like "2024-03-20T23:00:00Z"
                try:
                    event_dt = datetime.fromisoformat(start_iso.replace("Z", "+00:00"))
                    
                    if target_date:
                        # Convert event to Eastern Time (NBA works on ET)
                        # ET is UTC-5 (standard) or UTC-4 (DST). For simplicity we use UTC-5.
                        from datetime import timezone, timedelta
                        et_tz = timezone(timedelta(hours=-5))
                        event_dt_et = event_dt.astimezone(et_tz)
                        
                        if event_dt_et.date() != target_date:
                            logger.debug(f"Skipping event {event.get('title')} at {start_iso} (ET: {event_dt_et.date()}) vs Target {target_date}")
                            continue
                except ValueError:
                    continue
                    continue

                # Parse teams
                markets = event.get("markets", [])
                if not markets: continue
                
                # Get teams from first market
                m = markets[0]
                outcomes = eval(m.get("outcomes", "[]"))
                if len(outcomes) < 2: continue
                
                team1_name = outcomes[0]
                team2_name = outcomes[1]
                
                abbr1 = self._find_abbreviation(team1_name)
                abbr2 = self._find_abbreviation(team2_name)
                
                if not abbr1 or not abbr2: continue
                
                # Determine Home/Away (Polymarket doesn't explicitly say, but usually Away @ Home order? Or random?)
                # We can't easily know who is home without a lookup.
                # Heuristic: Scan known NBA home/away patterns or assume order
                # Standard US convention: Away @ Home.
                # Polymarket often lists "Team A vs Team B".
                # Let's assume Team 2 is Home for now, or match with known schedule if possible.
                # FALLBACK: Just assign arbitrary home/away. This might affect Home Court Advantage feature.
                # Better: Check if team2 is a "Home" team via external validation? Too complex.
                # We will assume outcomes[0] is Away, outcomes[1] is Home (often standard).
                
                away_team = Team(name=team1_name, abbreviation=abbr1)
                home_team = Team(name=team2_name, abbreviation=abbr2)
                
                game = GameData(
                    matchup=f"{abbr1} @ {abbr2}",
                    game_time=start_iso,
                    away_team=away_team,
                    home_team=home_team
                )
                games.append(game)
                
            return games
            
        except Exception as e:
            logger.error(f"Failed to scrape games from Polymarket: {e}")
            return []
