"""
Leak-Free Clinical Data Preprocessing Pipeline.
Guarantees zero data leakage by isolating test/val partitions prior to fitting imputers and scalers.
"""

from typing import Dict, Tuple, Any
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.impute import KNNImputer, SimpleImputer
from sklearn.preprocessing import StandardScaler
import joblib

from ..config import (
    FEATURES,
    TARGET,
    PHYSIOLOGICAL_ZERO_COLS,
    RANDOM_SEED,
    TRAIN_RATIO,
    VAL_RATIO,
    TEST_RATIO,
    PROCESSED_DATA_DIR,
    MODELS_DIR,
)
from .loader import load_raw_dataset


class ClinicalPreprocessor:
    """
    Production preprocessor with clinical zero-handling, leak-free imputation,
    and standard scaling.
    """

    def __init__(self, imputation_strategy: str = "knn", n_neighbors: int = 5):
        self.imputation_strategy = imputation_strategy
        self.n_neighbors = n_neighbors
        self.feature_names = FEATURES

        if imputation_strategy == "knn":
            self.imputer = KNNImputer(n_neighbors=n_neighbors)
        elif imputation_strategy == "median":
            self.imputer = SimpleImputer(strategy="median")
        else:
            raise ValueError(f"Unsupported imputation strategy: {imputation_strategy}")

        self.scaler = StandardScaler()
        self.is_fitted = False
        self.train_impute_medians_ = {}

    @staticmethod
    def clean_physiological_zeros(df: pd.DataFrame) -> pd.DataFrame:
        """
        Converts biologically implausible zeros to NaN for physiological metrics.
        Leaves Pregnancies untouched as 0 is clinically valid.
        """
        df_cleaned = df.copy()
        for col in PHYSIOLOGICAL_ZERO_COLS:
            if col in df_cleaned.columns:
                df_cleaned[col] = df_cleaned[col].replace(0, np.nan)
        return df_cleaned

    def fit(self, X: pd.DataFrame) -> "ClinicalPreprocessor":
        """Fits the imputer and scaler strictly on training data."""
        X_df = X[self.feature_names].copy()
        X_cleaned = self.clean_physiological_zeros(X_df)

        # Store training medians for reference / fallback
        for col in self.feature_names:
            self.train_impute_medians_[col] = float(X_cleaned[col].median())

        X_imputed = self.imputer.fit_transform(X_cleaned)
        self.scaler.fit(X_imputed)
        self.is_fitted = True
        return self

    def transform(self, X: pd.DataFrame) -> np.ndarray:
        """Transforms unseen data using parameters learned strictly on train."""
        if not self.is_fitted:
            raise RuntimeError("ClinicalPreprocessor must be fitted before transform.")
        X_df = X[self.feature_names].copy()
        X_cleaned = self.clean_physiological_zeros(X_df)
        X_imputed = self.imputer.transform(X_cleaned)
        X_scaled = self.scaler.transform(X_imputed)
        return X_scaled

    def fit_transform(self, X: pd.DataFrame) -> np.ndarray:
        """Fits on train and returns transformed train."""
        return self.fit(X).transform(X)

    def transform_single(self, patient_dict: Dict[str, Any]) -> Tuple[np.ndarray, Dict[str, float]]:
        """
        Transforms a single patient's raw clinical input dictionary for inference.
        Returns scaled array and imputed unscaled feature dictionary.
        """
        df_single = pd.DataFrame([patient_dict])[self.feature_names]
        df_cleaned = self.clean_physiological_zeros(df_single)
        imputed_vals = self.imputer.transform(df_cleaned)[0]
        scaled_vals = self.scaler.transform([imputed_vals])[0]

        imputed_dict = {
            feat: float(imputed_vals[i]) for i, feat in enumerate(self.feature_names)
        }
        return scaled_vals.reshape(1, -1), imputed_dict


def prepare_data_pipeline(
    imputation_strategy: str = "knn", save_artifacts: bool = True
) -> Dict[str, Any]:
    """
    Executes the deterministic, leak-free data pipeline:
    1. Loads raw dataset.
    2. Performs stratified split: 70% Train, 15% Validation, 15% Test.
    3. Fits ClinicalPreprocessor strictly on Train.
    4. Transforms Validation and Test sets.
    5. Saves preprocessed datasets and serializes preprocessor artifact.
    """
    df = load_raw_dataset()

    X = df[FEATURES]
    y = df[TARGET].astype(int)

    # Step 1: Stratified split into Train (70%) and Temp (30%)
    temp_ratio = VAL_RATIO + TEST_RATIO
    X_train_raw, X_temp_raw, y_train, y_temp = train_test_split(
        X, y, test_size=temp_ratio, random_state=RANDOM_SEED, stratify=y
    )

    # Step 2: Split Temp into Validation (15% total) and Test (15% total)
    val_test_ratio = TEST_RATIO / temp_ratio  # 0.15 / 0.30 = 0.50
    X_val_raw, X_test_raw, y_val, y_test = train_test_split(
        X_temp_raw, y_temp, test_size=val_test_ratio, random_state=RANDOM_SEED, stratify=y_temp
    )

    # Step 3: Fit preprocessor strictly on X_train_raw
    preprocessor = ClinicalPreprocessor(imputation_strategy=imputation_strategy)
    X_train_scaled = preprocessor.fit_transform(X_train_raw)
    X_val_scaled = preprocessor.transform(X_val_raw)
    X_test_scaled = preprocessor.transform(X_test_raw)

    pipeline_data = {
        "X_train": X_train_scaled,
        "y_train": y_train.values,
        "X_val": X_val_scaled,
        "y_val": y_val.values,
        "X_test": X_test_scaled,
        "y_test": y_test.values,
        "X_train_raw": X_train_raw,
        "X_val_raw": X_val_raw,
        "X_test_raw": X_test_raw,
        "feature_names": FEATURES,
        "preprocessor": preprocessor,
        "split_counts": {
            "total": len(df),
            "train": len(y_train),
            "val": len(y_val),
            "test": len(y_test),
            "train_pos": int(y_train.sum()),
            "train_neg": int(len(y_train) - y_train.sum()),
            "val_pos": int(y_val.sum()),
            "val_neg": int(len(y_val) - y_val.sum()),
            "test_pos": int(y_test.sum()),
            "test_neg": int(len(y_test) - y_test.sum()),
        },
    }

    if save_artifacts:
        # Save preprocessor artifact
        joblib.dump(preprocessor, MODELS_DIR / "preprocessor.joblib")

        # Save processed splits as CSVs for inspection and reproducibility
        train_df = pd.DataFrame(X_train_scaled, columns=FEATURES)
        train_df[TARGET] = y_train.values
        train_df.to_csv(PROCESSED_DATA_DIR / "train.csv", index=False)

        val_df = pd.DataFrame(X_val_scaled, columns=FEATURES)
        val_df[TARGET] = y_val.values
        val_df.to_csv(PROCESSED_DATA_DIR / "val.csv", index=False)

        test_df = pd.DataFrame(X_test_scaled, columns=FEATURES)
        test_df[TARGET] = y_test.values
        test_df.to_csv(PROCESSED_DATA_DIR / "test.csv", index=False)

    return pipeline_data
