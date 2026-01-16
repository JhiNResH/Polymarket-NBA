#!/usr/bin/env python3
"""
Backtesting Script for NBA ML Model
====================================
Evaluates model performance on historical data

Usage:
    python -m lineup_scanner_v2.ml.backtest
"""
import logging
import pandas as pd
import numpy as np

from .data_collector import NBADataCollector
from .features import FeatureEngineer
from .model import NBAPredictor

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("backtest")


def simulate_betting(predictions: np.ndarray, actuals: np.ndarray, odds_implied: float = 0.50):
    """
    Simulate flat betting strategy.
    
    Args:
        predictions: Model predicted probabilities
        actuals: Actual outcomes (0 or 1)
        odds_implied: Implied probability from bookmaker (default 50%)
    
    Returns:
        Betting simulation results
    """
    # Only bet when model confidence > threshold
    threshold = 0.55
    bet_mask = predictions >= threshold
    
    bets = bet_mask.sum()
    if bets == 0:
        return {"bets": 0, "wins": 0, "roi": 0}
    
    # Simulate $100 flat bets at -110 odds (90.9% payout)
    wins = (actuals[bet_mask] == 1).sum()
    losses = bets - wins
    
    profit = wins * 90.91 - losses * 100
    roi = (profit / (bets * 100)) * 100
    
    return {
        "bets": int(bets),
        "wins": int(wins),
        "losses": int(losses),
        "win_rate": wins / bets * 100,
        "profit": profit,
        "roi": roi
    }


def main():
    logger.info("="*50)
    logger.info("🏀 NBA ML Model Backtesting")
    logger.info("="*50)
    
    # Load data
    logger.info("\n📥 Loading historical data...")
    collector = NBADataCollector()
    
    games_24 = collector.get_season_games("2024-25")
    games_23 = collector.get_season_games("2023-24")
    
    all_games = pd.concat([games_23, games_24], ignore_index=True)
    team_stats = collector.get_team_stats("2024-25")
    
    # Feature engineering
    logger.info("\n🔧 Feature engineering...")
    engineer = FeatureEngineer()
    df = collector.prepare_training_data(all_games)
    df = engineer.calculate_rolling_stats(df, window=10)
    df = engineer.add_matchup_features(df, team_stats)
    
    X, y, df_final = engineer.prepare_features(df)
    
    logger.info(f"Total samples: {len(X)}")
    
    # Load trained model
    logger.info("\n📊 Loading model...")
    model = NBAPredictor()
    
    if model.model is None:
        logger.error("Model not found! Run training first.")
        return
    
    # Make predictions on all data
    logger.info("\n🎯 Running predictions...")
    predictions = model.predict_proba(X)[:, 1]
    
    # Overall accuracy
    pred_outcomes = (predictions >= 0.5).astype(int)
    accuracy = (pred_outcomes == y.values).mean()
    
    logger.info(f"\n{'='*50}")
    logger.info("📈 BACKTEST RESULTS")
    logger.info(f"{'='*50}")
    logger.info(f"\n🎯 Overall Accuracy: {accuracy*100:.1f}%")
    
    # Confidence level breakdown
    logger.info("\n📊 Accuracy by Confidence Level:")
    for thresh in [0.50, 0.55, 0.60, 0.65, 0.70]:
        mask = predictions >= thresh
        if mask.sum() > 0:
            acc = (y.values[mask] == 1).mean()
            count = mask.sum()
            logger.info(f"   {thresh*100:.0f}%+ confidence: {acc*100:.1f}% accuracy ({count} games)")
    
    # Betting simulation
    logger.info("\n💰 Betting Simulation (flat $100 bets at -110 odds):")
    
    for thresh in [0.55, 0.60, 0.65]:
        bet_mask = predictions >= thresh
        bets = bet_mask.sum()
        
        if bets > 0:
            wins = (y.values[bet_mask] == 1).sum()
            losses = bets - wins
            profit = wins * 90.91 - losses * 100
            roi = (profit / (bets * 100)) * 100
            
            logger.info(f"\n   Threshold {thresh*100:.0f}%:")
            logger.info(f"   • Bets: {bets}")
            logger.info(f"   • Record: {wins}W - {losses}L ({wins/bets*100:.1f}%)")
            logger.info(f"   • Profit: ${profit:+.0f}")
            logger.info(f"   • ROI: {roi:+.1f}%")
    
    # Monthly breakdown
    logger.info("\n📅 Monthly Performance:")
    df_final['MONTH'] = pd.to_datetime(df_final['GAME_DATE']).dt.to_period('M')
    df_final['PRED'] = predictions
    
    for month in df_final['MONTH'].unique()[-6:]:  # Last 6 months
        month_mask = df_final['MONTH'] == month
        month_preds = df_final.loc[month_mask, 'PRED'].values
        month_actuals = df_final.loc[month_mask, 'WON'].values
        
        month_acc = ((month_preds >= 0.5) == month_actuals).mean()
        logger.info(f"   {month}: {month_acc*100:.1f}% accuracy ({month_mask.sum()} games)")
    
    logger.info(f"\n{'='*50}")
    logger.info("✅ Backtest complete!")
    logger.info(f"{'='*50}")


if __name__ == "__main__":
    main()
