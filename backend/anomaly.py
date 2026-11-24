"""AI Anomaly Detection using Isolation Forest"""

import numpy as np
import json
from typing import List, Dict, Any, Tuple
from datetime import datetime
from sklearn.ensemble import IsolationForest

from config import settings


class AnomalyDetector:
    """Isolation Forest based anomaly detector for supply chain events"""

    def __init__(self, contamination: float = None):
        self.contamination = contamination or settings.ISOLATION_FOREST_CONTAMINATION
        self.model = IsolationForest(
            contamination=self.contamination,
            random_state=settings.ISOLATION_FOREST_RANDOM_STATE,
            n_estimators=settings.ISOLATION_FOREST_N_ESTIMATORS
        )
        self.is_fitted = False
        self.feature_names = [
            "price_change_pct",
            "volume_zscore",
            "quality_index",
            "lead_time_days",
            "seasonal_factor",
            "volatility_7d",
            "sarima_residual"
        ]

    def extract_features(self, event: Dict[str, Any], history: List[Dict[str, Any]]) -> np.ndarray:
        """Extract 7-dimensional feature vector from event + history"""
        data = event.get("data_json", {})
        crop_id = event.get("crop_id")

        # Filter relevant history for this crop
        crop_history = [h for h in history if h.get("crop_id") == crop_id]

        features = []

        # 1. price_change_pct
        if data.get("price_cents") and crop_history:
            prev_price = crop_history[-1].get("data_json", {}).get("price_cents", 1)
            features.append((data["price_cents"] - prev_price) / prev_price * 100)
        else:
            features.append(0.0)

        # 2. volume_zscore
        volumes = [
            h.get("data_json", {}).get("quantity_kg", 0)
            for h in crop_history
            if h.get("data_json", {}).get("quantity_kg")
        ]
        if volumes:
            mean_v, std_v = np.mean(volumes), np.std(volumes) + 1e-6
            features.append((data.get("quantity_kg", 0) - mean_v) / std_v)
        else:
            features.append(0.0)

        # 3. quality_index (0-100)
        grade_score = {"A": 100, "B": 75, "C": 50, "D": 25}.get(data.get("grade", "C"), 50)
        moisture = data.get("moisture_pct", 12)
        quality = grade_score * (1 - abs(moisture - 12) / 20)  # penalize deviation from 12%
        features.append(max(0, min(100, quality)))

        # 4. lead_time_days
        harvest = event.get("harvest_date") or (crop_history[0].get("timestamp") if crop_history else event.get("timestamp"))
        if isinstance(harvest, str):
            harvest = datetime.fromisoformat(harvest.replace('Z', '+00:00')).timestamp()
        event_ts = event.get("timestamp")
        if isinstance(event_ts, str):
            event_ts = datetime.fromisoformat(event_ts.replace('Z', '+00:00')).timestamp()
        features.append((event_ts - harvest) / 86400)

        # 5. seasonal_factor
        dt = datetime.fromtimestamp(event_ts) if isinstance(event_ts, (int, float)) else datetime.utcnow()
        features.append(dt.month / 12.0)

        # 6. volatility_7d (simplified)
        prices = [
            h.get("data_json", {}).get("price_cents", 0)
            for h in crop_history[-7:]
            if h.get("data_json", {}).get("price_cents")
        ]
        features.append(np.std(prices) if len(prices) > 1 else 0.0)

        # 7. deviation_from_expected (placeholder for SARIMA)
        features.append(0.0)

        return np.array(features).reshape(1, -1)

    def fit(self, historical_events: List[Dict[str, Any]]):
        """Fit on historical feature vectors (optional — works without)"""
        if len(historical_events) >= 10:
            X = np.vstack([
                self.extract_features(e, historical_events)
                for e in historical_events
            ])
            self.model.fit(X)
            self.is_fitted = True

    def score(self, event: Dict[str, Any], history: List[Dict[str, Any]]) -> Tuple[int, Dict[str, float]]:
        """Returns (anomaly_score_0_100, feature_contributions)"""
        X = self.extract_features(event, history)

        if self.is_fitted:
            raw_score = self.model.decision_function(X)[0]  # negative = anomaly
            # Convert to 0-100 scale: more negative = higher anomaly
            anomaly_score = max(0, min(100, int(-raw_score * 20 + 50)))
        else:
            # Fallback: simple threshold-based
            anomaly_score = self._heuristic_score(X[0])

        # Feature contributions for explainability
        contributions = dict(zip(self.feature_names, X[0].tolist()))

        return anomaly_score, contributions

    def _heuristic_score(self, features: np.ndarray) -> int:
        """Simple rule-based fallback when no training data"""
        score = 0
        if abs(features[0]) > 50:
            score += 30  # price change >50%
        if abs(features[1]) > 3:
            score += 25   # volume 3 sigma out
        if features[2] < 30:
            score += 20   # low quality
        if features[3] > 30:
            score += 15   # long lead time
        if features[5] > 10000:
            score += 10   # high volatility
        return min(100, score)


# Global detector instance
_detector = None


def get_detector() -> AnomalyDetector:
    global _detector
    if _detector is None:
        _detector = AnomalyDetector()
    return _detector


def analyze_event(event: Dict[str, Any], history: List[Dict[str, Any]]) -> Tuple[int, Dict[str, float]]:
    """Analyze an event for anomalies"""
    detector = get_detector()
    return detector.score(event, history)


def train_detector(historical_events: List[Dict[str, Any]]):
    """Train the detector on historical data"""
    detector = get_detector()
    detector.fit(historical_events)