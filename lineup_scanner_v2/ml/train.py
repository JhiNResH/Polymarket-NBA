#!/usr/bin/env python3
"""
Training Script for NBA Prediction Model
=========================================
Usage:
    python -m lineup_scanner_v2.ml.train
"""
import logging
import sys
import traceback

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("nba_scanner.ml.train")


def main():
    from .data_collector import NBADataCollector
    from .features import FeatureEngineer
    from .model import NBAPredictor
    import pandas as pd

    logger.info("="*50)
    logger.info("🏀 NBA ML Model Training")
    logger.info("="*50)

    # Step 1: Collect data with error handling
    logger.info("\n📥 Step 1: Collecting NBA data...")
    collector = NBADataCollector()

    games_list = []
    seasons = ["2023-24", "2024-25", "2025-26"]

    for season in seasons:
        try:
            logger.info(f"Fetching {season} season data...")
            games = collector.get_season_games(season)
            if not games.empty:
                games_list.append(games)
                logger.info(f"✓ Collected {len(games)} games from {season}")
            else:
                logger.warning(f"No games found for {season}")
        except Exception as e:
            logger.error(f"Failed to collect {season} data: {e}")
            # Continue with other seasons

    if not games_list:
        logger.error("❌ No data collected from any season!")
        sys.exit(1)

    # Efficient memory usage: concat in one operation
    logger.info(f"Combining {len(games_list)} season datasets...")
    all_games = pd.concat(games_list, ignore_index=True, copy=False)
    del games_list  # Free memory

    logger.info(f"✓ Total games: {len(all_games)}")

    # Get team stats for current season with error handling
    try:
        team_stats = collector.get_team_stats("2025-26")
        logger.info(f"✓ Collected team stats for {len(team_stats)} teams")
    except Exception as e:
        logger.warning(f"Failed to collect team stats: {e}. Continuing without team stats.")
        team_stats = pd.DataFrame()
    
    # Step 2: Feature engineering with error handling
    logger.info("\n🔧 Step 2: Feature engineering...")
    try:
        engineer = FeatureEngineer()

        # Prepare basic features
        df = collector.prepare_training_data(all_games)
        logger.info(f"✓ Prepared {len(df)} training samples")

        # Add rolling stats (configurable window)
        ROLLING_WINDOW = 10
        df = engineer.calculate_rolling_stats(df, window=ROLLING_WINDOW)

        # Add matchup features
        df = engineer.add_matchup_features(df, team_stats)

        # Step 2b: Advanced features (opponent, streak, travel, etc.)
        logger.info("\n🔧 Step 2b: Adding advanced features...")
        from .advanced_features import AdvancedFeatureEngineer
        adv_engineer = AdvancedFeatureEngineer()
        df = adv_engineer.apply_all(df)

        # Get final features
        X, y, df_final = engineer.prepare_features(df)

        logger.info(f"✓ Training data: {len(X)} samples, {X.shape[1]} features")
        logger.info(f"  Feature columns: {list(X.columns)}")

        # Validate feature set
        if len(X) < 100:
            logger.warning(f"⚠️  Only {len(X)} samples available. Results may be unreliable.")
        if X.shape[1] < 5:
            logger.warning(f"⚠️  Only {X.shape[1]} features available. Model may underperform.")

    except Exception as e:
        logger.error(f"❌ Feature engineering failed: {e}")
        traceback.print_exc()
        sys.exit(1)
    
    # Step 3: Train model with error handling
    logger.info("\n🎯 Step 3: Training XGBoost model...")
    try:
        predictor = NBAPredictor()
        # Set tune_hyperparams=True for full tuning (slower but better)
        # Set tune_hyperparams=False for faster training with good defaults
        metrics = predictor.train(X, y, tune_hyperparams=True)

        # Step 4: Save model
        logger.info("\n💾 Step 4: Saving model...")
        predictor.save_model()

        logger.info("\n" + "="*50)
        logger.info("✅ Win/Loss Model Training complete!")
        logger.info(f"   Accuracy: {metrics['accuracy']*100:.1f}%")
        logger.info(f"   AUC: {metrics['auc']:.3f}")
        logger.info(f"   CV Score: {metrics['cv_mean']*100:.1f}% (+/- {metrics['cv_std']*100:.1f}%)")
        logger.info("="*50)

    except Exception as e:
        logger.error(f"❌ Model training failed: {e}")
        traceback.print_exc()
        sys.exit(1)
    
    # Step 5: Train Spread model with error handling
    logger.info("\n🎯 Step 5: Training Spread Prediction model...")
    try:
        from .spread_model import SpreadPredictor

        # Use PLUS_MINUS as target for spread prediction
        if 'PLUS_MINUS' in df_final.columns:
            y_spread = df_final['PLUS_MINUS']
            logger.info(f"   Spread target range: [{y_spread.min():.1f}, {y_spread.max():.1f}]")

            spread_predictor = SpreadPredictor()
            spread_metrics = spread_predictor.train(X, y_spread)

            logger.info("\n💾 Saving spread model...")
            spread_predictor.save_model()

            logger.info("\n" + "="*50)
            logger.info("✅ Spread Model Training complete!")
            logger.info(f"   MAE: {spread_metrics['mae']:.2f} points")
            logger.info(f"   RMSE: {spread_metrics['rmse']:.2f} points")
            logger.info("="*50)
        else:
            logger.warning("⚠️  PLUS_MINUS column not found, skipping spread model")

    except ImportError:
        logger.warning("⚠️  SpreadPredictor not available, skipping spread model")
    except Exception as e:
        logger.error(f"❌ Spread model training failed: {e}")
        logger.warning("Continuing without spread model...")
        traceback.print_exc()


if __name__ == "__main__":
    main()
