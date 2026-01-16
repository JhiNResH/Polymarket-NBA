"""
Spread Prediction Model - XGBoost Regressor for Point Margin
"""
import logging
import pickle
from pathlib import Path
from typing import Optional, Dict
import numpy as np
import pandas as pd
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import xgboost as xgb

logger = logging.getLogger("nba_scanner.ml.spread")


class SpreadPredictor:
    """XGBoost regressor for predicting point margin (spread)"""
    
    def __init__(self, model_path: Optional[str] = None):
        self.model: Optional[xgb.XGBRegressor] = None
        self.feature_names: list = []
        self.model_path = model_path or "lineup_scanner_v2/ml/spread_model.pkl"
        
        # Try to load existing model
        if Path(self.model_path).exists():
            self.load_model()
    
    def train(
        self, 
        X: pd.DataFrame, 
        y: pd.Series,
        test_size: float = 0.2
    ) -> Dict:
        """
        Train XGBoost regressor for point margin prediction.
        
        Args:
            X: Feature DataFrame
            y: Target Series (PLUS_MINUS / point margin)
            
        Returns:
            Dictionary with training metrics
        """
        self.feature_names = list(X.columns)
        
        # Train/test split
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=42
        )
        
        # Initialize XGBoost Regressor
        self.model = xgb.XGBRegressor(
            n_estimators=100,
            max_depth=5,
            learning_rate=0.1,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42
        )
        
        # Train
        logger.info("Training Spread Prediction model...")
        self.model.fit(
            X_train, y_train,
            eval_set=[(X_test, y_test)],
            verbose=False
        )
        
        # Evaluate
        y_pred = self.model.predict(X_test)
        
        mae = mean_absolute_error(y_test, y_pred)
        rmse = np.sqrt(mean_squared_error(y_test, y_pred))
        r2 = r2_score(y_test, y_pred)
        
        # Cross-validation
        cv_scores = cross_val_score(
            self.model, X, y, cv=5, scoring='neg_mean_absolute_error'
        )
        cv_mae = -cv_scores.mean()
        
        metrics = {
            'mae': mae,
            'rmse': rmse,
            'r2': r2,
            'cv_mae': cv_mae,
            'train_size': len(X_train),
            'test_size': len(X_test)
        }
        
        logger.info(f"Training complete:")
        logger.info(f"  MAE: {mae:.2f} points")
        logger.info(f"  RMSE: {rmse:.2f} points")
        logger.info(f"  R²: {r2:.3f}")
        logger.info(f"  CV MAE: {cv_mae:.2f} points")
        
        # Feature importance
        importance = dict(zip(self.feature_names, self.model.feature_importances_))
        sorted_importance = sorted(importance.items(), key=lambda x: x[1], reverse=True)[:10]
        logger.info("Top 10 Feature Importance:")
        for feat, imp in sorted_importance:
            logger.info(f"  {feat}: {imp:.3f}")
        
        return metrics
    
    def predict_spread(self, X: pd.DataFrame) -> np.ndarray:
        """
        Predict point margin.
        
        Returns:
            Array of predicted point margins (positive = home win)
        """
        if self.model is None:
            raise ValueError("Model not trained or loaded")
        
        X = X[self.feature_names]
        return self.model.predict(X)
    
    def predict_single(self, features: Dict) -> float:
        """
        Predict spread for a single game.
        
        Returns:
            Predicted point margin (positive = home win, negative = away win)
        """
        X = pd.DataFrame([features])[self.feature_names]
        return self.predict_spread(X)[0]
    
    def save_model(self, path: Optional[str] = None):
        """Save model to disk"""
        path = path or self.model_path
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, 'wb') as f:
            pickle.dump({
                'model': self.model,
                'feature_names': self.feature_names
            }, f)
        logger.info(f"Spread model saved to {path}")
    
    def load_model(self, path: Optional[str] = None):
        """Load model from disk"""
        path = path or self.model_path
        
        with open(path, 'rb') as f:
            data = pickle.load(f)
            self.model = data['model']
            self.feature_names = data['feature_names']
        logger.info(f"Spread model loaded from {path}")
