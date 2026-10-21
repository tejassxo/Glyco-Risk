"""
Centralized Configuration for GlycoRisk AI Platform.
Enforces deterministic reproducibility, clinical boundaries, and artifact paths.
"""

from pathlib import Path

# Deterministic random seed
RANDOM_SEED = 42

# Base Paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DATA_PATH = DATA_DIR / "raw" / "diabetes.csv"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
ARTIFACTS_DIR = BASE_DIR / "artifacts"
MODELS_DIR = ARTIFACTS_DIR / "models"
FIGURES_DIR = ARTIFACTS_DIR / "figures"
TABLES_DIR = ARTIFACTS_DIR / "tables"
DOCS_ARTIFACTS_DIR = ARTIFACTS_DIR / "documentation"
PRESENTATION_DIR = ARTIFACTS_DIR / "presentation"

# Ensure directories exist
for path in [PROCESSED_DATA_DIR, MODELS_DIR, FIGURES_DIR, TABLES_DIR, DOCS_ARTIFACTS_DIR, PRESENTATION_DIR]:
    path.mkdir(parents=True, exist_ok=True)

# Data Schema & Clinical Metadata
FEATURES = [
    "Pregnancies",
    "Glucose",
    "BloodPressure",
    "SkinThickness",
    "Insulin",
    "BMI",
    "DiabetesPedigreeFunction",
    "Age",
]

TARGET = "Outcome"

# Physiological features where a value of 0 is biologically implausible (represents missing clinical telemetry)
# Note: Pregnancies = 0 is clinically valid (nulliparous women)
PHYSIOLOGICAL_ZERO_COLS = [
    "Glucose",
    "BloodPressure",
    "SkinThickness",
    "Insulin",
    "BMI",
]

# Clinical Reference Intervals & Feature Descriptions
FEATURE_METADATA = {
    "Pregnancies": {
        "label": "Pregnancies",
        "description": "Number of times pregnant",
        "unit": "count",
        "min": 0,
        "max": 17,
        "normal_range": "0 - 4",
        "type": "discrete"
    },
    "Glucose": {
        "label": "Plasma Glucose Concentration",
        "description": "2-hour oral glucose tolerance test plasma glucose (mg/dL)",
        "unit": "mg/dL",
        "min": 44.0,
        "max": 199.0,
        "normal_range": "70 - 140 mg/dL (Normal: <100 fasting, <140 2h-OGTT; Impaired: 140-199; Diabetes: >=200)",
        "type": "continuous"
    },
    "BloodPressure": {
        "label": "Diastolic Blood Pressure",
        "description": "Diastolic blood pressure (mm Hg)",
        "unit": "mm Hg",
        "min": 24.0,
        "max": 122.0,
        "normal_range": "60 - 80 mm Hg (Normal: <80; Elevated/Stage 1: 80-89)",
        "type": "continuous"
    },
    "SkinThickness": {
        "label": "Triceps Skinfold Thickness",
        "description": "Triceps skin fold thickness (mm) as somatic body fat proxy",
        "unit": "mm",
        "min": 7.0,
        "max": 99.0,
        "normal_range": "10 - 30 mm",
        "type": "continuous"
    },
    "Insulin": {
        "label": "2-Hour Serum Insulin",
        "description": "2-Hour serum insulin (mu U/ml)",
        "unit": "mu U/ml",
        "min": 14.0,
        "max": 846.0,
        "normal_range": "16 - 166 mu U/ml",
        "type": "continuous"
    },
    "BMI": {
        "label": "Body Mass Index",
        "description": "Body mass index (weight in kg / (height in m)^2)",
        "unit": "kg/m^2",
        "min": 18.2,
        "max": 67.1,
        "normal_range": "18.5 - 24.9 kg/m^2 (Overweight: 25-29.9, Obese: >=30)",
        "type": "continuous"
    },
    "DiabetesPedigreeFunction": {
        "label": "Diabetes Pedigree Function",
        "description": "Genetic risk score synthesizing family history of diabetes mellitus",
        "unit": "score",
        "min": 0.078,
        "max": 2.42,
        "normal_range": "0.1 - 0.5 (Higher scores represent dense diabetic pedigree)",
        "type": "continuous"
    },
    "Age": {
        "label": "Age",
        "description": "Patient age in years",
        "unit": "years",
        "min": 21,
        "max": 81,
        "normal_range": "21 - 81 years",
        "type": "discrete"
    }
}

# Data Splitting Strategy: 70% Train, 15% Validation, 15% Test (Stratified)
TRAIN_RATIO = 0.70
VAL_RATIO = 0.15
TEST_RATIO = 0.15

# Imputation strategies
DEFAULT_IMPUTATION = "knn"  # 'median' or 'knn'
KNN_NEIGHBORS = 5

# Risk Stratification Tiers
RISK_TIERS = {
    "LOW_RISK": {
        "max_prob": 0.25,
        "label": "Low Risk",
        "color": "#1DB954",  # Emerald
        "action": "Routine annual metabolic surveillance recommended."
    },
    "MODERATE_RISK": {
        "max_prob": 0.50,
        "label": "Moderate / Borderline Risk",
        "color": "#FFB000",  # Amber
        "action": "Lifestyle intervention, HbA1c confirmatory laboratory screen, dietary audit."
    },
    "HIGH_RISK": {
        "max_prob": 0.75,
        "label": "High Clinical Risk",
        "color": "#FF6B4A",  # Coral / Red-orange
        "action": "Urgent endocrinologist consultation, comprehensive OGTT and glycemic panel."
    },
    "CRITICAL_RISK": {
        "max_prob": 1.00,
        "label": "Critical Risk",
        "color": "#FF3333",  # High-alert Red
        "action": "Immediate clinical diagnostic workup and acute glycemic management."
    }
}

# Web Server Configuration
SERVER_HOST = "127.0.0.1"
SERVER_PORT = 8000
