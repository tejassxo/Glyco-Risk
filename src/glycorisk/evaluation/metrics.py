"""
Comprehensive Clinical Metrics Engine and Bootstrap Confidence Interval Calculator.
Calculates ROC-AUC, PR-AUC, Sensitivity, Specificity, PPV, NPV, F1, and Brier Score.
"""

from typing import Dict, Any, List, Tuple
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import (
    roc_auc_score,
    average_precision_score,
    accuracy_score,
    f1_score,
    recall_score,
    precision_score,
    brier_score_loss,
    confusion_matrix,
    roc_curve,
    precision_recall_curve,
)

from ..config import FIGURES_DIR, TABLES_DIR


def evaluate_model_clinically(y_true: np.ndarray, y_probs: np.ndarray, threshold: float = 0.5) -> Dict[str, float]:
    """
    Computes all essential clinical and statistical metrics from predicted probabilities.
    """
    y_pred = (y_probs >= threshold).astype(int)
    cm = confusion_matrix(y_true, y_pred)
    tn, fp, fn, tp = cm.ravel()

    # Clinical diagnostics formulations
    sensitivity = tp / (tp + fn) if (tp + fn) > 0 else 0.0  # Recall
    specificity = tn / (tn + fp) if (tn + fp) > 0 else 0.0  # True Negative Rate
    ppv = tp / (tp + fp) if (tp + fp) > 0 else 0.0          # Positive Predictive Value / Precision
    npv = tn / (tn + fn) if (tn + fn) > 0 else 0.0          # Negative Predictive Value
    f1 = f1_score(y_true, y_pred, zero_division=0)
    acc = accuracy_score(y_true, y_pred)
    roc_auc = roc_auc_score(y_true, y_probs)
    pr_auc = average_precision_score(y_true, y_probs)
    brier = brier_score_loss(y_true, y_probs)

    return {
        "accuracy": float(acc),
        "roc_auc": float(roc_auc),
        "pr_auc": float(pr_auc),
        "sensitivity": float(sensitivity),
        "specificity": float(specificity),
        "ppv": float(ppv),
        "npv": float(npv),
        "f1": float(f1),
        "brier_score": float(brier),
        "tp": int(tp),
        "fp": int(fp),
        "tn": int(tn),
        "fn": int(fn),
    }


def compute_bootstrap_cis(
    y_true: np.ndarray, y_probs: np.ndarray, n_bootstraps: int = 1000, seed: int = 42
) -> Dict[str, Dict[str, float]]:
    """
    Computes 95% Empirical Bootstrap Confidence Intervals for clinical metrics.
    """
    rng = np.random.RandomState(seed)
    n = len(y_true)
    metrics_history = {
        "roc_auc": [],
        "pr_auc": [],
        "sensitivity": [],
        "specificity": [],
        "ppv": [],
        "f1": [],
        "brier_score": [],
    }

    for _ in range(n_bootstraps):
        boot_idx = rng.randint(0, n, size=n)
        b_true = y_true[boot_idx]
        b_probs = y_probs[boot_idx]

        # Ensure both classes are present in sample
        if len(np.unique(b_true)) < 2:
            continue

        res = evaluate_model_clinically(b_true, b_probs)
        for k in metrics_history:
            metrics_history[k].append(res[k])

    cis = {}
    for k, vals in metrics_history.items():
        low = np.percentile(vals, 2.5)
        high = np.percentile(vals, 97.5)
        mean_val = np.mean(vals)
        cis[k] = {
            "mean": float(mean_val),
            "ci_lower": float(low),
            "ci_upper": float(high),
            "formatted": f"{mean_val:.3f} (95% CI: [{low:.3f}, {high:.3f}])"
        }
    return cis


def evaluate_all_models_on_test(
    models_dict: Dict[str, Any], X_test: np.ndarray, y_test: np.ndarray
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Evaluates all benchmarked and calibrated models on the held-out test set.
    Generates comparison tables, confusion matrices, and ROC/PR curves.
    """
    results_list = []
    test_evaluations = {}

    for name, model in models_dict.items():
        probs = model.predict_proba(X_test)[:, 1]
        metrics = evaluate_model_clinically(y_test, probs)
        metrics["model_key"] = name
        results_list.append(metrics)
        test_evaluations[name] = {"probs": probs, "metrics": metrics}

    df_test = pd.DataFrame(results_list)
    cols_order = [
        "model_key", "roc_auc", "pr_auc", "sensitivity", "specificity",
        "ppv", "npv", "f1", "accuracy", "brier_score", "tp", "fp", "tn", "fn"
    ]
    df_test = df_test[cols_order].sort_values(by="roc_auc", ascending=False)
    df_test.to_csv(TABLES_DIR / "test_results_comparison.csv", index=False)

    # 1. Plot Confusion Matrices (Raw and Normalized for Primary Calibrated Model)
    best_model_key = "calibrated_primary" if "calibrated_primary" in models_dict else "xgboost"
    best_probs = test_evaluations[best_model_key]["probs"]
    best_preds = (best_probs >= 0.5).astype(int)
    cm_raw = confusion_matrix(y_test, best_preds)
    cm_norm = cm_raw.astype("float") / cm_raw.sum(axis=1)[:, np.newaxis]

    fig, axes = plt.subplots(1, 2, figsize=(10, 4.5), dpi=300)
    sns.heatmap(
        cm_raw, annot=True, fmt="d", cmap="Blues", cbar=False, ax=axes[0],
        xticklabels=["Non-Diabetic (0)", "Diabetic (1)"],
        yticklabels=["Non-Diabetic (0)", "Diabetic (1)"],
        annot_kws={"size": 11, "weight": "bold"}
    )
    axes[0].set_title(f"Fig. 7.1a: Raw Confusion Matrix (n={len(y_test)})", fontsize=10, fontweight="bold", pad=10)
    axes[0].set_xlabel("Predicted Clinical Class", fontsize=9, fontweight="bold")
    axes[0].set_ylabel("True Pathological Diagnosis", fontsize=9, fontweight="bold")

    sns.heatmap(
        cm_norm, annot=True, fmt=".2%", cmap="Blues", cbar=False, ax=axes[1],
        xticklabels=["Non-Diabetic (0)", "Diabetic (1)"],
        yticklabels=["Non-Diabetic (0)", "Diabetic (1)"],
        annot_kws={"size": 11, "weight": "bold"}
    )
    axes[1].set_title("Fig. 7.1b: Normalized Confusion Matrix", fontsize=10, fontweight="bold", pad=10)
    axes[1].set_xlabel("Predicted Clinical Class", fontsize=9, fontweight="bold")
    axes[1].set_ylabel("True Pathological Diagnosis", fontsize=9, fontweight="bold")

    fig.suptitle(f"Fig. 7.1: Primary Calibrated Model Diagnostic Confusion Matrix", fontsize=11, fontweight="bold", y=1.02)
    fig.savefig(FIGURES_DIR / "fig_7_1_confusion_matrix.png", dpi=300, bbox_inches="tight")
    plt.close(fig)

    # 2. Plot ROC and PR Curves comparing all models
    fig, axes = plt.subplots(1, 2, figsize=(12, 5), dpi=300)

    # ROC Curves
    axes[0].plot([0, 1], [0, 1], "k--", label="Random Chance (AUC = 0.500)", linewidth=1.2)
    colors = {"logistic_regression": "#7F8C8D", "svm_rbf": "#8E44AD", "random_forest": "#2980B9", "xgboost": "#D9381E", "calibrated_primary": "#1DB954"}
    
    for name, data in test_evaluations.items():
        fpr, tpr, _ = roc_curve(y_test, data["probs"])
        auc_val = data["metrics"]["roc_auc"]
        color = colors.get(name, "#333333")
        label = f"{name} (AUC: {auc_val:.3f})"
        axes[0].plot(fpr, tpr, label=label, linewidth=1.8, color=color)

    axes[0].set_title("Fig. 7.2a: Receiver Operating Characteristic (ROC)", fontsize=10, fontweight="bold", pad=10)
    axes[0].set_xlabel("False Positive Rate (1 - Specificity)", fontsize=9, fontweight="bold")
    axes[0].set_ylabel("True Positive Rate (Sensitivity / Recall)", fontsize=9, fontweight="bold")
    axes[0].legend(frameon=True, fontsize=8, loc="lower right")
    axes[0].grid(True, alpha=0.5)

    # Precision-Recall Curves
    baseline_pr = float(y_test.sum() / len(y_test))
    axes[1].axhline(y=baseline_pr, color="k", linestyle="--", label=f"Prevalence Baseline ({baseline_pr:.2f})", linewidth=1.2)
    for name, data in test_evaluations.items():
        precision, recall, _ = precision_recall_curve(y_test, data["probs"])
        pr_auc = data["metrics"]["pr_auc"]
        color = colors.get(name, "#333333")
        label = f"{name} (PR-AUC: {pr_auc:.3f})"
        axes[1].plot(recall, precision, label=label, linewidth=1.8, color=color)

    axes[1].set_title("Fig. 7.2b: Precision-Recall Curve (PR-AUC)", fontsize=10, fontweight="bold", pad=10)
    axes[1].set_xlabel("Recall (Sensitivity)", fontsize=9, fontweight="bold")
    axes[1].set_ylabel("Precision (Positive Predictive Value)", fontsize=9, fontweight="bold")
    axes[1].legend(frameon=True, fontsize=8, loc="lower left")
    axes[1].grid(True, alpha=0.5)

    fig.suptitle("Fig. 7.2: Comparative ROC and Precision-Recall Curves Across All Architectures", fontsize=11, fontweight="bold", y=1.02)
    fig.savefig(FIGURES_DIR / "fig_7_2_roc_pr_curves.png", dpi=300, bbox_inches="tight")
    plt.close(fig)

    return df_test, test_evaluations
