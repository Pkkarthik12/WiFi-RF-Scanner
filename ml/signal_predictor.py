import numpy as np
import pandas as pd
import math
from typing import List, Dict, Any, Tuple
import logging
import joblib
import os

try:
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.metrics import mean_squared_error, r2_score
    from sklearn.model_selection import train_test_split
except ImportError:
    logging.warning("scikit-learn not installed. ML predictor won't work.")

logger = logging.getLogger(__name__)

class RSSIPredictor:
    """
    Predicts distance from RSSI using Machine Learning to improve upon
    the standard Log-Distance Path Loss formula.
    """
    def __init__(self, model_path: str = "models/rssi_rf_model.pkl"):
        self.model_path = model_path
        self.model = None
        self.is_trained = False
        self._load_model()

    def _load_model(self):
        """Loads a pre-trained model if it exists."""
        if os.path.exists(self.model_path):
            try:
                self.model = joblib.load(self.model_path)
                self.is_trained = True
                logger.info(f"Loaded trained model from {self.model_path}")
            except Exception as e:
                logger.error(f"Failed to load model: {e}")

    def extract_features(self, signal_readings: List[Dict[str, Any]]) -> pd.DataFrame:
        """
        Converts raw signal dictionaries into a feature DataFrame.
        Expected keys: rssi, frequency, channel, is_line_of_sight
        """
        features = []
        for reading in signal_readings:
            # Baseline feature
            feat = {
                'rssi': reading.get('rssi', -90),
                'frequency': reading.get('frequency', 2437),
                'channel': reading.get('channel', 6)
            }
            
            # Engineered features
            feat['rssi_squared'] = feat['rssi'] ** 2
            feat['freq_band'] = 1 if feat['frequency'] > 4000 else 0 # 0=2.4G, 1=5G
            
            features.append(feat)
            
        return pd.DataFrame(features)

    def train_model(self, features: pd.DataFrame, labels: pd.Series):
        """Trains the Random Forest Regressor."""
        logger.info("Training RSSI -> Distance Predictor...")
        X_train, X_test, y_train, y_test = train_test_split(features, labels, test_size=0.2, random_state=42)
        
        self.model = RandomForestRegressor(n_estimators=100, max_depth=10, random_state=42)
        self.model.fit(X_train, y_train)
        
        # Evaluate
        preds = self.model.predict(X_test)
        mse = mean_squared_error(y_test, preds)
        r2 = r2_score(y_test, preds)
        
        logger.info(f"Model trained. MSE: {mse:.4f}, R2: {r2:.4f}")
        self.is_trained = True
        
        # Save model
        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
        joblib.dump(self.model, self.model_path)

    def predict_distance(self, signal_readings: List[Dict[str, Any]]) -> List[float]:
        """Predicts distance in meters given signal features."""
        if not self.is_trained or self.model is None:
            # Fallback to standard path loss formula if model isn't ready
            logger.debug("Model not trained, using fallback calculation.")
            return [self._fallback_path_loss(r.get('rssi', -90)) for r in signal_readings]
            
        features_df = self.extract_features(signal_readings)
        predictions = self.model.predict(features_df)
        return list(predictions)

    def _fallback_path_loss(self, rssi: float, cal_offset: float = -40, exponent: float = 2.5) -> float:
        """Standard Log-Distance Path Loss."""
        if rssi > -10: rssi = -10
        if rssi < -100: rssi = -100
        return math.pow(10, (cal_offset - rssi) / (10.0 * exponent))

    def evaluate_model(self, test_data: pd.DataFrame, test_labels: pd.Series) -> Dict[str, float]:
        if not self.is_trained:
            return {"error": "Model not trained"}
            
        preds = self.model.predict(test_data)
        return {
            "mse": mean_squared_error(test_labels, preds),
            "rmse": math.sqrt(mean_squared_error(test_labels, preds)),
            "r2": r2_score(test_labels, preds)
        }
