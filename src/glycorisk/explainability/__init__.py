"""
Explainable AI (XAI) and Clinical Forensics Engine using SHAP (Shapley Additive exPlanations).
"""

from .shap_explainer import ClinicalSHAPExplainer, initialize_shap_explainer
from .clinical_forensics import generate_clinical_forensics_record

__all__ = [
    "ClinicalSHAPExplainer",
    "initialize_shap_explainer",
    "generate_clinical_forensics_record",
]
