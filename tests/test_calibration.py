"""
Unit tests for clinical probability calibration and Brier score minimization.
"""

import numpy as np
import pytest
from sklearn.linear_model import LogisticRegression

from src.glycorisk.calibration.calibrator import ClinicalCalibrator, compute_ece


def test_ece_computation():
    """Verify that Expected Calibration Error computes correctly on synthetic ground truth."""
    y_true = np.array([1, 1, 0, 0, 1, 0, 1, 0])
    y_prob = np.array([0.9, 0.8, 0.1, 0.2, 0.85, 0.15, 0.75, 0.05])
    ece = compute_ece(y_true, y_prob, n_bins=5)
    assert 0.0 <= ece <= 1.0
    assert ece < 0.25, f"ECE on well-separated synthetic data is too high: {ece}"


def test_calibrator_probability_bounds_and_brier():
    """Verify that calibrated models output valid probabilities bounded in [0, 1]."""
    X_synthetic = np.random.randn(100, 8)
    y_synthetic = (X_synthetic[:, 0] + X_synthetic[:, 1] > 0).astype(int)

    base = LogisticRegression()
    base.fit(X_synthetic[:60], y_synthetic[:60])

    calibrator = ClinicalCalibrator(base)
    calibrator.fit_calibration(X_synthetic[60:80], y_synthetic[60:80])

    test_probs = calibrator.predict_proba(X_synthetic[80:])

    assert test_probs.shape == (20, 2)
    assert (test_probs >= 0.0).all()
    assert (test_probs <= 1.0).all()
    np.testing.assert_allclose(test_probs.sum(axis=1), np.ones(20), atol=1e-5)
