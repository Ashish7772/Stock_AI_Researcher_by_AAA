from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, balanced_accuracy_score, precision_score, recall_score

from app.technical import feature_columns

LABELS = ["bearish", "sideways", "bullish"]


def _dataset(df: pd.DataFrame, horizon: int, threshold: float):
    x = df.copy()
    future = x["close"].shift(-horizon) / x["close"] - 1
    y = pd.Series(np.select([future >= threshold, future <= -threshold], [2, 0], default=1), index=x.index)
    features = x[feature_columns()].replace([np.inf, -np.inf], np.nan)
    data = pd.concat([features, y.rename("target"), future.rename("future_return")], axis=1).dropna()
    return data


def train_and_predict(df: pd.DataFrame, horizon: int, threshold: float = 0.04):
    data = _dataset(df, horizon, threshold)
    if len(data) < 250:
        return None
    X = data[feature_columns()]
    y = data["target"].astype(int)
    model = RandomForestClassifier(
        n_estimators=400,
        max_depth=8,
        min_samples_leaf=8,
        class_weight="balanced_subsample",
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X, y)
    latest = df.iloc[[-1]][feature_columns()].replace([np.inf, -np.inf], np.nan)
    if latest.isna().any(axis=None):
        return None
    proba = model.predict_proba(latest)[0]
    output = {"bearish": 0.0, "sideways": 0.0, "bullish": 0.0}
    for cls, prob in zip(model.classes_, proba):
        output[LABELS[int(cls)]] = float(prob * 100)
    return output


def walk_forward_backtest(df: pd.DataFrame, horizon: int, threshold: float = 0.04, folds: int = 6):
    data = _dataset(df, horizon, threshold)
    if len(data) < 400:
        return None
    X = data[feature_columns()]
    y = data["target"].astype(int)
    n = len(data)
    results = []
    for i in range(folds):
        train_end = int(n * (0.45 + i * 0.07))
        test_end = int(n * (0.52 + i * 0.07))
        if test_end <= train_end or test_end > n:
            continue
        model = RandomForestClassifier(
            n_estimators=250, max_depth=8, min_samples_leaf=8,
            class_weight="balanced_subsample", random_state=100 + i, n_jobs=-1,
        )
        # Purge the final horizon rows from the training sample so labels do not
        # overlap the first test observations.
        fit_end = max(0, train_end - horizon)
        if fit_end < 100:
            continue
        model.fit(X.iloc[:fit_end], y.iloc[:fit_end])
        pred = model.predict(X.iloc[train_end:test_end])
        actual = y.iloc[train_end:test_end]
        if len(actual) == 0:
            continue
        results.append({
            "accuracy": float(accuracy_score(actual, pred)),
            "balanced_accuracy": float(balanced_accuracy_score(actual, pred)),
            "precision_macro": float(precision_score(actual, pred, labels=[0, 1, 2], average="macro", zero_division=0)),
            "recall_macro": float(recall_score(actual, pred, labels=[0, 1, 2], average="macro", zero_division=0)),
        })
    if not results:
        return None
    keys = results[0].keys()
    return {k: float(np.mean([r[k] for r in results])) for k in keys} | {"folds": len(results)}
