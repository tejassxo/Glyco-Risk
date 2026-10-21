"""
Production Clinical Inference API and Dashboard Server for GlycoRisk AI.
Serves the Tejas Deep Obsidian interface and exposes clinical telemetry REST endpoints.
"""

from pathlib import Path
from typing import Dict, Any, Optional
import json
import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from ..config import (
    MODELS_DIR,
    TABLES_DIR,
    DOCS_ARTIFACTS_DIR,
    FEATURES,
    FEATURE_METADATA,
    RISK_TIERS,
    SERVER_HOST,
    SERVER_PORT,
)
from ..explainability.clinical_forensics import generate_clinical_forensics_record

STATIC_PATH = Path(__file__).parent / "static"

app = FastAPI(
    title="GlycoCheck AI Clinical Intelligence Platform",
    description="Risk-Calibrated, Explainable Clinical Decision Support System for Diabetes Mellitus",
    version="1.0.0",
)

ARTIFACTS_PATH = Path(__file__).resolve().parents[3] / "artifacts"
if ARTIFACTS_PATH.exists():
    app.mount("/artifacts", StaticFiles(directory=str(ARTIFACTS_PATH)), name="artifacts")


class PatientTelemetryInput(BaseModel):
    Pregnancies: int = Field(5, ge=0, le=25, description="Number of pregnancies")
    Glucose: float = Field(148.0, ge=0.0, le=400.0, description="2h oral glucose tolerance test plasma glucose (mg/dL)")
    BloodPressure: float = Field(72.0, ge=0.0, le=200.0, description="Diastolic blood pressure (mm Hg)")
    SkinThickness: float = Field(35.0, ge=0.0, le=120.0, description="Triceps skinfold thickness (mm)")
    Insulin: float = Field(0.0, ge=0.0, le=1000.0, description="2-hour serum insulin (mu U/ml). 0 represents unmeasured.")
    BMI: float = Field(33.6, ge=0.0, le=80.0, description="Body Mass Index (kg/m^2)")
    DiabetesPedigreeFunction: float = Field(0.627, ge=0.0, le=3.0, description="Genetic diabetes pedigree risk score")
    Age: int = Field(50, ge=18, le=120, description="Patient age in years")


# Lazy model holder
class ModelHolder:
    preprocessor = None
    calibrated_model = None
    shap_explainer = None
    is_loaded = False

    @classmethod
    def load(cls):
        prep_path = MODELS_DIR / "preprocessor.joblib"
        model_path = MODELS_DIR / "calibrated_primary_model.joblib"
        shap_path = MODELS_DIR / "shap_explainer.joblib"

        if prep_path.exists() and model_path.exists() and shap_path.exists():
            cls.preprocessor = joblib.load(prep_path)
            cls.calibrated_model = joblib.load(model_path)
            cls.shap_explainer = joblib.load(shap_path)
            cls.is_loaded = True
            print("Production ML models, preprocessor, and SHAP explainer loaded successfully.")
        else:
            print("Models not found on disk yet. Run pipeline first.")


@app.on_event("startup")
def startup_event():
    ModelHolder.load()


@app.get("/", response_class=HTMLResponse)
def serve_dashboard():
    """Serves the Deep Obsidian web interface."""
    index_file = STATIC_PATH / "index.html"
    if not index_file.exists():
        raise HTTPException(status_code=404, detail="index.html not found")
    with open(index_file, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


@app.get("/styles.css")
def serve_css():
    """Serves Deep Obsidian stylesheet."""
    return FileResponse(STATIC_PATH / "styles.css", media_type="text/css")


@app.get("/app.js")
def serve_js():
    """Serves client-side telemetry script."""
    return FileResponse(STATIC_PATH / "app.js", media_type="application/javascript")


@app.get("/api/health")
def health_check():
    """System health check and model loading status."""
    return {
        "status": "HEALTHY",
        "model_loaded": ModelHolder.is_loaded,
        "engine": "XGBoost 3.4.1 (Platt Calibrated)",
        "framework": "GlycoRisk AI v1.0.0",
        "aesthetic": "Tejas Deep Obsidian / Apple Monochrome",
    }


@app.get("/api/metadata")
def get_metadata():
    """Returns clinical reference ranges, feature schema, and risk stratification tiers."""
    return {
        "features": FEATURES,
        "feature_metadata": FEATURE_METADATA,
        "risk_tiers": RISK_TIERS,
    }


@app.get("/api/metrics")
def get_benchmark_metrics():
    """Returns verified test-set performance metrics across all 5 benchmarked models."""
    csv_path = TABLES_DIR / "test_results_comparison.csv"
    if csv_path.exists():
        df = pd.read_csv(csv_path)
        return df.to_dict(orient="records")
    return []


@app.post("/api/predict")
def predict_patient_risk(patient: PatientTelemetryInput):
    """
    Executes real-time inference, risk calibration, and local SHAP decomposition.
    Returns the complete Clinical Forensics Record.
    """
    if not ModelHolder.is_loaded:
        ModelHolder.load()
    if not ModelHolder.is_loaded:
        raise HTTPException(
            status_code=503,
            detail="Machine learning models are not yet compiled on disk. Execute pipeline first.",
        )

    patient_dict = patient.dict()
    record = generate_clinical_forensics_record(
        patient_telemetry=patient_dict,
        preprocessor=ModelHolder.preprocessor,
        calibrated_model=ModelHolder.calibrated_model,
        explainer=ModelHolder.shap_explainer,
    )
    return record


def run_server():
    """Launches the production ASGI server with uvicorn."""
    import uvicorn
    uvicorn.run(app, host=SERVER_HOST, port=SERVER_PORT)


if __name__ == "__main__":
    run_server()
