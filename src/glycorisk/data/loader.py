"""
Clinical Dataset Loader and Provenance Tracking for GlycoRisk AI.
"""

import urllib.request
import pandas as pd
from ..config import RAW_DATA_PATH, FEATURES, TARGET


def get_dataset_provenance():
    """Returns official provenance metadata for the Pima Indians Diabetes Dataset."""
    return {
        "dataset_name": "Pima Indians Diabetes Database",
        "source_repository": "National Institute of Diabetes and Digestive and Kidney Diseases (NIDDK) / UCI Machine Learning Repository / Kaggle",
        "url_doi": "https://www.kaggle.com/datasets/uciml/pima-indians-diabetes-database / https://doi.org/10.24432/C57K72",
        "original_creators": "Vincent Sigillito, National Institute of Diabetes and Digestive and Kidney Diseases",
        "year": "1990",
        "license": "Open Data Commons Public Domain Dedication and License (PDDL) / CC0 Public Domain",
        "access_date": "2026-10-21",
        "sample_count": 768,
        "feature_count": 8,
        "target_variable": TARGET,
        "population": "Females of Pima Indian heritage, aged >= 21 years living near Phoenix, Arizona, USA",
        "citation": "Smith, J.W., Everhart, J.E., Dickson, W.C., Knowler, W.C., & Johannes, R.S. (1988). Using the ADAP learning algorithm to forecast the onset of diabetes mellitus. In Proceedings of the Symposium on Computer Applications and Medical Care (pp. 261-265). IEEE Computer Society Press."
    }


def load_raw_dataset(force_download: bool = False) -> pd.DataFrame:
    """Loads the raw tabular clinical dataset, downloading if absent."""
    if not RAW_DATA_PATH.exists() or force_download:
        RAW_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
        url = "https://raw.githubusercontent.com/plotly/datasets/master/diabetes.csv"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req) as response:
            content = response.read()
        with open(RAW_DATA_PATH, "wb") as f:
            f.write(content)

    df = pd.read_csv(RAW_DATA_PATH)
    
    # Validation
    expected_cols = set(FEATURES + [TARGET])
    if not expected_cols.issubset(set(df.columns)):
        missing = expected_cols - set(df.columns)
        raise ValueError(f"Raw dataset is missing expected columns: {missing}")
    
    return df
