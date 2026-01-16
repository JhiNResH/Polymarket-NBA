"""
NBA Data Collector - Fetches historical game data from NBA API
"""
import logging
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import pandas as pd

from nba_api.stats.endpoints import leaguegamefinder, teamestimatedmetrics
from nba_api.stats.static import teams

logger = logging.getLogger("nba_scanner.ml.data")

# Team abbreviation to ID mapping
TEAM_ABBREV_TO_ID = {team['abbreviation']: team['id'] for team in teams.get_teams()}


class NBADataCollector:
    """Collects NBA game and team stats data"""
    
    def __init__(self):
        self.team_info = {team['abbreviation']: team for team in teams.get_teams()}
    
    def get_season_games(self, season: str = "2025-26") -> pd.DataFrame:
        """
        Get all regular season games for a given season.
        
        Args:
            season: Season string like "2024-25"
            
        Returns:
            DataFrame with game results
        """
        logger.info(f"Fetching games for season {season}...")
        
        try:
            gamefinder = leaguegamefinder.LeagueGameFinder(
                season_nullable=season,
                season_type_nullable="Regular Season"
            )
            games_df = gamefinder.get_data_frames()[0]
            
            logger.info(f"Found {len(games_df)} game entries")
            return games_df
        except Exception as e:
            logger.error(f"Failed to fetch games: {e}")
            return pd.DataFrame()
    
    def get_team_stats(self, season: str = "2025-26") -> pd.DataFrame:
        """
        Get current team advanced stats (Net Rating, etc.)
        
        Returns:
            DataFrame with team metrics
        """
        logger.info(f"Fetching team stats for {season}...")
        
        try:
            metrics = teamestimatedmetrics.TeamEstimatedMetrics(season=season)
            stats_df = metrics.get_data_frames()[0]
            
            logger.info(f"Got stats for {len(stats_df)} teams")
            return stats_df
        except Exception as e:
            logger.error(f"Failed to fetch team stats: {e}")
            return pd.DataFrame()
    
    def prepare_training_data(self, games_df: pd.DataFrame) -> pd.DataFrame:
        """
        Transform raw game data into training features

        Each row = one team's game (includes both home and away)
        IMPROVED: Now includes ALL games, not just home games
        """
        if games_df.empty:
            return pd.DataFrame()

        # Use ALL games, not just home games
        all_games = games_df.copy()

        # Extract features
        all_games['WON'] = (all_games['WL'] == 'W').astype(int)
        all_games['GAME_DATE'] = pd.to_datetime(all_games['GAME_DATE'])

        # Calculate point differential (preserve original)
        all_games['POINT_DIFF'] = all_games['PTS'] - all_games['PTS'].mean()

        # Sort by date
        all_games = all_games.sort_values(['TEAM_ABBREVIATION', 'GAME_DATE'])

        # Columns to keep from box score
        keep_cols = [
            'GAME_DATE', 'TEAM_ABBREVIATION', 'MATCHUP', 'WON', 'PTS', 'POINT_DIFF',
            'AST', 'REB', 'STL', 'BLK', 'TOV',  # Box score
            'FG_PCT', 'FG3_PCT', 'FT_PCT',      # Shooting %
            'PLUS_MINUS'                         # Point margin
        ]

        # Only keep columns that exist
        available_cols = [c for c in keep_cols if c in all_games.columns]

        logger.info(f"Prepared {len(all_games)} training samples (home + away)")
        return all_games[available_cols]
    
    def collect_and_save(self, output_path: str = "nba_training_data.csv"):
        """Collect data and save to CSV"""
        # Get multiple seasons for more data
        all_games = []
        
        for season in ["2023-24", "2024-25"]:
            games = self.get_season_games(season)
            if not games.empty:
                games['SEASON'] = season
                all_games.append(games)
        
        if not all_games:
            logger.error("No data collected")
            return None
        
        combined = pd.concat(all_games, ignore_index=True)
        training_data = self.prepare_training_data(combined)
        
        if not training_data.empty:
            training_data.to_csv(output_path, index=False)
            logger.info(f"Saved {len(training_data)} rows to {output_path}")
        
        return training_data
