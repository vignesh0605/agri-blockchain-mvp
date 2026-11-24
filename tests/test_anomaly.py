"""Tests for anomaly detection"""

import pytest
import numpy as np
from datetime import datetime, timedelta

from anomaly import AnomalyDetector, analyze_event, train_detector


class TestAnomalyDetector:
    """Test Isolation Forest anomaly detector"""

    def setup_method(self):
        self.detector = AnomalyDetector(contamination=0.1)

    def create_sample_event(self, price_cents=1500, quantity_kg=100, grade="A", moisture_pct=12):
        """Create a sample event dict"""
        return {
            "id": 1,
            "crop_id": 1,
            "event_type": "price",
            "actor_role": "wholesaler",
            "actor_id": "WHOLE-001",
            "timestamp": datetime.utcnow().timestamp(),
            "location": "Market",
            "data_json": {
                "price_cents": price_cents,
                "quantity_kg": quantity_kg,
                "grade": grade,
                "moisture_pct": moisture_pct
            },
            "harvest_date": (datetime.utcnow() - timedelta(days=5)).timestamp()
        }

    def create_history(self, num_events=10, base_price=1500):
        """Create historical events"""
        history = []
        for i in range(num_events):
            event = self.create_sample_event(
                price_cents=base_price + random.randint(-100, 100),
                quantity_kg=100 + random.randint(-10, 10)
            )
            event["id"] = i + 1
            event["timestamp"] = (datetime.utcnow() - timedelta(days=num_events-i)).timestamp()
            history.append(event)
        return history

    def test_extract_features(self):
        """Test feature extraction"""
        event = self.create_sample_event()
        history = self.create_history(5)

        features = self.detector.extract_features(event, history)

        assert features.shape == (1, 7)
        assert all(isinstance(f, (int, float)) for f in features[0])

    def test_heuristic_score_normal(self):
        """Test heuristic scoring for normal event"""
        event = self.create_sample_event(price_cents=1500, quantity_kg=100, grade="A", moisture_pct=12)
        history = self.create_history(10, base_price=1500)

        features = self.detector.extract_features(event, history)
        score = self.detector._heuristic_score(features[0])

        # Normal event should have low score
        assert score <= 30

    def test_heuristic_score_anomalous_price(self):
        """Test heuristic scoring for anomalous price"""
        event = self.create_sample_event(price_cents=5000, quantity_kg=100, grade="A", moisture_pct=12)  # 233% increase
        history = self.create_history(10, base_price=1500)

        features = self.detector.extract_features(event, history)
        score = self.detector._heuristic_score(features[0])

        # Anomalous price should have high score
        assert score > 70

    def test_heuristic_score_low_quality(self):
        """Test heuristic scoring for low quality"""
        event = self.create_sample_event(price_cents=1500, quantity_kg=100, grade="D", moisture_pct=20)
        history = self.create_history(10)

        features = self.detector.extract_features(event, history)
        score = self.detector._heuristic_score(features[0])

        # Low quality should increase score
        assert score >= 20

    def test_fit_and_score(self):
        """Test fitting and scoring"""
        history = self.create_history(20)

        # Fit detector
        self.detector.fit(history)
        assert self.detector.is_fitted

        # Score normal event
        event = self.create_sample_event(price_cents=1550)  # Small change
        score, contributions = self.detector.score(event, history)

        assert 0 <= score <= 100
        assert len(contributions) == 7

    def test_analyze_event_function(self):
        """Test module-level analyze_event function"""
        event = self.create_sample_event()
        history = self.create_history(5)

        score, contributions = analyze_event(event, history)

        assert 0 <= score <= 100
        assert isinstance(contributions, dict)
        assert len(contributions) == 7


import random


class TestSARIMA:
    """Test SARIMA detector"""

    def test_compute_residual_insufficient_data(self):
        """Test SARIMA with insufficient data"""
        from sarima_detector import compute_sarima_residual

        # Less than 20 points
        prices = [1500, 1510, 1490, 1520, 1505]
        residual = compute_sarima_residual(prices)
        assert residual == 0.0

    def test_compute_residual_sufficient_data(self):
        """Test SARIMA with sufficient data"""
        from sarima_detector import compute_sarima_residual

        # Generate 30 price points with trend
        prices = [1500 + i * 10 + random.randint(-50, 50) for i in range(30)]
        residual = compute_sarima_residual(prices)

        # Should return a float (may be 0 if statsmodels not available)
        assert isinstance(residual, float)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])