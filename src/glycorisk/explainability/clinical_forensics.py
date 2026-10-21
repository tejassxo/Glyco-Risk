"""
Clinical Forensics Record Generator for GlycoRisk AI.
Builds the standardized, auditable clinical inference record.
"""

import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional
import numpy as np

from ..config import RISK_TIERS, FEATURE_METADATA


def generate_clinical_forensics_record(
    patient_telemetry: Dict[str, Any],
    preprocessor: Any,
    calibrated_model: Any,
    explainer: Any,
    patient_id: Optional[str] = None,
    model_version: str = "glycorisk-xgboost-calibrated-v1",
    calibration_method: str = "Platt Scaling (Sigmoid)",
) -> Dict[str, Any]:
    """
    Executes real-time inference, calibration, SHAP attribution, and constructs
    the Clinical Forensics Record JSON artifact.
    """
    t_start = time.perf_counter()

    if not patient_id:
        patient_id = f"PT-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{np.random.randint(1000, 9999)}"

    # Step 1: Preprocessing & Imputation
    scaled_array, imputed_dict = preprocessor.transform_single(patient_telemetry)

    # Step 2: Calibrated Probability Inference
    risk_prob = float(calibrated_model.predict_proba(scaled_array)[0, 1])
    is_diabetic = risk_prob >= 0.50
    prediction_str = "Positive (High Diabetic Risk)" if is_diabetic else "Negative (Normal / Low Risk)"

    # Determine Clinical Risk Tier
    risk_tier_key = "LOW_RISK"
    for tier, cfg in RISK_TIERS.items():
        if risk_prob <= cfg["max_prob"]:
            risk_tier_key = tier
            break

    tier_info = RISK_TIERS[risk_tier_key]

    # Confidence status based on distance from decision boundary (0.50)
    boundary_distance = abs(risk_prob - 0.50)
    if boundary_distance >= 0.30:
        confidence_status = "HIGH_CONFIDENCE"
    elif boundary_distance >= 0.15:
        confidence_status = "MODERATE_CONFIDENCE"
    else:
        confidence_status = "BORDERLINE_UNCERTAINTY"

    # Step 3: SHAP Explanations
    shap_res = explainer.explain_instance(scaled_array)
    top_drivers = shap_res["top_drivers"]
    protective_drivers = shap_res["protective_drivers"]

    top_factors = [
        {
            "feature": d["feature"],
            "clinical_label": d["label"],
            "patient_value": imputed_dict.get(d["feature"]),
            "unit": FEATURE_METADATA.get(d["feature"], {}).get("unit", ""),
            "normal_range": FEATURE_METADATA.get(d["feature"], {}).get("normal_range", ""),
            "impact": d["impact"],
            "direction": d["direction"],
        }
        for d in top_drivers
    ]

    protective_factors = [
        {
            "feature": d["feature"],
            "clinical_label": d["label"],
            "patient_value": imputed_dict.get(d["feature"]),
            "unit": FEATURE_METADATA.get(d["feature"], {}).get("unit", ""),
            "normal_range": FEATURE_METADATA.get(d["feature"], {}).get("normal_range", ""),
            "impact": d["impact"],
            "direction": d["direction"],
        }
        for d in protective_drivers
    ]

    t_end = time.perf_counter()
    latency_ms = round((t_end - t_start) * 1000, 2)

    forensics_record = {
        "patient_id": patient_id,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "prediction": prediction_str,
        "is_diabetic_flag": bool(is_diabetic),
        "risk_probability": round(risk_prob, 4),
        "risk_percentage": round(risk_prob * 100, 1),
        "risk_tier": risk_tier_key,
        "tier_label": tier_info["label"],
        "tier_color": tier_info["color"],
        "confidence_status": confidence_status,
        "recommended_clinical_action": tier_info["action"],
        "top_contributing_factors": top_factors,
        "protective_factors": protective_factors,
        "all_feature_attributions": shap_res["feature_contributions"],
        "imputed_patient_telemetry": imputed_dict,
        "model_version": model_version,
        "calibration_method": calibration_method,
        "inference_latency_ms": latency_ms,
    }

    return forensics_record
