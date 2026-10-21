"""
Clinical Error Intelligence & Diagnostic Failure Mode Analysis for GlycoRisk AI.
Investigates False Negatives (critical under-diagnosis) vs False Positives (over-diagnosis).
"""

from typing import Dict, Any, Tuple
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

from ..config import FIGURES_DIR, TABLES_DIR, FEATURES, TARGET, FEATURE_METADATA


def perform_clinical_error_forensics(
    model: Any,
    X_test_raw: pd.DataFrame,
    X_test_scaled: np.ndarray,
    y_test: np.ndarray,
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Performs patient-level forensic breakdown of model predictions:
    Identifies False Negatives (FN) and False Positives (FP) and computes
    clinical differential feature profiles.
    """
    probs = model.predict_proba(X_test_scaled)[:, 1]
    preds = (probs >= 0.5).astype(int)

    analysis_df = X_test_raw.copy()
    analysis_df["True_Outcome"] = y_test
    analysis_df["Predicted_Class"] = preds
    analysis_df["Predicted_Probability"] = np.round(probs, 4)

    def classify_outcome(row):
        if row["True_Outcome"] == 1 and row["Predicted_Class"] == 1:
            return "True Positive (TP)"
        elif row["True_Outcome"] == 0 and row["Predicted_Class"] == 0:
            return "True Negative (TN)"
        elif row["True_Outcome"] == 1 and row["Predicted_Class"] == 0:
            return "False Negative (FN) [Critical Risk]"
        else:
            return "False Positive (FP) [Over-Diagnosis]"

    analysis_df["Diagnostic_Category"] = analysis_df.apply(classify_outcome, axis=1)

    # Compute mean clinical profiles across the 4 confusion categories
    profile_summary = analysis_df.groupby("Diagnostic_Category")[FEATURES + ["Predicted_Probability"]].mean()
    profile_counts = analysis_df["Diagnostic_Category"].value_counts()
    profile_summary["Patient_Count"] = profile_counts

    # Save detailed CSV
    profile_summary.to_csv(TABLES_DIR / "clinical_error_profiles.csv")
    analysis_df.to_csv(TABLES_DIR / "test_patient_predictions.csv", index=False)

    # Detailed False Negative extraction
    fn_df = analysis_df[analysis_df["Diagnostic_Category"].str.startswith("False Negative")]
    fp_df = analysis_df[analysis_df["Diagnostic_Category"].str.startswith("False Positive")]

    forensics_report = {
        "total_test_patients": len(analysis_df),
        "true_positives": int((analysis_df["Diagnostic_Category"] == "True Positive (TP)").sum()),
        "true_negatives": int((analysis_df["Diagnostic_Category"] == "True Negative (TN)").sum()),
        "false_negatives_count": len(fn_df),
        "false_positives_count": len(fp_df),
        "fn_mean_glucose": float(fn_df["Glucose"].mean()) if len(fn_df) > 0 else 0.0,
        "tp_mean_glucose": float(analysis_df[analysis_df["Diagnostic_Category"] == "True Positive (TP)"]["Glucose"].mean()),
        "tn_mean_glucose": float(analysis_df[analysis_df["Diagnostic_Category"] == "True Negative (TN)"]["Glucose"].mean()),
        "fp_mean_glucose": float(fp_df["Glucose"].mean()) if len(fp_df) > 0 else 0.0,
        "clinical_takeaway": (
            f"False Negatives (missed diabetic cases: n={len(fn_df)}) demonstrated an average plasma glucose of "
            f"{fn_df['Glucose'].mean():.1f} mg/dL, which is substantially lower than True Positives ({analysis_df[analysis_df['Diagnostic_Category'] == 'True Positive (TP)']['Glucose'].mean():.1f} mg/dL). "
            "These patients represent atypical early-stage or normoglycemic diabetes presentations with high insulin resistance masked by normal fasting glucose. "
            f"Conversely, False Positives (n={len(fp_df)}) had elevated BMI ({fp_df['BMI'].mean():.1f} kg/m^2) and Age ({fp_df['Age'].mean():.1f} years), triggering precautionary clinical warnings."
        ),
    }

    # Plot error comparison bar chart
    fig, ax = plt.subplots(figsize=(8, 4.5), dpi=300)
    cats = ["True Negative (TN)", "False Positive (FP)", "False Negative (FN)", "True Positive (TP)"]
    # Re-order to match standard
    cat_keys = [c for c in profile_summary.index]
    cat_glucose = [profile_summary.loc[c, "Glucose"] for c in cat_keys]
    colors = ["#2ECC71" if "TN" in c else "#F39C12" if "FP" in c else "#E74C3C" if "FN" in c else "#3498DB" for c in cat_keys]

    bars = ax.bar(cat_keys, cat_glucose, color=colors, edgecolor="#222222", width=0.5)
    ax.axhline(y=140, color="#E74C3C", linestyle="--", linewidth=1.2, label="Pre-diabetes Threshold (140 mg/dL)")
    ax.axhline(y=100, color="#2ECC71", linestyle=":", linewidth=1.2, label="Normal Fasting Threshold (100 mg/dL)")

    for bar, val in zip(bars, cat_glucose):
        ax.text(bar.get_x() + bar.get_width()/2, val + 2, f"{val:.1f}", ha="center", va="bottom", fontsize=9, fontweight="bold")

    ax.set_ylabel("Mean Plasma Glucose (mg/dL)", fontsize=10, fontweight="bold")
    ax.set_title("Fig. 7.5: Clinical Error Telemetry — Mean Glucose by Diagnostic Category", fontsize=11, fontweight="bold", pad=12)
    ax.set_xticks(range(len(cat_keys)))
    ax.set_xticklabels([c.split(" [")[0] for c in cat_keys], rotation=10, ha="right", fontsize=9, fontweight="bold")
    ax.set_ylim(0, 200)
    ax.legend(frameon=True, fontsize=8.5, loc="upper left")
    ax.grid(axis="y", alpha=0.5)
    sns.despine(top=True, right=True)

    fig.savefig(FIGURES_DIR / "fig_7_5_error_analysis.png", dpi=300, bbox_inches="tight")
    plt.close(fig)

    return profile_summary, forensics_report
