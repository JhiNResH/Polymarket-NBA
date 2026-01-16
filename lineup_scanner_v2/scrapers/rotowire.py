"""
RotoWire NBA Lineup Scraper - Async httpx implementation
"""
import re
import json
import logging
from typing import List, Optional
from datetime import datetime
import httpx
from bs4 import BeautifulSoup

from .base import BaseScraper
from ..config import config
from ..models import GameData, Team, Player

logger = logging.getLogger("nba_scanner.scrapers.rotowire")


class LineupScraper(BaseScraper):
    """Scrapes NBA lineups from RotoWire using httpx (no Selenium)"""
    
    def __init__(self):
        super().__init__()
        self.url = config.rotowire_url
    
    async def scrape(self, client: httpx.AsyncClient, date: Optional[str] = None) -> List[GameData]:
        """Fetch and parse all NBA lineups"""
        url = self.url
        if date:
            url = f"{self.url}?date={date}"
            logger.info(f"Fetching RotoWire lineups for {date}...")
        else:
            logger.info("Fetching RotoWire lineups...")
        
        try:
            response = await self.fetch(client, url)
            html = response.text
            games = self._parse_lineups(html)
            logger.info(f"Parsed {len(games)} games")
            return games
        except Exception as e:
            logger.error(f"Failed to scrape lineups: {e}")
            return []
    
    def _parse_lineups(self, html: str) -> List[GameData]:
        """Parse HTML to extract game data"""
        soup = BeautifulSoup(html, 'html.parser')
        games = []
        
        # Find all lineup cards
        lineup_cards = soup.find_all('div', class_='lineup__box')
        
        for card in lineup_cards:
            try:
                game = self._parse_game_card(card)
                if game:
                    games.append(game)
            except Exception as e:
                logger.warning(f"Failed to parse game card: {e}")
                continue
        
        return games
    
    def _parse_game_card(self, card) -> Optional[GameData]:
        """Parse a single game card"""
        # Extract matchup info
        matchup_el = card.find('div', class_='lineup__matchup')
        if not matchup_el:
            return None
        
        # Get team abbreviations
        teams = card.find_all('div', class_='lineup__abbr')
        if len(teams) < 2:
            return None
        
        away_abbr = teams[0].get_text(strip=True)
        home_abbr = teams[1].get_text(strip=True)
        matchup = f"{away_abbr} @ {home_abbr}"
        
        # Get game time
        time_el = card.find('div', class_='lineup__time')
        game_time = time_el.get_text(strip=True) if time_el else ""
        
        # Parse both teams
        team_sections = card.find_all('ul', class_='lineup__list')
        
        away_team = self._parse_team_section(team_sections[0] if len(team_sections) > 0 else None, away_abbr)
        home_team = self._parse_team_section(team_sections[1] if len(team_sections) > 1 else None, home_abbr)
        
        return GameData(
            matchup=matchup,
            game_time=game_time,
            away_team=away_team,
            home_team=home_team,
            scraped_at=datetime.now()
        )
    
    def _parse_team_section(self, section, abbr: str) -> Team:
        """Parse a team's lineup section"""
        players = []
        injuries = []
        
        if section:
            player_items = section.find_all('li', class_='lineup__player')
            
            for item in player_items:
                name_el = item.find('a')
                name = name_el.get_text(strip=True) if name_el else "Unknown"
                
                # Check for injury status
                status = "Starting"
                status_el = item.find('span', class_='lineup__inj')
                if status_el:
                    status = status_el.get_text(strip=True)
                
                player = Player(name=name, status=status)
                players.append(player)
                
                if status in ("Out", "GTD", "Doubtful", "Questionable"):
                    injuries.append(player)
        
        return Team(
            name=abbr,
            abbreviation=abbr,
            players=players,
            injuries=injuries
        )
