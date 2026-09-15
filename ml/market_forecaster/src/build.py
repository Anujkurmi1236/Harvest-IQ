"""
Build training data for the market price forecaster.

Design decision (and why): the raw price level (LCU/tonne or the Index) has
a strong upward trend that's mostly currency inflation compounding over 35
years, not a real market signal - predicting it directly would mean the
model just learns "prices go up," which is hollow. So the TARGET here is
the year-over-year % change in the Producer Price Index, and the eventual
forecast reconstructs a future price level by compounding that predicted
growth rate onto the last known real value - not by predicting the level
directly.

Why the Index (2014-2016=100) and not raw LCU/tonne: LCU prices are on a
wildly different absolute scale per crop (like the yield model's sugarcane-
vs-everything-else problem) AND carry decades of nominal inflation. The
Index is base-100 for every item, making growth rates comparable across
crops. India_Prices_Data.csv (1966-1990, LCU only, pre-dates the Index) is
NOT used here for that reason - it can't be reconciled onto the same scale
without a price deflator this dataset doesn't provide. This model's
effective history is 1991-2025 only; that's a real scope limit, not an
oversight.
"""

import pandas as pd
import numpy as np
import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
OUT_DIR = BASE_DIR / "output"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# DATA_DIR = "data"
# OUT_DIR = "output"
# os.makedirs(OUT_DIR, exist_ok=True)

PRICES_FILE = "India_Prices_E_All_Data_Normalized.csv"
N_LAGS = 3 


def load(name):
    return pd.read_csv(os.path.join(DATA_DIR, name))


def build_index_series():
    df = load(PRICES_FILE)
    idx = df[df["Element"] == "Producer Price Index (2014-2016 = 100)"][
        ["Year", "Item", "Value"]
    ].rename(columns={"Value": "index_level"})
    idx = idx.sort_values(["Item", "Year"])
    return idx


def add_growth_and_lags(idx):
    idx = idx.copy()
    idx["pct_change"] = idx.groupby("Item")["index_level"].pct_change() * 100

    for lag in range(1, N_LAGS + 1):
        idx[f"pct_change_lag{lag}"] = idx.groupby("Item")["pct_change"].shift(lag)

    idx["rolling_mean_growth_3yr"] = (
        idx.groupby("Item")["pct_change"].shift(1).rolling(3).mean().reset_index(level=0, drop=True)
    )

    # the TARGET: next year's growth rate, known only in hindsight - this is
    # what the model learns to predict from this year's info
    idx["target_next_pct_change"] = idx.groupby("Item")["pct_change"].shift(-1)
    # needed at inference time to reconstruct the forecast level from a
    # predicted growth rate, kept alongside but not used as a feature
    idx["next_year_actual_level"] = idx.groupby("Item")["index_level"].shift(-1)

    return idx


def main():
    idx = build_index_series()
    idx = add_growth_and_lags(idx)

    # first N_LAGS+1 years of every item lack full lag history - can't be used
    # as training rows (not a data quality issue, just insufficient history)
    feature_cols = ["Year", "pct_change"] + [f"pct_change_lag{i}" for i in range(1, N_LAGS + 1)] + [
        "rolling_mean_growth_3yr"
    ]
    target_col = "target_next_pct_change"

    usable = idx.dropna(subset=feature_cols + [target_col]).copy()

    item_dummies = pd.get_dummies(usable["Item"], prefix="item", dtype=np.float32)
    usable = pd.concat([usable, item_dummies], axis=1)

    all_feature_cols = feature_cols + list(item_dummies.columns)

    usable.to_csv(os.path.join(OUT_DIR, "merged_price_table.csv"), index=False)
    idx.to_csv(os.path.join(OUT_DIR, "full_index_series.csv"), index=False)  # kept for inference lookups

    X = usable[all_feature_cols].to_numpy(dtype=np.float32)
    y = usable[target_col].to_numpy(dtype=np.float32)
    years = usable["Year"].to_numpy()

    np.save(os.path.join(OUT_DIR, "X.npy"), X)
    np.save(os.path.join(OUT_DIR, "y.npy"), y)
    np.save(os.path.join(OUT_DIR, "years.npy"), years)
    with open(os.path.join(OUT_DIR, "feature_names.txt"), "w") as f:
        f.write("\n".join(all_feature_cols))

    print(f"Usable training rows: {usable.shape[0]} (from {idx.shape[0]} raw item-year rows, "
          f"{idx['Item'].nunique()} items)")
    print(f"Features: {len(all_feature_cols)} ({len(feature_cols)} numeric/lag, "
          f"{len(item_dummies.columns)} item one-hot)")
    print(f"Target: {target_col} (% growth from Year to Year+1)")
    print(f"Year range: {int(years.min())}-{int(years.max())}")


if __name__ == "__main__":
    main()