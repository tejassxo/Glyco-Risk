"""
Probability Calibration Engine for GlycoRisk AI.
Calibrates raw predictive outputs via Platt Scaling and Isotonic Regression to enforce clinical certainty.
"""

from typing import Dict, Any, Tuple
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.calibration import CalibratedClassifierCV, calibration_curve
from sklearn.metrics import brier_score_loss
import joblib

from ..config import MODELS_DIR, FIGURES_DIR


def compute_ece(y_true: np.ndarray, y_prob: np.ndarray, n_bins: int = 10) -> float:
    """
    Computes Expected Calibration Error (ECE):
    ECE = sum_{m=1}^M (|B_m| / N) * |acc(B_m) - conf(B_m)|
    """
    bins = np.linspace(0.0, 1.0, n_bins + 1)
    binids = np.digitize(y_prob, bins) - 1
    ece = 0.0
    n = len(y_true)

    for i in range(n_bins):
        idx = binids == i
        if np.sum(idx) > 0:
            bin_acc = np.mean(y_true[idx])
            bin_conf = np.mean(y_prob[idx])
            bin_size = np.sum(idx)
            ece += (bin_size / n) * np.abs(bin_acc - bin_conf)

    return float(ece)


class ClinicalCalibrator:
    """Wraps pre-trained models with validation-fitted probability calibration."""

    def __init__(self, base_model: Any):
        self.base_model = base_model
        self.platt_calibrator = None
        self.isotonic_calibrator = None
        self.best_calibrator = None
        self.best_method = None
        self.metrics_summary = {}

    def fit_calibration(self, X_val: np.ndarray, y_val: np.ndarray) -> "ClinicalCalibrator":
        """Fits Platt scaling and Isotonic regression strictly on held-out validation set."""
        # Uncalibrated baseline on val
        raw_probs = self.base_model.predict_proba(X_val)[:, 1]
        raw_brier = brier_score_loss(y_val, raw_probs)
        raw_ece = compute_ece(y_val, raw_probs)

        # Wrap prefit model for scikit-learn 1.8+ compatibility
        try:
            from sklearn.frozen import FrozenEstimator
            estimator_to_fit = FrozenEstimator(self.base_model)
            cv_val = None
        except ImportError:
            estimator_to_fit = self.base_model
            cv_val = "prefit"

        # 1. Platt Scaling (Sigmoidal calibration)
        self.platt_calibrator = CalibratedClassifierCV(
            estimator=estimator_to_fit, method="sigmoid", cv=cv_val
        )
        self.platt_calibrator.fit(X_val, y_val)
        platt_probs = self.platt_calibrator.predict_proba(X_val)[:, 1]
        platt_brier = brier_score_loss(y_val, platt_probs)
        platt_ece = compute_ece(y_val, platt_probs)

        # 2. Isotonic Regression (Non-parametric monotonic step calibration)
        self.isotonic_calibrator = CalibratedClassifierCV(
            estimator=estimator_to_fit, method="isotonic", cv=cv_val
        )
        self.isotonic_calibrator.fit(X_val, y_val)
        iso_probs = self.isotonic_calibrator.predict_proba(X_val)[:, 1]
        iso_brier = brier_score_loss(y_val, iso_probs)
        iso_ece = compute_ece(y_val, iso_probs)

        # Choose best method based on lowest Brier score
        if platt_brier <= iso_brier:
            self.best_calibrator = self.platt_calibrator
            self.best_method = "Platt Scaling (Sigmoid)"
        else:
            self.best_calibrator = self.isotonic_calibrator
            self.best_method = "Isotonic Regression"

        self.metrics_summary = {
            "raw": {"brier": raw_brier, "ece": raw_ece},
            "platt": {"brier": platt_brier, "ece": platt_ece},
            "isotonic": {"brier": iso_brier, "ece": iso_ece},
            "selected_method": self.best_method,
        }

        # Serialize best calibrated model
        joblib.dump(self.best_calibrator, MODELS_DIR / "calibrated_primary_model.joblib")
        return self

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """Returns calibrated probability array."""
        return self.best_calibrator.predict_proba(X)

    def predict(self, X: np.ndarray, threshold: float = 0.5) -> np.ndarray:
        """Returns binary predictions based on clinical risk threshold."""
        probs = self.predict_proba(X)[:, 1]
        return (probs >= threshold).astype(int)

    def plot_reliability_curves(self, X_test: np.ndarray, y_test: np.ndarray):
        """Generates Fig. 7.4 Reliability Curves comparing Raw, Platt, and Isotonic calibration."""
        raw_probs = self.base_model.predict_proba(X_test)[:, 1]
        platt_probs = self.platt_calibrator.predict_proba(X_test)[:, 1]
        iso_probs = self.isotonic_calibrator.predict_proba(X_test)[:, 1]

        fig, ax = plt.subplots(figsize=(7, 6), dpi=300)

        # Perfectly calibrated diagonal reference
        ax.plot([0, 1], [0, 1], "k:", label="Perfect Calibration (y = x)", linewidth=1.5)

        # Curves
        for probs, label, color, ls in [
            (raw_probs, f"Raw Model (Brier: {brier_score_loss(y_test, raw_probs):.4f})", "#7F8C8D", "--"),
            (platt_probs, f"Platt Calibrated (Brier: {brier_score_loss(y_test, platt_probs):.4f})", "#2980B9", "-"),
            (iso_probs, f"Isotonic Calibrated (Brier: {brier_score_loss(y_test, iso_probs):.4f})", "#27AE60", "-."),
        ]:
            prob_true, prob_pred = calibration_curve(y_test, probs, n_bins=8, strategy="uniform")
            ax.plot(prob_pred, prob_true, marker="o", linewidth=2.0, label=label, color=color, linestyle=ls)

        ax.set_title("Fig. 7.4: Risk Probability Calibration & Reliability Curves (Test Set)", fontsize=11, fontweight="bold", pad=12)
        ax.set_xlabel("Mean Predicted Probability (Risk Confidence)", fontsize=10, fontweight="bold")
        ax.set_ylabel("Empirical Fraction of Positives (True Prevalence)", fontsize=10, fontweight="bold")
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.legend(frameon=True, facecolor="#F8F9FA", edgecolor="#CCCCCC", fontsize=8.5, loc="upper left")
        ax.grid(True, alpha=0.5)
        sns.despine(top=True, right=True)

        fig.savefig(FIGURES_DIR / "fig_7_4_calibration_reliability.png", dpi=300, bbox_inches="tight")
        plt.close(fig)


def calibrate_primary_model(base_model: Any, X_val: np.ndarray, y_val: np.ndarray, X_test: np.ndarray, y_test: np.ndarray) -> ClinicalCalibrator:
    """Instantiates, fits, evaluates, and plots probability calibration."""
    calibrator = ClinicalCalibrator(base_model)
    calibrator.fit_calibration(X_val, y_val)
    calibrator.plot_reliability_curves(X_test, y_test)
    print(f"Calibration fitted. Selected optimal method: {calibrator.best_method}")
    print(f"Validation Brier - Raw: {calibrator.metrics_summary['raw']['brier']:.4f} -> Platt: {calibrator.metrics_summary['platt']['brier']:.4f} -> Isotonic: {calibrator.metrics_summary['isotonic']['brier']:.4f}")
    return calibrator
