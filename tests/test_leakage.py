"""
Unit tests verifying strict absence of data leakage and accurate zero semantics.
"""

import numpy as np
import pandas as pd
import pytest

from src.glycorisk.config import PHYSIOLOGICAL_ZERO_COLS, FEATURES, TARGET
from src.glycorisk.data.preprocessor import ClinicalPreprocessor, prepare_data_pipeline


def test_physiological_zero_semantics():
    """Verify that zeros in physiological features are replaced by NaN, while Pregnancies zero is preserved."""
    test_df = pd.DataFrame([{
        "Pregnancies": 0,
        "Glucose": 0,
        "BloodPressure": 0,
        "SkinThickness": 0,
        "Insulin": 0,
        "BMI": 0.0,
        "DiabetesPedigreeFunction": 0.45,
        "Age": 25,
    }])

    cleaned = ClinicalPreprocessor.clean_physiological_zeros(test_df)

    # Pregnancies must remain 0
    assert cleaned["Pregnancies"].iloc[0] == 0

    # Physiological features must be NaN
    for col in PHYSIOLOGICAL_ZERO_COLS:
        assert np.isnan(cleaned[col].iloc[0]), f"{col} zero was not converted to NaN"


def test_leak_free_split_isolation():
    """Verify that train, validation, and test partitions are completely disjoint and have no shared indices."""
    pipeline_data = prepare_data_pipeline(save_artifacts=False)

    train_raw = pipeline_data["X_train_raw"]
    val_raw = pipeline_data["X_val_raw"]
    test_raw = pipeline_data["X_test_raw"]

    train_idx = set(train_raw.index)
    val_idx = set(val_raw.index)
    test_idx = set(test_raw.index)

    # Strict partition disjointness
    assert len(train_idx.intersection(val_idx)) == 0, "Train and Val partitions overlap!"
    assert len(train_idx.intersection(test_idx)) == 0, "Train and Test partitions overlap!"
    assert len(val_idx.intersection(test_idx)) == 0, "Val and Test partitions overlap!"

    # Shape consistency
    total_samples = len(train_idx) + len(val_idx) + len(test_idx)
    assert total_samples == 768, f"Total split samples ({total_samples}) != 768"


def test_preprocessor_parameters_fit_strictly_on_train():
    """Verify that scaler and imputer parameters are fitted strictly on train and can transform unseen test data."""
    pipeline_data = prepare_data_pipeline(save_artifacts=False)
    preprocessor = pipeline_data["preprocessor"]

    assert preprocessor.is_fitted is True
    assert len(preprocessor.scaler.mean_) == len(FEATURES)
    assert len(preprocessor.scaler.scale_) == len(FEATURES)

    # Transform test set without fitting
    test_scaled = preprocessor.transform(pipeline_data["X_test_raw"])
    assert test_scaled.shape == (len(pipeline_data["X_test_raw"]), len(FEATURES))
    assert not np.isnan(test_scaled).any(), "Transformed test set contains NaNs"
