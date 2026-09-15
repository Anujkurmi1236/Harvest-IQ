"""
Train a model to predict next-year price growth rate (%) per crop.

Same honesty check as the weather model: compare against naive baselines
before trusting XGBoost's complexity. Three naive baselines:
  - zero: "prices don't change" (predict 0%)
  - persistence: "next year repeats this year's growth rate"
  - historical mean: "next year = this item's 3-year rolling average growth"
If XGBoost doesn't clearly beat these, that's reported plainly, not hidden.
"""

import os
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
OUT_DIR = BASE_DIR / "output"
TEST_YEARS_FRACTION = 0.2


def load_data():
    X = np.load(os.path.join(OUT_DIR, "X.npy"))
    y = np.load(os.path.join(OUT_DIR, "y.npy"))
    years = np.load(os.path.join(OUT_DIR, "years.npy"))
    with open(os.path.join(OUT_DIR, "feature_names.txt")) as f:
        feature_names = f.read().splitlines()
    return X, y, years, feature_names


def time_based_split(X, y, years):
    unique_years = np.sort(np.unique(years))
    cutoff_year = unique_years[int(len(unique_years) * (1 - TEST_YEARS_FRACTION))]
    train_mask = years < cutoff_year
    test_mask = years >= cutoff_year
    print(f"Train: {years[train_mask].min()}-{years[train_mask].max()} ({train_mask.sum()} rows)")
    print(f"Test:  {years[test_mask].min()}-{years[test_mask].max()} ({test_mask.sum()} rows)")
    return train_mask, test_mask


def report(name, y_true, y_pred):
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    mae = mean_absolute_error(y_true, y_pred)
    r2 = r2_score(y_true, y_pred)
    print(f"{name:22s} RMSE={rmse:6.2f}  MAE={mae:6.2f}  R2={r2:6.3f}")
    return rmse


def main():
    X, y, years, feature_names = load_data()
    train_mask, test_mask = time_based_split(X, y, years)

    pct_change_idx = feature_names.index("pct_change")
    rolling_mean_idx = feature_names.index("rolling_mean_growth_3yr")

    y_test = y[test_mask]
    print()
    naive_zero_rmse = report("Naive: zero growth", y_test, np.zeros_like(y_test))
    naive_persist_rmse = report("Naive: persistence", y_test, X[test_mask, pct_change_idx])
    naive_mean_rmse = report("Naive: 3yr rolling mean", y_test, X[test_mask, rolling_mean_idx])

    model = xgb.XGBRegressor(
        n_estimators=400,
        learning_rate=0.03,
        max_depth=4,
        subsample=0.8,
        colsample_bytree=0.7,
        reg_lambda=3.0,
        objective="reg:squarederror",
        random_state=42,
    )
    model.fit(X[train_mask], y[train_mask])
    preds = model.predict(X[test_mask])
    print()
    xgb_rmse = report("XGBoost", y_test, preds)

    best_naive_rmse = min(naive_zero_rmse, naive_persist_rmse, naive_mean_rmse)
    print()
    if xgb_rmse < best_naive_rmse:
        print(f"XGBoost beats the best naive baseline ({xgb_rmse:.2f} vs {best_naive_rmse:.2f} RMSE) - keeping it.")
    else:
        print(f"XGBoost does NOT beat the best naive baseline ({xgb_rmse:.2f} vs {best_naive_rmse:.2f} RMSE) - "
              f"flagging this, the simpler baseline may be the honest choice for production.")

    model.save_model(os.path.join(OUT_DIR, "price_growth_model.json"))

    importances = pd.Series(model.feature_importances_, index=feature_names)
    top_features = importances.sort_values(ascending=False).head(15)
    print("\n=== Top 15 features ===")
    for fname, score in top_features.items():
        print(f"{score:.4f}  {fname}")
    top_features.to_csv(os.path.join(OUT_DIR, "top_feature_importances.csv"))

    pd.DataFrame({
        "year": years[test_mask], "actual_pct_change": y_test,
        "xgb_pred": preds, "naive_persistence": X[test_mask, pct_change_idx],
        "naive_rolling_mean": X[test_mask, rolling_mean_idx],
    }).to_csv(os.path.join(OUT_DIR, "test_predictions.csv"), index=False)


if __name__ == "__main__":
    main()