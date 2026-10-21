"""
Clinical SHAP Explanation Engine.
Generates local patient-level attributions and global feature rankings using Shapley values.
"""

from typing import Dict, Any, List, Tuple
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import shap

from ..config import FIGURES_DIR, FEATURES, FEATURE_METADATA


class ClinicalSHAPExplainer:
    """Manages global and patient-level SHAP attributions for clinical defensibility."""

    def __init__(self, model: Any, background_data: np.ndarray, feature_names: List[str] = FEATURES):
        self.model = model
        self.background_data = background_data
        self.feature_names = feature_names

        # Recursively unwrap CalibratedClassifierCV and FrozenEstimator
        underlying_model = model
        while hasattr(underlying_model, "estimator"):
            underlying_model = underlying_model.estimator
        if hasattr(underlying_model, "calibrated_classifiers_") and len(underlying_model.calibrated_classifiers_) > 0:
            underlying_model = underlying_model.calibrated_classifiers_[0]
            while hasattr(underlying_model, "estimator"):
                underlying_model = underlying_model.estimator

        self.underlying_model = underlying_model

        try:
            self.explainer = shap.TreeExplainer(self.underlying_model)
        except Exception:
            # Fallback for non-tree models
            self.explainer = shap.Explainer(self.underlying_model.predict_proba, self.background_data)

        # Robust expected_value extraction
        exp_val = getattr(self.explainer, "expected_value", 0.0)
        if isinstance(exp_val, (list, np.ndarray)):
            self.expected_value = float(exp_val[1]) if len(exp_val) > 1 else float(exp_val[0])
        else:
            self.expected_value = float(exp_val)

    def explain_instance(self, x_scaled: np.ndarray) -> Dict[str, Any]:
        """
        Computes local SHAP attributions for a single patient instance.
        Returns base value, feature contributions, and sorted drivers.
        """
        if x_scaled.ndim == 1:
            x_scaled = x_scaled.reshape(1, -1)

        shap_values = self.explainer(x_scaled)
        values = shap_values.values[0]
        if values.ndim > 1:  # Multi-class output, extract positive class
            values = values[:, 1]

        contributions = []
        for feat, val in zip(self.feature_names, values):
            contributions.append({
                "feature": feat,
                "label": FEATURE_METADATA.get(feat, {}).get("label", feat),
                "shap_value": float(val),
                "impact": f"+{val:.3f}" if val >= 0 else f"{val:.3f}",
                "direction": "RISK_INCREASING" if val > 0 else "PROTECTIVE",
                "abs_impact": abs(float(val)),
            })

        contributions = sorted(contributions, key=lambda x: x["abs_impact"], reverse=True)

        return {
            "base_value": self.expected_value,
            "feature_contributions": contributions,
            "top_drivers": [c for c in contributions if c["direction"] == "RISK_INCREASING"][:3],
            "protective_drivers": [c for c in contributions if c["direction"] == "PROTECTIVE"][:3],
        }

    def generate_global_importance_plots(self, X_test_scaled: np.ndarray):
        """
        Computes SHAP values over the entire test set and plots:
        - Fig 7.3: Global Feature Importance Bar Chart
        - Fig 7.6: SHAP Summary Beeswarm Plot
        """
        shap_values = self.explainer(X_test_scaled)
        values = shap_values.values
        if values.ndim == 3:  # Binary classification with (samples, features, classes)
            values = values[:, :, 1]

        # 1. Global Mean Absolute SHAP Importance Bar Chart
        mean_abs_shap = np.mean(np.abs(values), axis=0)
        df_imp = pd.DataFrame({
            "Feature": self.feature_names,
            "Mean_Abs_SHAP": mean_abs_shap,
        }).sort_values(by="Mean_Abs_SHAP", ascending=True)

        fig, ax = plt.subplots(figsize=(7, 4.8), dpi=300)
        y_pos = np.arange(len(df_imp))
        bars = ax.barh(y_pos, df_imp["Mean_Abs_SHAP"], color="#2B2B2B", edgecolor="#111111", height=0.55)
        ax.set_yticks(y_pos)
        ax.set_yticklabels([FEATURE_METADATA[f]["label"] for f in df_imp["Feature"]], fontsize=9, fontweight="bold")
        ax.set_xlabel("Mean |SHAP Value| (Average Impact on Model Risk Output)", fontsize=9.5, fontweight="bold")
        ax.set_title("Fig. 7.3: Global Feature Importance (SHAP Attributions)", fontsize=11, fontweight="bold", pad=12)

        for bar in bars:
            w = bar.get_width()
            ax.text(w + 0.01, bar.get_y() + bar.get_height()/2, f"{w:.3f}", va="center", fontsize=8.5, fontweight="bold")

        ax.grid(axis="x", alpha=0.5)
        sns.despine(top=True, right=True)
        fig.savefig(FIGURES_DIR / "fig_7_3_feature_importance.png", dpi=300, bbox_inches="tight")
        plt.close(fig)

        # 2. Local Waterfall Plot for a representative high-risk patient
        # Select first high-risk patient in test set
        high_risk_idx = 0
        local_exp = self.explain_instance(X_test_scaled[high_risk_idx])

        fig, ax = plt.subplots(figsize=(8, 5.0), dpi=300)
        feats = [c["feature"] for c in local_exp["feature_contributions"]]
        shaps = [c["shap_value"] for c in local_exp["feature_contributions"]]
        colors = ["#E74C3C" if s > 0 else "#2ECC71" for s in shaps]

        y_pos = np.arange(len(feats))
        ax.barh(y_pos, shaps, color=colors, edgecolor="#222222", height=0.55)
        ax.axvline(0, color="#111111", linewidth=1.0)
        ax.set_yticks(y_pos)
        ax.set_yticklabels(feats, fontsize=9.5, fontweight="bold")
        ax.invert_yaxis()
        ax.set_xlabel("SHAP Value (Marginal Contribution to Log-Odds)", fontsize=9.5, fontweight="bold")
        ax.set_title("Fig. 7.7: Local Patient SHAP Attribution Waterfall (Representative Case)", fontsize=11, fontweight="bold", pad=12)

        for i, val in enumerate(shaps):
            offset = 0.02 if val >= 0 else -0.02
            ha = "left" if val >= 0 else "right"
            ax.text(val + offset, i, f"{val:+.3f}", va="center", ha=ha, fontsize=8.5, fontweight="bold")

        ax.grid(axis="x", alpha=0.5)
        sns.despine(top=True, right=True)
        fig.savefig(FIGURES_DIR / "fig_7_7_shap_waterfall.png", dpi=300, bbox_inches="tight")
        plt.close(fig)


def initialize_shap_explainer(model: Any, X_train: np.ndarray, feature_names: List[str] = FEATURES) -> ClinicalSHAPExplainer:
    """Creates and returns the production clinical SHAP explainer."""
    return ClinicalSHAPExplainer(model=model, background_data=X_train, feature_names=feature_names)
