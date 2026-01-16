"""
XGBoost Model for NBA Win Probability Prediction
"""
import logging
import pickle
from pathlib import Path
from typing import Optional, Tuple, Dict
import numpy as np
import pandas as pd
from sklearn.model_selection import cross_val_score, train_test_split, RandomizedSearchCV
from sklearn.metrics import accuracy_score, roc_auc_score, classification_report
from sklearn.utils.class_weight import compute_class_weight
import xgboost as xgb

logger = logging.getLogger("nba_scanner.ml.model")


class NBAPredictor:
    """XGBoost-based NBA game outcome predictor"""
    
    def __init__(self, model_path: Optional[str] = None):
        self.model: Optional[xgb.XGBClassifier] = None
        self.feature_names: list = []
        self.model_path = model_path or "lineup_scanner_v2/ml/nba_model.pkl"
        
        # Try to load existing model
        if Path(self.model_path).exists():
            self.load_model()
    
    def train(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        test_size: float = 0.2,
        tune_hyperparams: bool = True
    ) -> Dict:
        """
        Train XGBoost model with cross-validation and hyperparameter tuning.

        Args:
            X: Feature matrix
            y: Target labels
            test_size: Test set size ratio
            tune_hyperparams: Whether to perform hyperparameter tuning

        Returns:
            Dictionary with training metrics
        """
        self.feature_names = list(X.columns)

        # Train/test split
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=42, stratify=y
        )

        # Handle class imbalance with scale_pos_weight
        class_weights = compute_class_weight('balanced', classes=np.unique(y_train), y=y_train)
        scale_pos_weight = class_weights[1] / class_weights[0] if len(class_weights) > 1 else 1.0

        logger.info(f"Class distribution - 0: {(y_train==0).sum()}, 1: {(y_train==1).sum()}")
        logger.info(f"Using scale_pos_weight: {scale_pos_weight:.3f}")

        if tune_hyperparams:
            logger.info("Performing hyperparameter tuning with RandomizedSearchCV...")

            # Parameter grid for tuning
            param_dist = {
                'n_estimators': [100, 200, 300],
                'max_depth': [3, 4, 5, 6],
                'learning_rate': [0.01, 0.05, 0.1, 0.15],
                'subsample': [0.7, 0.8, 0.9],
                'colsample_bytree': [0.7, 0.8, 0.9],
                'min_child_weight': [1, 3, 5],
                'gamma': [0, 0.1, 0.2]
            }

            base_model = xgb.XGBClassifier(
                random_state=42,
                eval_metric='logloss',
                scale_pos_weight=scale_pos_weight
            )

            # Randomized search with 5-fold CV
            random_search = RandomizedSearchCV(
                base_model,
                param_distributions=param_dist,
                n_iter=20,  # Number of random combinations to try
                cv=5,
                scoring='roc_auc',
                n_jobs=-1,
                random_state=42,
                verbose=1
            )

            random_search.fit(X_train, y_train)
            self.model = random_search.best_estimator_

            logger.info(f"Best parameters: {random_search.best_params_}")
            logger.info(f"Best CV score: {random_search.best_score_:.3f}")

        else:
            # Use improved default parameters
            self.model = xgb.XGBClassifier(
                n_estimators=200,
                max_depth=5,
                learning_rate=0.05,
                subsample=0.8,
                colsample_bytree=0.8,
                min_child_weight=3,
                gamma=0.1,
                scale_pos_weight=scale_pos_weight,
                random_state=42,
                eval_metric='logloss'
            )

            # Train
            logger.info("Training XGBoost model with improved defaults...")
            self.model.fit(
                X_train, y_train,
                eval_set=[(X_test, y_test)],
                verbose=False
            )
        
        # Evaluate
        y_pred = self.model.predict(X_test)
        y_prob = self.model.predict_proba(X_test)[:, 1]
        
        accuracy = accuracy_score(y_test, y_pred)
        auc = roc_auc_score(y_test, y_prob)
        
        # Cross-validation
        cv_scores = cross_val_score(self.model, X, y, cv=5, scoring='accuracy')
        
        metrics = {
            'accuracy': accuracy,
            'auc': auc,
            'cv_mean': cv_scores.mean(),
            'cv_std': cv_scores.std(),
            'train_size': len(X_train),
            'test_size': len(X_test)
        }
        
        logger.info(f"Training complete:")
        logger.info(f"  Accuracy: {accuracy:.3f}")
        logger.info(f"  AUC: {auc:.3f}")
        logger.info(f"  CV Mean: {cv_scores.mean():.3f} (+/- {cv_scores.std():.3f})")
        
        # Feature importance
        importance = dict(zip(self.feature_names, self.model.feature_importances_))
        sorted_importance = sorted(importance.items(), key=lambda x: x[1], reverse=True)
        logger.info("Feature Importance:")
        for feat, imp in sorted_importance:
            logger.info(f"  {feat}: {imp:.3f}")
        
        return metrics
    
    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """
        Predict win probability.
        
        Returns:
            Array of (P(Loss), P(Win)) for each sample
        """
        if self.model is None:
            raise ValueError("Model not trained or loaded")
        
        # Ensure correct feature order
        X = X[self.feature_names]
        return self.model.predict_proba(X)
    
    def predict_win_prob(self, features: Dict) -> float:
        """
        Predict win probability for a single game.
        
        Args:
            features: Dict with feature values
            
        Returns:
            Win probability (0-1)
        """
        X = pd.DataFrame([features])[self.feature_names]
        proba = self.predict_proba(X)
        return proba[0][1]  # P(Win)
    
    def save_model(self, path: Optional[str] = None):
        """Save model to disk"""
        path = path or self.model_path
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, 'wb') as f:
            pickle.dump({
                'model': self.model,
                'feature_names': self.feature_names
            }, f)
        logger.info(f"Model saved to {path}")
    
    def load_model(self, path: Optional[str] = None):
        """Load model from disk"""
        path = path or self.model_path
        
        with open(path, 'rb') as f:
            data = pickle.load(f)
            self.model = data['model']
            self.feature_names = data['feature_names']
        logger.info(f"Model loaded from {path}")
