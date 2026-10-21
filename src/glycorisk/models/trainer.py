"""
Comprehensive Clinical Model Trainer, Hyperparameter Optimizer, and Convergence Tracker.
Evaluates:
  1. Baseline A: Logistic Regression (L2)
  2. Baseline B: Support Vector Machine (RBF)
  3. Baseline C: Random Forest Classifier
  4. Primary Architecture: XGBoost Classifier (with early stopping)
  5. Alternative Primary: LightGBM Classifier
"""

import time
from typing import Dict, Any, Tuple
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import joblib

from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import GridSearchCV, learning_curve
from sklearn.metrics import (
    roc_auc_score,
    average_precision_score,
    accuracy_score,
    f1_score,
    recall_score,
    precision_score,
    brier_score_loss,
    log_loss,
)
import xgboost as xgb
import lightgbm as lgb

from ..config import (
    RANDOM_SEED,
    MODELS_DIR,
    FIGURES_DIR,
    TABLES_DIR,
    ARTIFACTS_DIR,
)


class ModelTrainer:
    """Manages multi-architecture clinical training, validation, and serialization."""

    def __init__(self, X_train: np.ndarray, y_train: np.ndarray, X_val: np.ndarray, y_val: np.ndarray, feature_names: list):
        self.X_train = X_train
        self.y_train = y_train
        self.X_val = X_val
        self.y_val = y_val
        self.feature_names = feature_names
        self.trained_models = {}
        self.experiment_results = []
        self.xgb_evals_result = {}

        # Imbalance weighting ratio
        num_neg = (self.y_train == 0).sum()
        num_pos = (self.y_train == 1).sum()
        self.scale_pos_weight = float(num_neg / max(1, num_pos))

    def train_logistic_regression(self) -> Dict[str, Any]:
        """Baseline A: L2-Regularized Logistic Regression."""
        t0 = time.time()
        param_grid = {"C": [0.01, 0.1, 1.0, 5.0, 10.0]}
        base_lr = LogisticRegression(
            solver="lbfgs",
            class_weight="balanced",
            max_iter=1000,
            random_state=RANDOM_SEED,
        )
        grid = GridSearchCV(base_lr, param_grid, cv=5, scoring="roc_auc", n_jobs=1)
        grid.fit(self.X_train, self.y_train)
        best_lr = grid.best_estimator_
        latency = (time.time() - t0) * 1000

        self.trained_models["logistic_regression"] = best_lr
        joblib.dump(best_lr, MODELS_DIR / "logistic_regression.joblib")

        val_probs = best_lr.predict_proba(self.X_val)[:, 1]
        val_preds = best_lr.predict(self.X_val)

        return {
            "model_name": "Logistic Regression (L2)",
            "key": "logistic_regression",
            "best_params": grid.best_params_,
            "training_latency_ms": round(latency, 2),
            "val_auc": float(roc_auc_score(self.y_val, val_probs)),
            "val_pr_auc": float(average_precision_score(self.y_val, val_probs)),
            "val_f1": float(f1_score(self.y_val, val_preds)),
            "val_sensitivity": float(recall_score(self.y_val, val_preds)),
            "val_brier": float(brier_score_loss(self.y_val, val_probs)),
        }

    def train_svm(self) -> Dict[str, Any]:
        """Baseline B: Support Vector Machine (RBF Kernel)."""
        t0 = time.time()
        param_grid = {
            "C": [0.1, 1.0, 10.0],
            "gamma": ["scale", "auto", 0.05, 0.1],
        }
        base_svm = SVC(
            kernel="rbf",
            probability=True,
            class_weight="balanced",
            random_state=RANDOM_SEED,
        )
        grid = GridSearchCV(base_svm, param_grid, cv=5, scoring="roc_auc", n_jobs=1)
        grid.fit(self.X_train, self.y_train)
        best_svm = grid.best_estimator_
        latency = (time.time() - t0) * 1000

        self.trained_models["svm_rbf"] = best_svm
        joblib.dump(best_svm, MODELS_DIR / "svm_rbf.joblib")

        val_probs = best_svm.predict_proba(self.X_val)[:, 1]
        val_preds = best_svm.predict(self.X_val)

        return {
            "model_name": "Support Vector Machine (RBF)",
            "key": "svm_rbf",
            "best_params": grid.best_params_,
            "training_latency_ms": round(latency, 2),
            "val_auc": float(roc_auc_score(self.y_val, val_probs)),
            "val_pr_auc": float(average_precision_score(self.y_val, val_probs)),
            "val_f1": float(f1_score(self.y_val, val_preds)),
            "val_sensitivity": float(recall_score(self.y_val, val_preds)),
            "val_brier": float(brier_score_loss(self.y_val, val_probs)),
        }

    def train_random_forest(self) -> Dict[str, Any]:
        """Baseline C: Random Forest Classifier."""
        t0 = time.time()
        param_grid = {
            "n_estimators": [100, 200],
            "max_depth": [3, 5, 8],
            "min_samples_split": [2, 5],
        }
        base_rf = RandomForestClassifier(
            class_weight="balanced",
            random_state=RANDOM_SEED,
            n_jobs=1,
        )
        grid = GridSearchCV(base_rf, param_grid, cv=5, scoring="roc_auc", n_jobs=1)
        grid.fit(self.X_train, self.y_train)
        best_rf = grid.best_estimator_
        latency = (time.time() - t0) * 1000

        self.trained_models["random_forest"] = best_rf
        joblib.dump(best_rf, MODELS_DIR / "random_forest.joblib")

        val_probs = best_rf.predict_proba(self.X_val)[:, 1]
        val_preds = best_rf.predict(self.X_val)

        return {
            "model_name": "Random Forest Classifier",
            "key": "random_forest",
            "best_params": grid.best_params_,
            "training_latency_ms": round(latency, 2),
            "val_auc": float(roc_auc_score(self.y_val, val_probs)),
            "val_pr_auc": float(average_precision_score(self.y_val, val_probs)),
            "val_f1": float(f1_score(self.y_val, val_preds)),
            "val_sensitivity": float(recall_score(self.y_val, val_preds)),
            "val_brier": float(brier_score_loss(self.y_val, val_probs)),
        }

    def train_xgboost(self) -> Dict[str, Any]:
        """Primary Architecture: XGBoost with early stopping and class weight balancing."""
        t0 = time.time()

        # Step 1: Tune hyperparameters with cross-validation on train
        param_grid = {
            "max_depth": [3, 4],
            "learning_rate": [0.05, 0.1],
            "subsample": [0.8, 1.0],
            "colsample_bytree": [0.8, 1.0],
            "reg_alpha": [0.0, 0.5],
        }
        base_xgb = xgb.XGBClassifier(
            n_estimators=100,
            scale_pos_weight=self.scale_pos_weight,
            eval_metric="auc",
            random_state=RANDOM_SEED,
        )
        grid = GridSearchCV(base_xgb, param_grid, cv=5, scoring="roc_auc", n_jobs=1)
        grid.fit(self.X_train, self.y_train)
        best_params = grid.best_params_

        # Step 2: Fit with full early stopping on validation set to capture convergence history
        best_xgb = xgb.XGBClassifier(
            n_estimators=150,
            early_stopping_rounds=20,
            scale_pos_weight=self.scale_pos_weight,
            eval_metric=["logloss", "auc"],
            random_state=RANDOM_SEED,
            **best_params,
        )

        eval_set = [(self.X_train, self.y_train), (self.X_val, self.y_val)]
        best_xgb.fit(
            self.X_train,
            self.y_train,
            eval_set=eval_set,
            verbose=False,
        )
        latency = (time.time() - t0) * 1000

        self.trained_models["xgboost"] = best_xgb
        joblib.dump(best_xgb, MODELS_DIR / "xgboost.joblib")
        self.xgb_evals_result = best_xgb.evals_result()

        # Export training log per iteration
        train_logloss = self.xgb_evals_result["validation_0"]["logloss"]
        val_logloss = self.xgb_evals_result["validation_1"]["logloss"]
        train_auc = self.xgb_evals_result["validation_0"]["auc"]
        val_auc = self.xgb_evals_result["validation_1"]["auc"]

        log_df = pd.DataFrame({
            "iteration": range(1, len(train_logloss) + 1),
            "train_logloss": train_logloss,
            "val_logloss": val_logloss,
            "train_auc": train_auc,
            "val_auc": val_auc,
        })
        log_df.to_csv(ARTIFACTS_DIR / "training_log.csv", index=False)

        val_probs = best_xgb.predict_proba(self.X_val)[:, 1]
        val_preds = best_xgb.predict(self.X_val)

        return {
            "model_name": "XGBoost Classifier (Primary)",
            "key": "xgboost",
            "best_params": best_params,
            "best_iteration": int(best_xgb.best_iteration) if hasattr(best_xgb, "best_iteration") else len(train_logloss),
            "training_latency_ms": round(latency, 2),
            "val_auc": float(roc_auc_score(self.y_val, val_probs)),
            "val_pr_auc": float(average_precision_score(self.y_val, val_probs)),
            "val_f1": float(f1_score(self.y_val, val_preds)),
            "val_sensitivity": float(recall_score(self.y_val, val_preds)),
            "val_brier": float(brier_score_loss(self.y_val, val_probs)),
        }

    def train_lightgbm(self) -> Dict[str, Any]:
        """Alternative Primary: LightGBM Classifier."""
        t0 = time.time()
        param_grid = {
            "num_leaves": [15, 31],
            "learning_rate": [0.05, 0.1],
            "max_depth": [3, 5],
            "n_estimators": [80],
        }
        base_lgb = lgb.LGBMClassifier(
            is_unbalance=True,
            random_state=RANDOM_SEED,
            verbose=-1,
        )
        grid = GridSearchCV(base_lgb, param_grid, cv=5, scoring="roc_auc", n_jobs=1)
        grid.fit(self.X_train, self.y_train)
        best_lgb = grid.best_estimator_
        latency = (time.time() - t0) * 1000

        self.trained_models["lightgbm"] = best_lgb
        joblib.dump(best_lgb, MODELS_DIR / "lightgbm.joblib")

        val_probs = best_lgb.predict_proba(self.X_val)[:, 1]
        val_preds = best_lgb.predict(self.X_val)

        return {
            "model_name": "LightGBM Classifier",
            "key": "lightgbm",
            "best_params": grid.best_params_,
            "training_latency_ms": round(latency, 2),
            "val_auc": float(roc_auc_score(self.y_val, val_probs)),
            "val_pr_auc": float(average_precision_score(self.y_val, val_probs)),
            "val_f1": float(f1_score(self.y_val, val_preds)),
            "val_sensitivity": float(recall_score(self.y_val, val_preds)),
            "val_brier": float(brier_score_loss(self.y_val, val_probs)),
        }

    def plot_convergence_curves(self):
        """Generates Fig 6.1 (Loss curves) and Fig 6.2 (Metric curves) from real iteration telemetry."""
        if not self.xgb_evals_result:
            return

        train_logloss = self.xgb_evals_result["validation_0"]["logloss"]
        val_logloss = self.xgb_evals_result["validation_1"]["logloss"]
        train_auc = self.xgb_evals_result["validation_0"]["auc"]
        val_auc = self.xgb_evals_result["validation_1"]["auc"]
        iterations = range(1, len(train_logloss) + 1)
        best_iter = getattr(self.trained_models["xgboost"], "best_iteration", len(train_logloss) - 1) + 1

        # Fig 6.1: Loss Curves
        fig, ax = plt.subplots(figsize=(7, 4.5), dpi=300)
        ax.plot(iterations, train_logloss, label="Training Log-Loss", color="#2B2B2B", linewidth=2.0)
        ax.plot(iterations, val_logloss, label="Validation Log-Loss", color="#D9381E", linewidth=2.0, linestyle="--")
        ax.axvline(x=best_iter, color="#1DB954", linestyle=":", linewidth=1.5, label=f"Best Iteration (n={best_iter})")
        ax.set_title("Fig. 6.1: XGBoost Loss Curves (Cross-Entropy Loss vs. Iterations)", fontsize=11, fontweight="bold", pad=12)
        ax.set_xlabel("Boosting Iteration (Trees)", fontsize=10, fontweight="bold")
        ax.set_ylabel("Log-Loss", fontsize=10, fontweight="bold")
        ax.legend(frameon=True, facecolor="#F8F9FA", edgecolor="#CCCCCC", fontsize=9)
        ax.grid(True, alpha=0.5)
        sns.despine(top=True, right=True)
        fig.savefig(FIGURES_DIR / "fig_6_1_loss_curves.png", dpi=300, bbox_inches="tight")
        plt.close(fig)

        # Fig 6.2: Metric Curves (ROC-AUC)
        fig, ax = plt.subplots(figsize=(7, 4.5), dpi=300)
        ax.plot(iterations, train_auc, label="Training ROC-AUC", color="#2B2B2B", linewidth=2.0)
        ax.plot(iterations, val_auc, label="Validation ROC-AUC", color="#D9381E", linewidth=2.0, linestyle="--")
        ax.axvline(x=best_iter, color="#1DB954", linestyle=":", linewidth=1.5, label=f"Best Iteration (n={best_iter})")
        ax.set_title("Fig. 6.2: XGBoost Discriminative Convergence (ROC-AUC vs. Iterations)", fontsize=11, fontweight="bold", pad=12)
        ax.set_xlabel("Boosting Iteration (Trees)", fontsize=10, fontweight="bold")
        ax.set_ylabel("Area Under ROC Curve (AUC)", fontsize=10, fontweight="bold")
        ax.legend(frameon=True, facecolor="#F8F9FA", edgecolor="#CCCCCC", fontsize=9)
        ax.grid(True, alpha=0.5)
        sns.despine(top=True, right=True)
        fig.savefig(FIGURES_DIR / "fig_6_2_metric_curves.png", dpi=300, bbox_inches="tight")
        plt.close(fig)

    def plot_learning_curves(self):
        """Generates Fig 6.3: Learning Curves across training sample increments."""
        xgb_model = self.trained_models.get("xgboost")
        if xgb_model is not None and hasattr(xgb_model, "get_params"):
            params = {k: v for k, v in xgb_model.get_params().items() if k not in ["early_stopping_rounds", "callbacks"]}
            params["eval_metric"] = "logloss"
            curve_estimator = xgb.XGBClassifier(**params)
        else:
            curve_estimator = self.trained_models.get("random_forest")

        train_sizes, train_scores, test_scores = learning_curve(
            curve_estimator,
            self.X_train,
            self.y_train,
            cv=5,
            scoring="roc_auc",
            train_sizes=np.linspace(0.2, 1.0, 6),
            random_state=RANDOM_SEED,
            n_jobs=1,
        )

        train_mean = np.mean(train_scores, axis=1)
        train_std = np.std(train_scores, axis=1)
        test_mean = np.mean(test_scores, axis=1)
        test_std = np.std(test_scores, axis=1)

        fig, ax = plt.subplots(figsize=(7, 4.5), dpi=300)
        ax.plot(train_sizes, train_mean, "o-", color="#2B2B2B", label="Training Score (ROC-AUC)", linewidth=2.0)
        ax.fill_between(train_sizes, train_mean - train_std, train_mean + train_std, alpha=0.15, color="#2B2B2B")
        ax.plot(train_sizes, test_mean, "s--", color="#D9381E", label="Cross-Validation Score", linewidth=2.0)
        ax.fill_between(train_sizes, test_mean - test_std, test_mean + test_std, alpha=0.15, color="#D9381E")

        ax.set_title("Fig. 6.3: Empirical Learning Curve (Sample Size vs. Generalization)", fontsize=11, fontweight="bold", pad=12)
        ax.set_xlabel("Training Set Sample Size (n)", fontsize=10, fontweight="bold")
        ax.set_ylabel("Cross-Validated ROC-AUC", fontsize=10, fontweight="bold")
        ax.legend(frameon=True, facecolor="#F8F9FA", edgecolor="#CCCCCC", fontsize=9)
        ax.grid(True, alpha=0.5)
        sns.despine(top=True, right=True)
        fig.savefig(FIGURES_DIR / "fig_6_3_learning_curves.png", dpi=300, bbox_inches="tight")
        plt.close(fig)


def run_model_benchmarking(pipeline_data: Dict[str, Any]) -> Tuple[pd.DataFrame, ModelTrainer]:
    """Runs end-to-end training and benchmarking of all models."""
    trainer = ModelTrainer(
        X_train=pipeline_data["X_train"],
        y_train=pipeline_data["y_train"],
        X_val=pipeline_data["X_val"],
        y_val=pipeline_data["y_val"],
        feature_names=pipeline_data["feature_names"],
    )

    results = []
    print("Training Baseline A: Logistic Regression...")
    results.append(trainer.train_logistic_regression())

    print("Training Baseline B: Support Vector Machine (RBF)...")
    results.append(trainer.train_svm())

    print("Training Baseline C: Random Forest Classifier...")
    results.append(trainer.train_random_forest())

    print("Training Primary Architecture: XGBoost Classifier...")
    results.append(trainer.train_xgboost())

    print("Training Alternative Primary: LightGBM Classifier...")
    results.append(trainer.train_lightgbm())

    df_results = pd.DataFrame(results)
    df_results.to_csv(ARTIFACTS_DIR / "experiment_results.csv", index=False)

    # Plot convergence figures
    trainer.plot_convergence_curves()
    trainer.plot_learning_curves()

    print("Model benchmarking complete. Artifacts written to artifacts/")
    return df_results, trainer
