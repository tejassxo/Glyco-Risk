"""
Publication-Grade Exploratory Data Analysis & Diagram Generator for GlycoRisk AI.
Adheres to clinical visualization standards: precise scales, crisp typography, and high resolution.
"""

import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np
from ..config import (
    FIGURES_DIR,
    FEATURES,
    TARGET,
    PHYSIOLOGICAL_ZERO_COLS,
    FEATURE_METADATA,
)
from .loader import load_raw_dataset

# Style configurations for publication figures
plt.rcParams.update({
    "font.sans-serif": "DejaVu Sans",
    "axes.edgecolor": "#333333",
    "axes.linewidth": 0.8,
    "grid.color": "#E5E5E5",
    "grid.linestyle": "--",
    "grid.linewidth": 0.5,
    "figure.autolayout": True,
})


def generate_all_eda_figures():
    """Generates all publication-grade EDA figures and architectural diagrams."""
    raw_df = load_raw_dataset()

    # 1. Fig 3.1: Class Distribution of the Target Variable
    fig, ax = plt.subplots(figsize=(6, 4.5), dpi=300)
    counts = raw_df[TARGET].value_counts().sort_index()
    percentages = (counts / len(raw_df)) * 100
    bars = ax.bar(
        ["Non-Diabetic (0)", "Diabetic (1)"],
        counts.values,
        color=["#2B2B2B", "#D9381E"],
        width=0.45,
        edgecolor="#111111",
        linewidth=1.2,
    )
    for bar, pct, count in zip(bars, percentages, counts):
        yval = bar.get_height()
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            yval + 8,
            f"n = {count} ({pct:.1f}%)",
            ha="center",
            va="bottom",
            fontsize=10,
            fontweight="bold",
            color="#222222",
        )
    ax.set_ylim(0, 600)
    ax.set_title("Fig. 3.1: Class Distribution of the Target Variable (Outcome)", fontsize=11, fontweight="bold", pad=12)
    ax.set_ylabel("Patient Count (n)", fontsize=10, fontweight="bold")
    ax.grid(axis="y", alpha=0.6)
    sns.despine(top=True, right=True)
    fig.savefig(FIGURES_DIR / "fig_3_1_class_distribution.png", dpi=300, bbox_inches="tight")
    plt.close(fig)

    # 2. Fig 3.2: Correlation Heatmap of Features
    fig, ax = plt.subplots(figsize=(8, 6.5), dpi=300)
    # Use physiologically cleaned dataframe so spurious zero correlations don't distort medical reality
    cleaned_df = raw_df.copy()
    for col in PHYSIOLOGICAL_ZERO_COLS:
        cleaned_df[col] = cleaned_df[col].replace(0, np.nan)
    corr = cleaned_df[FEATURES + [TARGET]].corr()

    mask = np.triu(np.ones_like(corr, dtype=bool))
    cmap = sns.diverging_palette(220, 15, as_cmap=True)
    sns.heatmap(
        corr,
        mask=mask,
        cmap=cmap,
        vmax=0.6,
        vmin=-0.2,
        center=0,
        square=True,
        linewidths=0.7,
        cbar_kws={"shrink": 0.8, "label": "Pearson Correlation (r)"},
        annot=True,
        fmt=".2f",
        annot_kws={"size": 8.5, "weight": "bold"},
        ax=ax,
    )
    ax.set_title("Fig. 3.2: Correlation Heatmap of Physiological Features and Diabetic Outcome", fontsize=11, fontweight="bold", pad=12)
    fig.savefig(FIGURES_DIR / "fig_3_2_correlation_heatmap.png", dpi=300, bbox_inches="tight")
    plt.close(fig)

    # 3. Fig 3.3: Missing & Zero-Value Artifact Prevalence
    fig, ax = plt.subplots(figsize=(7, 4.2), dpi=300)
    zero_counts = {}
    for col in PHYSIOLOGICAL_ZERO_COLS:
        zero_counts[col] = (raw_df[col] == 0).sum()
    zero_series = pd.Series(zero_counts).sort_values(ascending=False)
    zero_pcts = (zero_series / len(raw_df)) * 100

    y_pos = np.arange(len(zero_series))
    ax.barh(y_pos, zero_pcts.values, color="#3A3A3A", edgecolor="#111111", height=0.55)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(zero_series.index, fontsize=10, fontweight="bold")
    ax.invert_yaxis()
    ax.set_xlabel("Physiological Zero Prevalence (%) [Biologically Implausible / Missing Telemetry]", fontsize=10, fontweight="bold")
    ax.set_title("Fig. 3.3: Clinical Missingness Artifacts (Zero-Value Telemetry)", fontsize=11, fontweight="bold", pad=12)

    for i, (pct, count) in enumerate(zip(zero_pcts, zero_series)):
        ax.text(pct + 1.0, i, f"{pct:.1f}% (n={count})", va="center", fontsize=9, fontweight="bold", color="#111111")
    ax.set_xlim(0, 60)
    ax.grid(axis="x", alpha=0.6)
    sns.despine(top=True, right=True)
    fig.savefig(FIGURES_DIR / "fig_3_3_missing_zero_artifacts.png", dpi=300, bbox_inches="tight")
    plt.close(fig)

    # 4. Fig 3.4: Risk Factor Distributions vs. Diabetic Outcome
    fig, axes = plt.subplots(2, 2, figsize=(9, 7), dpi=300)
    key_features = ["Glucose", "BMI", "Age", "Insulin"]
    for idx, feat in enumerate(key_features):
        ax = axes[idx // 2, idx % 2]
        plot_df = cleaned_df[[feat, TARGET]].dropna()
        sns.boxplot(
            data=plot_df,
            x=TARGET,
            y=feat,
            hue=TARGET,
            legend=False,
            ax=ax,
            palette=["#E0E0E0", "#FF4D4D"],
            width=0.45,
            fliersize=3,
        )
        ax.set_xticks([0, 1])
        ax.set_xticklabels(["Non-Diabetic (0)", "Diabetic (1)"], fontweight="bold", fontsize=9)
        ax.set_xlabel("")
        ax.set_ylabel(f"{FEATURE_METADATA[feat]['label']} ({FEATURE_METADATA[feat]['unit']})", fontweight="bold", fontsize=9)
        ax.set_title(f"{feat} Stratification", fontweight="bold", fontsize=10)
        ax.grid(axis="y", alpha=0.5)
        sns.despine(ax=ax, top=True, right=True)

    fig.suptitle("Fig. 3.4: Distribution of Primary Metabolic Risk Factors by Diabetic Outcome", fontsize=11, fontweight="bold", y=1.01)
    fig.savefig(FIGURES_DIR / "fig_3_4_risk_factor_distributions.png", dpi=300, bbox_inches="tight")
    plt.close(fig)

    # 5. Fig 4.1: Preprocessing Pipeline Architecture Diagram
    fig, ax = plt.subplots(figsize=(10, 3.2), dpi=300)
    ax.axis("off")
    boxes = [
        {"text": "Raw Clinical Data\n(768 Patients, 8 Features)", "x": 0.08, "y": 0.5, "w": 0.14, "h": 0.6, "color": "#F0F0F0"},
        {"text": "Physiological Zero\nCorrection (NaN Flagging)\n[Gluc, BP, Skin, Ins, BMI]", "x": 0.26, "y": 0.5, "w": 0.16, "h": 0.6, "color": "#FDF2E9"},
        {"text": "Stratified Isolation\n70% Train (n=537)\n15% Val (n=115)\n15% Test (n=116)", "x": 0.46, "y": 0.5, "w": 0.15, "h": 0.6, "color": "#EAF2F8"},
        {"text": "Leak-Free Imputation\nKNN (k=5) / Median\n[Fit strictly on Train]", "x": 0.66, "y": 0.5, "w": 0.15, "h": 0.6, "color": "#E8F8F5"},
        {"text": "Standard Scaling\nz = (x - mu) / sigma\n[Normalized Inputs]", "x": 0.86, "y": 0.5, "w": 0.14, "h": 0.6, "color": "#FEF9E7"},
    ]
    for b in boxes:
        rect = plt.Rectangle(
            (b["x"] - b["w"]/2, b["y"] - b["h"]/2),
            b["w"],
            b["h"],
            facecolor=b["color"],
            edgecolor="#222222",
            linewidth=1.2,
            transform=ax.transAxes,
        )
        ax.add_patch(rect)
        ax.text(
            b["x"],
            b["y"],
            b["text"],
            ha="center",
            va="center",
            fontsize=8.5,
            fontweight="bold",
            color="#111111",
            transform=ax.transAxes,
        )

    # Draw connecting arrows
    for i in range(len(boxes) - 1):
        x_start = boxes[i]["x"] + boxes[i]["w"]/2
        x_end = boxes[i+1]["x"] - boxes[i+1]["w"]/2
        ax.annotate(
            "",
            xy=(x_end, 0.5),
            xytext=(x_start, 0.5),
            arrowprops=dict(arrowstyle="->", color="#111111", lw=1.5),
        )

    ax.set_title("Fig. 4.1: End-to-End Leak-Free Clinical Preprocessing Pipeline", fontsize=11, fontweight="bold", pad=12)
    fig.savefig(FIGURES_DIR / "fig_4_1_preprocessing_pipeline.png", dpi=300, bbox_inches="tight")
    plt.close(fig)

    # 6. Fig 5.1: Proposed System Workflow Diagram
    fig, ax = plt.subplots(figsize=(10, 4.0), dpi=300)
    ax.axis("off")
    workflow_nodes = [
        {"text": "Clinical EHR Inputs\n(Patient Telemetry)", "x": 0.10, "y": 0.65, "w": 0.15, "h": 0.45, "color": "#EBF5FB"},
        {"text": "Data Preprocessor\n(Zero Clean + Scaling)", "x": 0.32, "y": 0.65, "w": 0.16, "h": 0.45, "color": "#E8F8F5"},
        {"text": "Calibrated ML Core\n(Tuned XGBoost / RF\n+ Platt / Isotonic)", "x": 0.55, "y": 0.65, "w": 0.18, "h": 0.45, "color": "#FCF3CF"},
        {"text": "Explainability Engine\n(TreeSHAP Local Drivers\n+ Waterfall Attribution)", "x": 0.78, "y": 0.65, "w": 0.18, "h": 0.45, "color": "#FDEDEC"},
        {"text": "Deep Obsidian Web UI\n(Real-Time Risk Gauge, Monospace Telemetry, Clinical Forensics JSON)", "x": 0.44, "y": 0.18, "w": 0.70, "h": 0.28, "color": "#EAEDED"},
    ]
    for b in workflow_nodes:
        rect = plt.Rectangle(
            (b["x"] - b["w"]/2, b["y"] - b["h"]/2),
            b["w"],
            b["h"],
            facecolor=b["color"],
            edgecolor="#222222",
            linewidth=1.2,
            transform=ax.transAxes,
        )
        ax.add_patch(rect)
        ax.text(
            b["x"],
            b["y"],
            b["text"],
            ha="center",
            va="center",
            fontsize=8.5,
            fontweight="bold",
            color="#111111",
            transform=ax.transAxes,
        )

    # Arrows between top stages
    for i in range(3):
        x_start = workflow_nodes[i]["x"] + workflow_nodes[i]["w"]/2
        x_end = workflow_nodes[i+1]["x"] - workflow_nodes[i+1]["w"]/2
        ax.annotate(
            "",
            xy=(x_end, 0.65),
            xytext=(x_start, 0.65),
            arrowprops=dict(arrowstyle="->", color="#111111", lw=1.5),
        )

    # Arrow from top stages to web UI
    ax.annotate(
        "",
        xy=(0.65, 0.33),
        xytext=(0.65, 0.42),
        arrowprops=dict(arrowstyle="->", color="#111111", lw=1.5),
    )

    ax.set_title("Fig. 5.1: Overall GlycoRisk AI Architectural and Inference Workflow", fontsize=11, fontweight="bold", pad=12)
    fig.savefig(FIGURES_DIR / "fig_5_1_system_workflow.png", dpi=300, bbox_inches="tight")
    plt.close(fig)
    print("All EDA & architectural figures successfully generated in artifacts/figures/")


if __name__ == "__main__":
    generate_all_eda_figures()
