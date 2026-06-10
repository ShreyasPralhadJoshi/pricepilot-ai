"""Train and load the two supervised models that power PricePilot.

1. Demand regressor  -> predicts units_sold for a (product, price, context).
2. Conversion classifier -> predicts probability that an offer converts well.

Both share the same preprocessing pipeline (one-hot category + scaled numerics)
so they stay consistent.
"""
from pathlib import Path

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingRegressor, RandomForestClassifier
from sklearn.metrics import mean_absolute_error, r2_score, roc_auc_score, accuracy_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from .features import (
    BINARY_FEATURES,
    CATEGORICAL_FEATURES,
    NUMERIC_FEATURES,
    build_features,
)

REGRESSOR_FILE = "demand_regressor.joblib"
CLASSIFIER_FILE = "conversion_classifier.joblib"


def _preprocessor() -> ColumnTransformer:
    return ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), NUMERIC_FEATURES + BINARY_FEATURES),
            ("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL_FEATURES),
        ]
    )


def train_models(df: pd.DataFrame, models_dir: Path) -> dict:
    """Train both models on a sales dataframe and persist them. Returns metrics."""
    models_dir = Path(models_dir)
    models_dir.mkdir(parents=True, exist_ok=True)

    X = build_features(df)
    y_demand = df["units_sold"].astype(float)
    y_conv = df["converted"].astype(int)

    Xtr, Xte, ytr_d, yte_d, ytr_c, yte_c = train_test_split(
        X, y_demand, y_conv, test_size=0.2, random_state=42
    )

    # --- Regression: demand forecasting ---
    regressor = Pipeline(
        steps=[
            ("prep", _preprocessor()),
            ("model", GradientBoostingRegressor(random_state=42)),
        ]
    )
    regressor.fit(Xtr, ytr_d)
    pred_d = regressor.predict(Xte)
    reg_metrics = {
        "mae": round(float(mean_absolute_error(yte_d, pred_d)), 3),
        "r2": round(float(r2_score(yte_d, pred_d)), 3),
    }

    # --- Classification: purchase / conversion likelihood ---
    classifier = Pipeline(
        steps=[
            ("prep", _preprocessor()),
            ("model", RandomForestClassifier(n_estimators=200, random_state=42)),
        ]
    )
    classifier.fit(Xtr, ytr_c)
    proba = classifier.predict_proba(Xte)[:, 1]
    preds = classifier.predict(Xte)
    clf_metrics = {
        "accuracy": round(float(accuracy_score(yte_c, preds)), 3),
        "roc_auc": round(float(roc_auc_score(yte_c, proba)), 3),
    }

    joblib.dump(regressor, models_dir / REGRESSOR_FILE)
    joblib.dump(classifier, models_dir / CLASSIFIER_FILE)

    return {"regression": reg_metrics, "classification": clf_metrics,
            "train_rows": len(Xtr), "test_rows": len(Xte)}


class DemandPredictor:
    """Loads the trained models and exposes simple predict helpers."""

    def __init__(self, models_dir: Path):
        models_dir = Path(models_dir)
        self.regressor = joblib.load(models_dir / REGRESSOR_FILE)
        self.classifier = joblib.load(models_dir / CLASSIFIER_FILE)

    def predict_demand(self, feature_rows: pd.DataFrame) -> list:
        X = build_features(feature_rows)
        return [max(0.0, float(v)) for v in self.regressor.predict(X)]

    def predict_conversion(self, feature_rows: pd.DataFrame) -> list:
        X = build_features(feature_rows)
        return [float(p) for p in self.classifier.predict_proba(X)[:, 1]]
