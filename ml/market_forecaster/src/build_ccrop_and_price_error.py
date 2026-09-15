"""
Per-crop error stats for the price growth model, same purpose as
yield_pred's crop_error_stats.csv: a single pooled error number is
misleading when accuracy varies this much by crop. Uses Mean Absolute
Error in percentage points (not MAPE) because the target is already a %
value that can sit near zero, where MAPE blows up meaninglessly.
"""

import os
import numpy as np
import pandas as pd
import xgboost as xgb
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
OUT_DIR = BASE_DIR / "output"
TEST_YEARS_FRACTION = 0.2


def main():
    X = np.load(os.path.join(OUT_DIR, "X.npy"))
    y = np.load(os.path.join(OUT_DIR, "y.npy"))
    years = np.load(os.path.join(OUT_DIR, "years.npy"))
    with open(os.path.join(OUT_DIR, "feature_names.txt")) as f:
        feature_names = f.read().splitlines()

    merged = pd.read_csv(os.path.join(OUT_DIR, "merged_price_table.csv"))

    unique_years = np.sort(np.unique(years))
    cutoff_year = unique_years[int(len(unique_years) * (1 - TEST_YEARS_FRACTION))]
    train_mask = years < cutoff_year
    test_mask = years >= cutoff_year

    model = xgb.XGBRegressor(
        n_estimators=400, learning_rate=0.03, max_depth=4,
        subsample=0.8, colsample_bytree=0.7, reg_lambda=3.0,
        objective="reg:squarederror", random_state=42,
    )
    model.fit(X[train_mask], y[train_mask])
    preds = model.predict(X[test_mask])

    test_items = np.asarray(merged.loc[test_mask, "Item"])
    errors = pd.DataFrame({
        "Item": test_items,
        "actual": y[test_mask],
        "predicted": preds,
    })
    errors["abs_error_pp"] = np.abs(errors["actual"] - errors["predicted"])

    overall_mae = errors["abs_error_pp"].mean()

    stats = (
        errors.groupby("Item")
        .agg(n_test_rows=("abs_error_pp", "size"), mae_pp=("abs_error_pp", "mean"))
        .sort_values("mae_pp")
    )
    stats["low_confidence"] = stats["n_test_rows"] < 3
    stats.to_csv(os.path.join(OUT_DIR, "crop_price_error_stats.csv"))

    print(f"Overall MAE: {overall_mae:.2f} percentage points")
    print(f"Crops covered in test set: {len(stats)} / {merged['Item'].nunique()}")
    print(stats.head(10))


if __name__ == "__main__":
    main()