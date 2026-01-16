"""
Advanced Feature Engineering - Comprehensive NBA Prediction Features
"""
import logging
from typing import Dict, Optional
import pandas as pd
import numpy as np

logger = logging.getLogger("nba_scanner.ml.advanced_features")

# Team conference/division mapping
TEAM_CONFERENCE = {
    # Eastern Conference
    'ATL': 'East', 'BOS': 'East', 'BKN': 'East', 'CHA': 'East', 'CHI': 'East',
    'CLE': 'East', 'DET': 'East', 'IND': 'East', 'MIA': 'East', 'MIL': 'East',
    'NYK': 'East', 'ORL': 'East', 'PHI': 'East', 'TOR': 'East', 'WAS': 'East',
    # Western Conference
    'DAL': 'West', 'DEN': 'West', 'GSW': 'West', 'HOU': 'West', 'LAC': 'West',
    'LAL': 'West', 'MEM': 'West', 'MIN': 'West', 'NOP': 'West', 'OKC': 'West',
    'PHX': 'West', 'POR': 'West', 'SAC': 'West', 'SAS': 'West', 'UTA': 'West'
}

# Team city locations for travel distance (lat, lon)
TEAM_LOCATIONS = {
    'ATL': (33.76, -84.40), 'BOS': (42.37, -71.06), 'BKN': (40.68, -73.98),
    'CHA': (35.23, -80.84), 'CHI': (41.88, -87.63), 'CLE': (41.50, -81.69),
    'DAL': (32.79, -96.81), 'DEN': (39.75, -105.00), 'DET': (42.34, -83.05),
    'GSW': (37.77, -122.20), 'HOU': (29.76, -95.36), 'IND': (39.76, -86.16),
    'LAC': (34.04, -118.27), 'LAL': (34.04, -118.27), 'MEM': (35.14, -90.05),
    'MIA': (25.78, -80.19), 'MIL': (43.04, -87.92), 'MIN': (44.98, -93.28),
    'NOP': (29.95, -90.08), 'NYK': (40.75, -73.99), 'OKC': (35.47, -97.51),
    'ORL': (28.54, -81.38), 'PHI': (39.90, -75.17), 'PHX': (33.45, -112.07),
    'POR': (45.53, -122.67), 'SAC': (38.58, -121.50), 'SAS': (29.43, -98.44),
    'TOR': (43.64, -79.38), 'UTA': (40.77, -111.90), 'WAS': (38.90, -77.02)
}


class AdvancedFeatureEngineer:
    """Creates comprehensive features for NBA prediction"""
    
    def __init__(self):
        self.team_stats_cache = {}
    
    # Public API methods (with copy for safety)
    def add_opponent_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add opponent-related features (optimized with merge)"""
        df = df.copy()

        # Extract opponent abbreviation (vectorized) - flatten Series from extract
        df['OPPONENT'] = df['MATCHUP'].str.extract(r'(?:vs\.|@)\s*(\w+)', expand=False)

        # Select only required columns for merge to reduce memory
        merge_cols = ['TEAM_ABBREVIATION', 'GAME_DATE']
        stat_cols = []

        if 'ROLLING_WIN_RATE' in df.columns:
            stat_cols.append('ROLLING_WIN_RATE')
        if 'ROLLING_PLUS_MINUS' in df.columns:
            stat_cols.append('ROLLING_PLUS_MINUS')
        if 'TEAM_NET_RATING' in df.columns:
            stat_cols.append('TEAM_NET_RATING')

        if not stat_cols:
            logger.warning("No rolling stats available for opponent features")
            return df

        # Create team stats lookup with minimal columns
        team_stats = df[merge_cols + stat_cols].copy()

        # Rename for merge (add 'OPP_' prefix)
        rename_map = {'TEAM_ABBREVIATION': 'OPPONENT'}
        for col in stat_cols:
            rename_map[col] = f'OPP_{col}' if not col.startswith('TEAM_') else col.replace('TEAM_', 'OPP_')
        team_stats.rename(columns=rename_map, inplace=True)

        # Merge opponent stats - O(n log n) instead of O(n²)
        df = df.merge(team_stats, on=['OPPONENT', 'GAME_DATE'], how='left')

        # Vectorized fillna for all opponent columns at once
        opp_fill_defaults = {
            'OPP_ROLLING_WIN_RATE': 0.5,
            'OPP_ROLLING_PLUS_MINUS': 0,
            'OPP_NET_RATING': 0
        }
        df.fillna({k: v for k, v in opp_fill_defaults.items() if k in df.columns}, inplace=True)

        # Calculate differentials - vectorized
        if 'ROLLING_WIN_RATE' in df.columns and 'OPP_ROLLING_WIN_RATE' in df.columns:
            df['WIN_RATE_DIFF'] = df['ROLLING_WIN_RATE'] - df['OPP_ROLLING_WIN_RATE']

        if 'TEAM_NET_RATING' in df.columns and 'OPP_NET_RATING' in df.columns:
            df['NET_RATING_DIFF'] = df['TEAM_NET_RATING'] - df['OPP_NET_RATING']

        logger.info("Added opponent features: OPP_ROLLING_WIN_RATE, OPP_NET_RATING, WIN_RATE_DIFF")
        return df
    
    def add_streak_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add win/loss streak features (vectorized)"""
        df = df.copy()
        # Sorting is now handled in apply_all()

        def calculate_streak_vectorized(won_series):
            """Vectorized calculation of consecutive wins (positive) or losses (negative)"""
            won = won_series.values
            n = len(won)

            if n == 0:
                return pd.Series([], dtype=float)

            # Create streak array
            streaks = np.zeros(n, dtype=int)
            current_streak = 0

            # Vectorized approach using cumsum
            # Identify win/loss run boundaries
            is_win = won.astype(int)
            is_loss = (1 - is_win)

            # Create change points
            win_change = np.diff(is_win, prepend=is_win[0])

            # Calculate streak using groupby-like logic
            for i in range(n):
                if won[i] == 1:
                    current_streak = max(0, current_streak) + 1
                else:
                    current_streak = min(0, current_streak) - 1
                streaks[i] = current_streak

            # Shift by 1 to get streak BEFORE this game
            return pd.Series(np.concatenate([[0], streaks[:-1]]), index=won_series.index)

        df['WIN_STREAK'] = df.groupby('TEAM_ABBREVIATION', group_keys=False)['WON'].apply(calculate_streak_vectorized)

        logger.info("Added streak feature: WIN_STREAK")
        return df
    
    def add_conference_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add conference matchup features"""
        df = df.copy()
        
        df['TEAM_CONF'] = df['TEAM_ABBREVIATION'].map(TEAM_CONFERENCE)
        df['OPP_CONF'] = df['OPPONENT'].map(TEAM_CONFERENCE)
        
        # Same conference matchup (usually more competitive)
        df['SAME_CONFERENCE'] = (df['TEAM_CONF'] == df['OPP_CONF']).astype(int)
        
        logger.info("Added conference feature: SAME_CONFERENCE")
        return df
    
    def add_travel_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add travel-related features (fully vectorized)"""
        df = df.copy()

        def haversine_vectorized(lat1, lon1, lat2, lon2):
            """Vectorized Haversine distance calculation"""
            # Convert to radians (works on arrays)
            lat1, lon1, lat2, lon2 = np.radians(lat1), np.radians(lon1), np.radians(lat2), np.radians(lon2)

            # Haversine formula
            dlat = lat2 - lat1
            dlon = lon2 - lon1
            a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
            c = 2 * np.arcsin(np.sqrt(a))

            # Earth radius in miles
            return 3956 * c

        # Vectorized coordinate lookup
        df['TEAM_LAT'] = df['TEAM_ABBREVIATION'].map({k: v[0] for k, v in TEAM_LOCATIONS.items()})
        df['TEAM_LON'] = df['TEAM_ABBREVIATION'].map({k: v[1] for k, v in TEAM_LOCATIONS.items()})
        df['OPP_LAT'] = df['OPPONENT'].map({k: v[0] for k, v in TEAM_LOCATIONS.items()})
        df['OPP_LON'] = df['OPPONENT'].map({k: v[1] for k, v in TEAM_LOCATIONS.items()})

        # Calculate distances for all rows at once (vectorized)
        df['TRAVEL_DISTANCE'] = haversine_vectorized(
            df['TEAM_LAT'].fillna(0),
            df['TEAM_LON'].fillna(0),
            df['OPP_LAT'].fillna(0),
            df['OPP_LON'].fillna(0)
        )

        # Set home games to 0 distance (vectorized)
        df.loc[df['IS_HOME'] == 1, 'TRAVEL_DISTANCE'] = 0

        # Clean up temporary columns
        df.drop(['TEAM_LAT', 'TEAM_LON', 'OPP_LAT', 'OPP_LON'], axis=1, inplace=True)

        # Long road trip indicator (>1500 miles) - vectorized
        df['LONG_ROAD_TRIP'] = (df['TRAVEL_DISTANCE'] > 1500).astype(int)

        # Count consecutive away games (already optimized)
        df['IS_AWAY'] = (df['IS_HOME'] == 0).astype(int)
        df['ROAD_GAME_STREAK'] = df.groupby('TEAM_ABBREVIATION')['IS_AWAY'].transform(
            lambda x: x.groupby((x != x.shift()).cumsum()).cumsum() * x
        )
        df.drop('IS_AWAY', axis=1, inplace=True)

        logger.info("Added travel features: TRAVEL_DISTANCE, LONG_ROAD_TRIP, ROAD_GAME_STREAK")
        return df
    
    def add_season_phase_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add season phase features (vectorized)"""
        df = df.copy()
        # GAME_DATE is already datetime from apply_all()

        # Month of game
        df['GAME_MONTH'] = df['GAME_DATE'].dt.month

        # Season phase (early/mid/late) - vectorized with conditions
        conditions = [
            df['GAME_MONTH'].isin([10, 11, 12]),  # Oct-Dec: Early season
            df['GAME_MONTH'].isin([1, 2, 3]),     # Jan-Mar: Mid season
        ]
        choices = [0, 1]
        df['SEASON_PHASE'] = np.select(conditions, choices, default=2)  # Apr+: Late season

        logger.info("Added season phase features: GAME_MONTH, SEASON_PHASE")
        return df

    def add_head_to_head_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add head-to-head matchup history features"""
        df = df.copy()
        return self._add_head_to_head_features_inplace(df)

    def add_form_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add recent form features"""
        df = df.copy()
        return self._add_form_features_inplace(df)
    
    def apply_all(self, df: pd.DataFrame, inplace: bool = False) -> pd.DataFrame:
        """Apply all advanced features (optimized with single sort and minimal copies)"""
        # Single copy at the top level
        if not inplace:
            df = df.copy()

        # Sort once at the beginning instead of in each method
        df['GAME_DATE'] = pd.to_datetime(df['GAME_DATE'])
        df.sort_values(['TEAM_ABBREVIATION', 'GAME_DATE'], inplace=True)

        # Apply features in optimal order (methods now operate in-place)
        df = self._add_opponent_features_inplace(df)
        df = self._add_streak_features_inplace(df)
        df = self._add_conference_features_inplace(df)
        df = self._add_travel_features_inplace(df)
        df = self._add_season_phase_features_inplace(df)
        df = self._add_head_to_head_features_inplace(df)
        df = self._add_form_features_inplace(df)
        df = self._add_scoring_features_inplace(df)  # NEW
        return df

    def _add_opponent_features_inplace(self, df: pd.DataFrame) -> pd.DataFrame:
        """Internal method for add_opponent_features without copy"""
        # Extract opponent abbreviation (vectorized) - flatten Series from extract
        df['OPPONENT'] = df['MATCHUP'].str.extract(r'(?:vs\.|@)\s*(\w+)', expand=False)

        # Select only required columns for merge to reduce memory
        merge_cols = ['TEAM_ABBREVIATION', 'GAME_DATE']
        stat_cols = []

        if 'ROLLING_WIN_RATE' in df.columns:
            stat_cols.append('ROLLING_WIN_RATE')
        if 'ROLLING_PLUS_MINUS' in df.columns:
            stat_cols.append('ROLLING_PLUS_MINUS')
        if 'TEAM_NET_RATING' in df.columns:
            stat_cols.append('TEAM_NET_RATING')

        if not stat_cols:
            logger.warning("No rolling stats available for opponent features")
            return df

        # Create team stats lookup with minimal columns
        team_stats = df[merge_cols + stat_cols].copy()

        # Rename for merge (add 'OPP_' prefix)
        rename_map = {'TEAM_ABBREVIATION': 'OPPONENT'}
        for col in stat_cols:
            rename_map[col] = f'OPP_{col}' if not col.startswith('TEAM_') else col.replace('TEAM_', 'OPP_')
        team_stats.rename(columns=rename_map, inplace=True)

        # Merge opponent stats
        result = df.merge(team_stats, on=['OPPONENT', 'GAME_DATE'], how='left')

        # Vectorized fillna for all opponent columns at once
        opp_fill_defaults = {
            'OPP_ROLLING_WIN_RATE': 0.5,
            'OPP_ROLLING_PLUS_MINUS': 0,
            'OPP_NET_RATING': 0
        }
        result.fillna({k: v for k, v in opp_fill_defaults.items() if k in result.columns}, inplace=True)

        # Calculate differentials
        if 'ROLLING_WIN_RATE' in result.columns and 'OPP_ROLLING_WIN_RATE' in result.columns:
            result['WIN_RATE_DIFF'] = result['ROLLING_WIN_RATE'] - result['OPP_ROLLING_WIN_RATE']

        if 'TEAM_NET_RATING' in result.columns and 'OPP_NET_RATING' in result.columns:
            result['NET_RATING_DIFF'] = result['TEAM_NET_RATING'] - result['OPP_NET_RATING']

        logger.info("Added opponent features: OPP_ROLLING_WIN_RATE, OPP_NET_RATING, WIN_RATE_DIFF")
        return result

    def _add_streak_features_inplace(self, df: pd.DataFrame) -> pd.DataFrame:
        """Internal method for add_streak_features without copy"""
        def calculate_streak_vectorized(won_series):
            won = won_series.values
            n = len(won)
            if n == 0:
                return pd.Series([], dtype=float)

            streaks = np.zeros(n, dtype=int)
            current_streak = 0

            for i in range(n):
                if won[i] == 1:
                    current_streak = max(0, current_streak) + 1
                else:
                    current_streak = min(0, current_streak) - 1
                streaks[i] = current_streak

            return pd.Series(np.concatenate([[0], streaks[:-1]]), index=won_series.index)

        df['WIN_STREAK'] = df.groupby('TEAM_ABBREVIATION', group_keys=False)['WON'].apply(calculate_streak_vectorized)
        logger.info("Added streak feature: WIN_STREAK")
        return df

    def _add_conference_features_inplace(self, df: pd.DataFrame) -> pd.DataFrame:
        """Internal method for add_conference_features without copy"""
        df['TEAM_CONF'] = df['TEAM_ABBREVIATION'].map(TEAM_CONFERENCE)
        df['OPP_CONF'] = df['OPPONENT'].map(TEAM_CONFERENCE)
        df['SAME_CONFERENCE'] = (df['TEAM_CONF'] == df['OPP_CONF']).astype(int)
        logger.info("Added conference feature: SAME_CONFERENCE")
        return df

    def _add_travel_features_inplace(self, df: pd.DataFrame) -> pd.DataFrame:
        """Internal method for add_travel_features without copy"""
        def haversine_vectorized(lat1, lon1, lat2, lon2):
            lat1, lon1, lat2, lon2 = np.radians(lat1), np.radians(lon1), np.radians(lat2), np.radians(lon2)
            dlat = lat2 - lat1
            dlon = lon2 - lon1
            a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
            c = 2 * np.arcsin(np.sqrt(a))
            return 3956 * c

        # Vectorized coordinate lookup
        df['TEAM_LAT'] = df['TEAM_ABBREVIATION'].map({k: v[0] for k, v in TEAM_LOCATIONS.items()})
        df['TEAM_LON'] = df['TEAM_ABBREVIATION'].map({k: v[1] for k, v in TEAM_LOCATIONS.items()})
        df['OPP_LAT'] = df['OPPONENT'].map({k: v[0] for k, v in TEAM_LOCATIONS.items()})
        df['OPP_LON'] = df['OPPONENT'].map({k: v[1] for k, v in TEAM_LOCATIONS.items()})

        # Calculate distances
        df['TRAVEL_DISTANCE'] = haversine_vectorized(
            df['TEAM_LAT'].fillna(0), df['TEAM_LON'].fillna(0),
            df['OPP_LAT'].fillna(0), df['OPP_LON'].fillna(0)
        )
        df.loc[df['IS_HOME'] == 1, 'TRAVEL_DISTANCE'] = 0
        df.drop(['TEAM_LAT', 'TEAM_LON', 'OPP_LAT', 'OPP_LON'], axis=1, inplace=True)

        # Long road trip
        df['LONG_ROAD_TRIP'] = (df['TRAVEL_DISTANCE'] > 1500).astype(int)

        # Road game streak
        df['IS_AWAY'] = (df['IS_HOME'] == 0).astype(int)
        df['ROAD_GAME_STREAK'] = df.groupby('TEAM_ABBREVIATION')['IS_AWAY'].transform(
            lambda x: x.groupby((x != x.shift()).cumsum()).cumsum() * x
        )
        df.drop('IS_AWAY', axis=1, inplace=True)

        logger.info("Added travel features: TRAVEL_DISTANCE, LONG_ROAD_TRIP, ROAD_GAME_STREAK")
        return df

    def _add_season_phase_features_inplace(self, df: pd.DataFrame) -> pd.DataFrame:
        """Internal method for add_season_phase_features without copy"""
        df['GAME_MONTH'] = df['GAME_DATE'].dt.month
        conditions = [
            df['GAME_MONTH'].isin([10, 11, 12]),
            df['GAME_MONTH'].isin([1, 2, 3]),
        ]
        df['SEASON_PHASE'] = np.select(conditions, [0, 1], default=2)
        logger.info("Added season phase features: GAME_MONTH, SEASON_PHASE")
        return df

    def _add_head_to_head_features_inplace(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add head-to-head matchup history features (vectorized)"""
        # Create matchup key for grouping (sorted to ensure A vs B = B vs A)
        df['MATCHUP_KEY'] = df.apply(
            lambda r: tuple(sorted([r['TEAM_ABBREVIATION'], r['OPPONENT']])), axis=1
        ).astype(str)

        # Calculate rolling H2H win rate per team-opponent pair
        # Group by team + opponent, then calculate rolling mean with shift
        def calc_h2h_win_rate(group):
            """Calculate H2H win rate from previous games against this opponent"""
            # Rolling mean of last 3 games, shifted to exclude current game
            return group['WON'].rolling(window=3, min_periods=1).mean().shift(1)

        # Group by team and opponent combination
        df['H2H_WIN_RATE'] = df.groupby(
            ['TEAM_ABBREVIATION', 'OPPONENT'], group_keys=False
        ).apply(calc_h2h_win_rate)

        # Fill NaN (first matchup) with 0.5
        df['H2H_WIN_RATE'] = df['H2H_WIN_RATE'].fillna(0.5)

        # Clean up temporary column
        df.drop('MATCHUP_KEY', axis=1, inplace=True)

        logger.info("Added head-to-head features: H2H_WIN_RATE")
        return df

    def _add_form_features_inplace(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add recent form features (last 3 and 5 games)"""
        # Last 3 games form
        df['FORM_L3'] = df.groupby('TEAM_ABBREVIATION')['WON'].transform(
            lambda x: x.rolling(window=3, min_periods=1).mean().shift(1)
        )

        # Last 5 games form
        df['FORM_L5'] = df.groupby('TEAM_ABBREVIATION')['WON'].transform(
            lambda x: x.rolling(window=5, min_periods=1).mean().shift(1)
        )

        # Momentum (difference between L3 and L5 form)
        df['MOMENTUM'] = df['FORM_L3'] - df['FORM_L5']

        # Fill NaN with neutral values
        df['FORM_L3'] = df['FORM_L3'].fillna(0.5)
        df['FORM_L5'] = df['FORM_L5'].fillna(0.5)
        df['MOMENTUM'] = df['MOMENTUM'].fillna(0)

        # Add opponent form features via merge
        form_cols = ['TEAM_ABBREVIATION', 'GAME_DATE', 'FORM_L3', 'FORM_L5']
        opp_form = df[form_cols].copy()
        opp_form.rename(columns={
            'TEAM_ABBREVIATION': 'OPPONENT',
            'FORM_L3': 'OPP_FORM_L3',
            'FORM_L5': 'OPP_FORM_L5'
        }, inplace=True)

        df = df.merge(opp_form, on=['OPPONENT', 'GAME_DATE'], how='left')
        df['OPP_FORM_L3'] = df['OPP_FORM_L3'].fillna(0.5)
        df['OPP_FORM_L5'] = df['OPP_FORM_L5'].fillna(0.5)

        # Form differential (how much better/worse our form is vs opponent)
        df['FORM_DIFF'] = df['FORM_L3'] - df['OPP_FORM_L3']

        logger.info("Added form features: FORM_L3, FORM_L5, MOMENTUM, OPP_FORM_L3, OPP_FORM_L5, FORM_DIFF")
        return df

    def _add_scoring_features_inplace(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add scoring trend features"""
        # Rolling scoring average (last 5 games)
        if 'PTS' in df.columns:
            df['ROLLING_PTS_L5'] = df.groupby('TEAM_ABBREVIATION')['PTS'].transform(
                lambda x: x.rolling(window=5, min_periods=1).mean().shift(1)
            )
            df['ROLLING_PTS_L5'] = df['ROLLING_PTS_L5'].fillna(df['PTS'].mean())

            # Scoring trend (are we scoring more or less recently?)
            df['ROLLING_PTS_L3'] = df.groupby('TEAM_ABBREVIATION')['PTS'].transform(
                lambda x: x.rolling(window=3, min_periods=1).mean().shift(1)
            )
            df['SCORING_TREND'] = df['ROLLING_PTS_L3'] - df['ROLLING_PTS_L5']
            df['SCORING_TREND'] = df['SCORING_TREND'].fillna(0)

            # Clean up
            df.drop('ROLLING_PTS_L3', axis=1, inplace=True)

            logger.info("Added scoring features: ROLLING_PTS_L5, SCORING_TREND")

        return df
