"""
Hybrid EV Calculator - Combines ML predictions with Gemini analysis
"""
import logging
from typing import Dict, Optional, List
import pandas as pd

from .model import NBAPredictor
from .spread_model import SpreadPredictor
from ..models import GameData, EVResult, OddsData
from ..config import config

logger = logging.getLogger("nba_scanner.ml.hybrid")


class HybridCalculator:
    """
    Hybrid predictor that combines:
    1. XGBoost ML model for win probability
    2. Spread Model for margin prediction
    3. Polymarket odds for EV calculation
    """
    
    def __init__(self):
        self.ml_model = NBAPredictor()
        self.spread_model = SpreadPredictor()
        # Initialize data structures
        self.team_stats = pd.DataFrame()
        self.net_rating_lookup = {}
        self.games_df = pd.DataFrame()
        
        # Load data
        self._load_data()
    
    def _load_data(self):
        """Load team stats and game history"""
        try:
            from .data_collector import NBADataCollector
            collector = NBADataCollector()
            
            # Load team stats
            self.team_stats = collector.get_team_stats("2025-26")
            if not self.team_stats.empty and 'E_NET_RATING' in self.team_stats.columns:
                self.net_rating_lookup = self.team_stats.set_index('TEAM_NAME')['E_NET_RATING'].to_dict()
                
            # Load game history for streaks/rest
            self.games_df = collector.get_season_games("2025-26")
            if not self.games_df.empty:
                # Pre-process dates
                self.games_df['GAME_DATE'] = pd.to_datetime(self.games_df['GAME_DATE'])
                self.games_df = self.games_df.sort_values('GAME_DATE')
                
            logger.info(f"Loaded stats for {len(self.net_rating_lookup)} teams and {len(self.games_df)} historical games")
            
        except Exception as e:
            logger.warning(f"Could not load ML data: {e}")

    def _get_team_metrics(self, team_abbrev: str) -> Dict:
        """Calculate dynamic metrics for a team based on game history"""
        metrics = {
            'IS_B2B': 0,
            'DAYS_REST': 2,
            'WIN_STREAK': 0,
            'FORM_L3': 0.5,
            'FORM_L5': 0.5
        }
        
        if self.games_df.empty:
            return metrics
            
        # Filter games for this team
        team_games = self.games_df[self.games_df['TEAM_ABBREVIATION'] == team_abbrev].copy()
        if team_games.empty:
            return metrics
            
        # Get last game date
        last_game = team_games.iloc[-1]
        last_date = last_game['GAME_DATE']
        today = pd.Timestamp.now()
        
        # Calculate rest days (days since last game)
        days_since_last = (today - last_date).days
        metrics['DAYS_REST'] = min(days_since_last, 7) # Cap at 7
        metrics['IS_B2B'] = 1 if days_since_last <= 1 else 0
        
        # Calculate streak
        # Get recent wins/losses
        recent_results = team_games['WL'].tail(10).values
        current_streak = 0
        if len(recent_results) > 0:
            last_result = recent_results[-1]
            if last_result == 'W':
                for res in reversed(recent_results):
                    if res == 'W': current_streak += 1
                    else: break
            elif last_result == 'L':
                for res in reversed(recent_results):
                    if res == 'L': current_streak -= 1
                    else: break
        metrics['WIN_STREAK'] = current_streak
        
        # Calculate recent form (Win Rate L3/L5)
        # Convert W/L to 1/0
        numeric_results = team_games['WL'].map({'W': 1, 'L': 0}).dropna()
        if len(numeric_results) >= 3:
            metrics['FORM_L3'] = numeric_results.tail(3).mean()
        if len(numeric_results) >= 5:
            metrics['FORM_L5'] = numeric_results.tail(5).mean()
            
        return metrics

    def predict_game(
        self,
        game: GameData,
        odds: Optional[Dict[str, OddsData]] = None
    ) -> EVResult:
        """
        Predict game outcome and calculate EV.
        
        Uses ML model for win probability and Spread model for margin.
        """
        if self.ml_model.model is None:
            logger.warning("ML model not loaded, using fallback")
            return self._create_fallback_result(game)
        
        # Build features for home team perspective
        home_features = self._build_features(game, is_home=True)
        
        try:
            # 1. Moneyline Prediction
            home_win_prob = self.ml_model.predict_win_prob(home_features)
            away_win_prob = 1 - home_win_prob
            
            # 2. Spread Prediction (Point Margin)
            # Positive = Home wins by X, Negative = Away wins by X
            pred_margin = self.spread_model.predict_single(home_features) if self.spread_model.model else 0.0
            

            
            # Get market odds
            home_market_prob = None
            away_market_prob = None
            market_spread = None # Home team spread

            # Manual Injury Overrides (Quick fix for user feedback)
            # If a key player is OUT, penalize the team's win probability significantly
            MANUAL_INJURY_OVERRIDES = {
                'NYK': {'player': 'Jalen Brunson', 'impact': 0.15},  # -15% win prob
                 # Add more as needed
            }
            
            # Apply penalties
            if game.home_team.abbreviation in MANUAL_INJURY_OVERRIDES:
                override = MANUAL_INJURY_OVERRIDES[game.home_team.abbreviation]
                logger.info(f"⚠️ Applying injury penalty for {game.home_team.name}: {override['player']} OUT (-{override['impact']:.0%})")
                home_win_prob -= override['impact']
                away_win_prob += override['impact']
                
            if game.away_team.abbreviation in MANUAL_INJURY_OVERRIDES:
                override = MANUAL_INJURY_OVERRIDES[game.away_team.abbreviation]
                logger.info(f"⚠️ Applying injury penalty for {game.away_team.name}: {override['player']} OUT (-{override['impact']:.0%})")
                away_win_prob -= override['impact']
                home_win_prob += override['impact']

            # Re-normalize to 0-1 range
            home_win_prob = max(0.01, min(0.99, home_win_prob))
            away_win_prob = 1 - home_win_prob   
            
            if odds:
                home_odds = odds.get(game.home_team.abbreviation)
                away_odds = odds.get(game.away_team.abbreviation)
                
                if home_odds and home_odds.moneyline_prob:
                    home_market_prob = home_odds.moneyline_prob
                if away_odds and away_odds.moneyline_prob:
                    away_market_prob = away_odds.moneyline_prob
                
                # Try to get spread line
                if home_odds and home_odds.spread_line:
                    market_spread = home_odds.spread_line
                elif away_odds and away_odds.spread_line:
                    market_spread = -away_odds.spread_line
            
            # Calculate ML edge
            home_edge = 0
            away_edge = 0
            
            if home_market_prob:
                home_edge = home_win_prob - home_market_prob
            if away_market_prob:
                away_edge = away_win_prob - away_market_prob
            
            # Determine best bet (ML)
            best_bet_raw = "PASS"
            ev = 0
            
            if home_edge > away_edge and home_edge > 0.05:
                best_bet_raw = "HOME_ML"
                ev = home_edge
            elif away_edge > home_edge and away_edge > 0.05:
                best_bet_raw = "AWAY_ML"
                ev = away_edge
                
            # Spread Overlay
            # If we predict Home wins by 10 (margin=10) and Market is Home -5.5
            # We cover by 4.5 points.
            spread_bet = None
            spread_ev = 0
            
            if market_spread is not None:
                # Calculate "Coverage"
                # If Market is -5.5 (Home -5.5), we need Margin > 5.5
                # Prediction - MarketLine
                coverage = pred_margin + market_spread # Logic check: if market is -5, we need pred > 5. 
                # Wait. If Market is -5.5. Pred is 10. 10 > 5.5.
                # If Market is +5.5 (Home Underdog). Pred is -2 (lose by 2). -2 > -5.5? Yes.
                # Actually, standard logic:
                # Margin + SpreadLine > 0 ==> Home Covers?
                # If Line is -5.5. Score is 100-90 (+10). 10 + (-5.5) = 4.5 > 0. Yes.
                # If Line is +5.5. Score is 90-100 (-10). -10 + 5.5 = -4.5 < 0. No cover.
                
                coverage = pred_margin + market_spread
                
                # Threshold of 2.5 points edge for spread bet
                if coverage > 2.5:
                    spread_bet = "HOME_SPREAD"
                    spread_ev = coverage / 20.0 # Approximate EV from point edge (5pts ~ 25% edge?)
                elif coverage < -2.5:
                    spread_bet = "AWAY_SPREAD"
                    spread_ev = -coverage / 20.0
            
            # Decision Logic: Prioritize high EV
            # If ML is PASS, check Spread
            if best_bet_raw == "PASS" and spread_bet:
                best_bet_raw = spread_bet
                ev = spread_ev
            
            # Confidence logic
            confidence = "HIGH" if ev > 0.10 else "MEDIUM"
            if ev < 0.05: confidence = "LOW"
            
            # Convert bet to display name
            best_bet = self._convert_bet_display(game, best_bet_raw)
            if market_spread and "SPREAD" in best_bet_raw:
                line_str = f"{market_spread:+.1f}" if best_bet_raw == "HOME_SPREAD" else f"{-market_spread:+.1f}"
                best_bet += f" ({line_str})"
            
            # Build analysis text
            analysis = f"""📊 ML Model Analysis

**ML 預測勝率:**
- {game.home_team.name}: {home_win_prob*100:.1f}%
- {game.away_team.name}: {away_win_prob*100:.1f}%

**Spread 預測:**
- 預測分差: {pred_margin:+.1f} (正=主勝)
- 市場盤口: {f"{market_spread:+.1f}" if market_spread else "N/A"}

**Edge:**
- ML Edge: {max(home_edge, away_edge)*100:+.1f}%
- Spread Edge: {ev*100:+.1f}% (Approx)

**建議:** {best_bet} (EV: {ev*100:+.1f}%)
"""
            
            return EVResult(
                game=game,
                ev=ev,
                best_bet=best_bet,
                best_bet_raw=best_bet_raw,
                confidence=confidence,
                analysis=analysis,
                has_signal=ev >= config.ev_threshold and best_bet_raw != "PASS"
            )
            
        except Exception as e:
            logger.error(f"ML prediction failed for {game.matchup}: {e}")
            return self._create_fallback_result(game)
    
    def _build_features(self, game: GameData, is_home: bool) -> Dict:
        """Build feature dict for ML model - provides all 34 features (updated)"""
        team = game.home_team if is_home else game.away_team
        opponent = game.away_team if is_home else game.home_team
        
        # Map abbreviation to full team name for net rating lookup
        abbrev_to_name = {
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
        
        # Conference mapping
        east_teams = ['ATL', 'BOS', 'BKN', 'CHA', 'CHI', 'CLE', 'DET', 'IND', 'MIA', 'MIL', 'NYK', 'ORL', 'PHI', 'TOR', 'WAS']
        
        team_name = abbrev_to_name.get(team.abbreviation, '')
        opp_name = abbrev_to_name.get(opponent.abbreviation, '')
        
        team_net_rating = self.net_rating_lookup.get(team_name, 0)
        opp_net_rating = self.net_rating_lookup.get(opp_name, 0)
        
        # Get dynamic metrics from history
        team_metrics = self._get_team_metrics(team.abbreviation)
        opp_metrics = self._get_team_metrics(opponent.abbreviation)
        
        # Use lineup_strength as baseline for rolling win rate, adjust with form
        # Weight: 60% Lineup Strength, 40% Recent Form
        team_win_rate = (team.lineup_strength * 0.6) + (team_metrics['FORM_L5'] * 0.4)
        opp_win_rate = (opponent.lineup_strength * 0.6) + (opp_metrics['FORM_L5'] * 0.4)
        
        # Conference check
        team_conf = 'East' if team.abbreviation in east_teams else 'West'
        opp_conf = 'East' if opponent.abbreviation in east_teams else 'West'
        
        # Calculate feature values
        win_rate_diff = team_win_rate - opp_win_rate
        net_rating_diff = team_net_rating - opp_net_rating
        
        is_home_val = 1 if is_home else 0
        is_b2b_val = team_metrics['IS_B2B']
        
        # Return all features
        features = {
            # Basic (3)
            'IS_HOME': is_home_val,
            'IS_B2B': is_b2b_val,
            'DAYS_REST': team_metrics['DAYS_REST'],

            # Rolling performance (10)
            'ROLLING_WIN_RATE': team_win_rate,
            'ROLLING_PTS': 110 + (team_net_rating * 0.5), # Estimate
            'ROLLING_AST': 25,  # League average
            'ROLLING_REB': 44,  # League average
            'ROLLING_STL': 7.5,
            'ROLLING_BLK': 5,
            'ROLLING_TOV': 14,
            'ROLLING_FG_PCT': 0.47,
            'ROLLING_FG3_PCT': 0.36,
            'ROLLING_PLUS_MINUS': team_net_rating * 1.5, # Adjusted estimate

            # Team strength (1)
            'TEAM_NET_RATING': team_net_rating,

            # Opponent features (5)
            'OPP_ROLLING_WIN_RATE': opp_win_rate,
            'OPP_ROLLING_PLUS_MINUS': opp_net_rating * 1.5,
            'OPP_NET_RATING': opp_net_rating,
            'WIN_RATE_DIFF': win_rate_diff,
            'NET_RATING_DIFF': net_rating_diff,

            # Streak (1)
            'WIN_STREAK': team_metrics['WIN_STREAK'],

            # Conference (1)
            'SAME_CONFERENCE': 1 if team_conf == opp_conf else 0,

            # Travel (3)
            'TRAVEL_DISTANCE': 0 if is_home else 500,  # Could be improved with lat/lon lookup
            'LONG_ROAD_TRIP': 0,
            'ROAD_GAME_STREAK': 0 if is_home else 1,

            # Season phase (1)
            'SEASON_PHASE': 1,  # Mid-season default

            # Head-to-head (1)
            'H2H_WIN_RATE': 0.5,

            # Recent form (3)
            'FORM_L3': team_metrics['FORM_L3'],
            'FORM_L5': team_metrics['FORM_L5'],
            'MOMENTUM': team_metrics['FORM_L3'] - team_metrics['FORM_L5']
        }

        # Opponent form features (3)
        features['OPP_FORM_L3'] = opp_metrics['FORM_L3']
        features['OPP_FORM_L5'] = opp_metrics['FORM_L5']
        features['FORM_DIFF'] = team_metrics['FORM_L3'] - opp_metrics['FORM_L3']

        # Scoring trends (2)
        features['ROLLING_PTS_L5'] = 110 + (team_net_rating * 0.5)
        features['SCORING_TREND'] = 0  # Would need more data

        # Feature interactions (8)
        features['HOME_X_STRENGTH'] = is_home_val * win_rate_diff
        features['B2B_X_FORM'] = is_b2b_val * team_win_rate
        features['TRAVEL_X_B2B'] = (features['TRAVEL_DISTANCE'] / 1000) * is_b2b_val
        features['STRENGTH_PRODUCT'] = win_rate_diff * net_rating_diff
        features['FORM_X_H2H'] = features['FORM_L3'] * features['H2H_WIN_RATE']
        features['FORM_DIFF_X_HOME'] = features['FORM_DIFF'] * is_home_val
        features['STREAK_X_FORM'] = team_metrics['WIN_STREAK'] * team_metrics['FORM_L3']
        features['SCORING_X_HOME'] = features['SCORING_TREND'] * is_home_val

        return features
    
    def _convert_bet_display(self, game: GameData, bet_raw: str) -> str:
        """Convert bet code to display name"""
        if bet_raw == "AWAY_ML":
            return f"{game.away_team.name} ML"
        elif bet_raw == "HOME_ML":
            return f"{game.home_team.name} ML"
        elif bet_raw == "AWAY_SPREAD":
            return f"{game.away_team.name} SPREAD"
        elif bet_raw == "HOME_SPREAD":
            return f"{game.home_team.name} SPREAD"
        return bet_raw
    
    def _create_fallback_result(self, game: GameData) -> EVResult:
        """Create fallback result when prediction fails"""
        return EVResult(
            game=game,
            ev=0,
            best_bet="PASS",
            best_bet_raw="PASS",
            confidence="LOW",
            analysis="ML 模型分析不可用",
            has_signal=False
        )
    
    async def analyze_batch(
        self,
        games: List[GameData],
        odds: Dict[str, OddsData]
    ) -> List[EVResult]:
        """Analyze multiple games"""
        results = []
        for game in games:
            # Skip games with extreme odds (likely finished)
            away_odds = odds.get(game.away_team.abbreviation)
            home_odds = odds.get(game.home_team.abbreviation)
            
            skip_game = False
            for team_odds in [away_odds, home_odds]:
                if team_odds and team_odds.moneyline_prob is not None:
                    if team_odds.moneyline_prob >= 0.95 or team_odds.moneyline_prob <= 0.05:
                        logger.warning(f"跳過 {game.matchup}: 賠率異常 - 比賽可能已結束")
                        skip_game = True
                        break
            
            if skip_game:
                results.append(self._create_fallback_result(game))
                continue
            
            result = self.predict_game(game, odds)
            results.append(result)
            logger.info(f"✅ {game.matchup}: ML_EV={result.ev*100:+.1f}% | {result.best_bet}")
        
        return results
