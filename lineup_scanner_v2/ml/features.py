"""
Feature Engineering for NBA Game Prediction
"""
import logging
from typing import Dict, Optional
import pandas as pd
import numpy as np

logger = logging.getLogger("nba_scanner.ml.features")

# Team abbreviation to full name mapping (module-level constant)
TEAM_ABBREV_TO_NAME = {
    'ATL': 'Atlanta Hawks', 'BOS': 'Boston Celtics', 'BKN': 'Brooklyn Nets',
    'CHA': 'Charlotte Hornets', 'CHI': 'Chicago Bulls', 'CLE': 'Cleveland Cavaliers',
    'DAL': 'Dallas Mavericks', 'DEN': 'Denver Nuggets', 'DET': 'Detroit Pistons',
    'GSW': 'Golden State Warriors', 'HOU': 'Houston Rockets', 'IND': 'Indiana Pacers',
    'LAC': 'LA Clippers', 'LAL': 'Los Angeles Lakers', 'MEM': 'Memphis Grizzlies',
    'MIA': 'Miami Heat', 'MIL': 'Milwaukee Bucks', 'MIN': 'Minnesota Timberwolves',
    'NOP': 'New Orleans Pelicans', 'NYK': 'New York Knicks', 'OKC': 'Oklahoma City Thunder',
    'ORL': 'Orlando Magic', 'PHI': 'Philadelphia 76ers', 'PHX': 'Phoenix Suns',
    'POR': 'Portland Trail Blazers', 'SAC': 'Sacramento Kings', 'SAS': 'San Antonio Spurs',
    'TOR': 'Toronto Raptors', 'UTA': 'Utah Jazz', 'WAS': 'Washington Wizards'
}


class FeatureEngineer:
    """Creates features for NBA game prediction"""
    
    def __init__(self):
        self.team_stats: Dict[str, Dict] = {}
    
    def calculate_rolling_stats(
        self,
        games_df: pd.DataFrame,
        window: int = 10
    ) -> pd.DataFrame:
        """
        Calculate rolling statistics for each team (optimized).

        Features:
        - Rolling win rate (last N games)
        - Rolling box score stats
        - Shooting percentages
        """
        if games_df.empty:
            return games_df

        df = games_df.copy()
        df = df.sort_values(['TEAM_ABBREVIATION', 'GAME_DATE'])

        # Define rolling stats to calculate
        rolling_stats = {
            'WON': 'ROLLING_WIN_RATE',
            'PTS': 'ROLLING_PTS',
            'AST': 'ROLLING_AST',
            'REB': 'ROLLING_REB',
            'STL': 'ROLLING_STL',
            'BLK': 'ROLLING_BLK',
            'TOV': 'ROLLING_TOV',
            'FG_PCT': 'ROLLING_FG_PCT',
            'FG3_PCT': 'ROLLING_FG3_PCT',
            'PLUS_MINUS': 'ROLLING_PLUS_MINUS'
        }

        # Filter only existing columns
        existing_cols = [src for src in rolling_stats.keys() if src in df.columns]

        # Single groupby operation for all rolling calculations
        # CRITICAL: shift(1) to avoid data leakage - use stats BEFORE current game
        if existing_cols:
            grouped = df.groupby('TEAM_ABBREVIATION')[existing_cols]
            rolling_result = grouped.transform(
                lambda x: x.rolling(window=window, min_periods=3).mean().shift(1)
            )

            # Rename columns and fill NaN
            for src_col in existing_cols:
                dest_col = rolling_stats[src_col]
                df[dest_col] = rolling_result[src_col].fillna(df[src_col].mean())

        logger.info(f"Calculated {len(existing_cols)} rolling stats with window={window}")
        return df
    
    def add_matchup_features(
        self,
        df: pd.DataFrame,
        team_stats: Optional[pd.DataFrame] = None
    ) -> pd.DataFrame:
        """
        Add matchup-specific features (optimized).

        - Home court advantage indicator
        - Team strength difference
        - Back-to-back flag
        """
        df = df.copy()

        # Home court - vectorized string operation
        df['IS_HOME'] = df['MATCHUP'].str.contains('vs.', regex=False).astype(int)

        # Extract opponent - vectorized with regex
        df['OPPONENT'] = df['MATCHUP'].str.extract(r'(?:vs\.|@)\s*(\w+)')[0]

        # Back-to-back detection
        df['GAME_DATE'] = pd.to_datetime(df['GAME_DATE'])
        df = df.sort_values(['TEAM_ABBREVIATION', 'GAME_DATE'])

        df['DAYS_REST'] = df.groupby('TEAM_ABBREVIATION')['GAME_DATE'].diff().dt.days
        df['IS_B2B'] = (df['DAYS_REST'] == 1).astype(int)
        df['IS_B2B'] = df['IS_B2B'].fillna(0)

        # If we have team stats, add strength differential
        if team_stats is not None and not team_stats.empty:
            if 'E_NET_RATING' in team_stats.columns:
                # Create team name to net rating lookup
                team_name_to_rating = team_stats.set_index('TEAM_NAME')['E_NET_RATING'].to_dict()

                # Use module-level constant and vectorized map operation
                # Create abbrev -> net rating mapping
                abbrev_to_rating = {
                    abbrev: team_name_to_rating.get(name, 0)
                    for abbrev, name in TEAM_ABBREV_TO_NAME.items()
                }

                # Vectorized mapping (much faster than apply)
                df['TEAM_NET_RATING'] = df['TEAM_ABBREVIATION'].map(abbrev_to_rating).fillna(0)

        return df
    
    def prepare_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Prepare final feature set for training.

        Returns DataFrame with features and target.
        """
        # Input validation
        if df.empty:
            raise ValueError("Input DataFrame is empty")

        required_cols = ['TEAM_ABBREVIATION', 'WON']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            raise ValueError(f"Missing required columns: {missing_cols}")

        # All possible features
        feature_cols = [
            # Basic
            'IS_HOME',
            'IS_B2B',
            'DAYS_REST',

            # Rolling performance (10 game window)
            'ROLLING_WIN_RATE',
            'ROLLING_PTS',
            'ROLLING_AST',
            'ROLLING_REB',
            'ROLLING_STL',
            'ROLLING_BLK',
            'ROLLING_TOV',
            'ROLLING_FG_PCT',
            'ROLLING_FG3_PCT',
            'ROLLING_PLUS_MINUS',

            # Team strength
            'TEAM_NET_RATING',

            # Opponent features
            'OPP_ROLLING_WIN_RATE',
            'OPP_ROLLING_PLUS_MINUS',
            'OPP_NET_RATING',
            'WIN_RATE_DIFF',
            'NET_RATING_DIFF',

            # Streak features
            'WIN_STREAK',

            # Conference
            'SAME_CONFERENCE',

            # Travel
            'TRAVEL_DISTANCE',
            'LONG_ROAD_TRIP',
            'ROAD_GAME_STREAK',

            # Season phase
            'SEASON_PHASE',

            # Head-to-head
            'H2H_WIN_RATE',

            # Recent form
            'FORM_L3',
            'FORM_L5',
            'MOMENTUM',

            # Opponent form
            'OPP_FORM_L3',
            'OPP_FORM_L5',
            'FORM_DIFF',

            # Scoring trends
            'ROLLING_PTS_L5',
            'SCORING_TREND',
        ]
        
        # Only use features that exist in dataframe
        available_features = [c for c in feature_cols if c in df.columns]

        # Only keep rows with all features
        df_clean = df.dropna(subset=available_features + ['WON']).copy()

        # Create feature interactions for XGBoost
        # These capture non-linear relationships
        if 'IS_HOME' in df_clean.columns and 'WIN_RATE_DIFF' in df_clean.columns:
            df_clean['HOME_X_STRENGTH'] = df_clean['IS_HOME'] * df_clean['WIN_RATE_DIFF']
            available_features.append('HOME_X_STRENGTH')

        if 'IS_B2B' in df_clean.columns and 'ROLLING_WIN_RATE' in df_clean.columns:
            df_clean['B2B_X_FORM'] = df_clean['IS_B2B'] * df_clean['ROLLING_WIN_RATE']
            available_features.append('B2B_X_FORM')

        if 'TRAVEL_DISTANCE' in df_clean.columns and 'IS_B2B' in df_clean.columns:
            df_clean['TRAVEL_X_B2B'] = (df_clean['TRAVEL_DISTANCE'] / 1000) * df_clean['IS_B2B']
            available_features.append('TRAVEL_X_B2B')

        if 'WIN_RATE_DIFF' in df_clean.columns and 'NET_RATING_DIFF' in df_clean.columns:
            df_clean['STRENGTH_PRODUCT'] = df_clean['WIN_RATE_DIFF'] * df_clean['NET_RATING_DIFF']
            available_features.append('STRENGTH_PRODUCT')

        if 'FORM_L3' in df_clean.columns and 'H2H_WIN_RATE' in df_clean.columns:
            df_clean['FORM_X_H2H'] = df_clean['FORM_L3'] * df_clean['H2H_WIN_RATE']
            available_features.append('FORM_X_H2H')

        # Form differential interaction with home court
        if 'FORM_DIFF' in df_clean.columns and 'IS_HOME' in df_clean.columns:
            df_clean['FORM_DIFF_X_HOME'] = df_clean['FORM_DIFF'] * df_clean['IS_HOME']
            available_features.append('FORM_DIFF_X_HOME')

        # Streak interaction with form
        if 'WIN_STREAK' in df_clean.columns and 'FORM_L3' in df_clean.columns:
            df_clean['STREAK_X_FORM'] = df_clean['WIN_STREAK'] * df_clean['FORM_L3']
            available_features.append('STREAK_X_FORM')

        # Scoring trend with home court
        if 'SCORING_TREND' in df_clean.columns and 'IS_HOME' in df_clean.columns:
            df_clean['SCORING_X_HOME'] = df_clean['SCORING_TREND'] * df_clean['IS_HOME']
            available_features.append('SCORING_X_HOME')

        X = df_clean[available_features]
        y = df_clean['WON']

        n_interactions = sum(1 for f in available_features if '_X_' in f)
        logger.info(f"Prepared {len(X)} samples with {len(available_features)} features (including {n_interactions} interactions)")
        logger.info(f"Feature list: {available_features}")
        return X, y, df_clean
