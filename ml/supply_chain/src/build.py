"""
Build the supply chain reference table: per-crop Loss Rate and Sellable
Share, computed directly from real Food Balance Sheet data (not benchmarks,
not assumptions - these are actual observed national ratios).

- loss_rate_pct = Losses / Production * 100
    Real spoilage/wastage during storage & transport, per crop, as a % of
    what was produced. Used by the optimizer as the "cost of holding" driver.
- sellable_share_pct = Food / Domestic supply quantity * 100
    How much of what's domestically available actually reaches the food
    market vs. being diverted to feed/seed/processing/other uses. Used to
    scale a raw harvest quantity down to what's actually sellable as food.

Both are averaged over the most recent 5 years (2019-2023) for stability -
a single year's ratio can be noisy (e.g. a bad-storage year inflates
Losses), and only items with real Production data are kept (excludes
aggregate rows like 'Vegetal Products', 'Grand Total', 'Population').
"""

import pandas as pd
import os
from pathlib import Path

BASE_DIR = Path(__file__).parent.resolve()

DATA_DIR = BASE_DIR.parent / "data"
OUT_DIR = BASE_DIR / "output"
os.makedirs(OUT_DIR, exist_ok=True)

FBS_FILE = "India_FoodBalanceSheets.csv"
RECENT_YEARS = 5

# aggregate/non-crop rows in the FBS Item list that shouldn't be treated as
# individual crops for a per-crop supply chain lookup
EXCLUDE_ITEMS = {
    "Population", "Grand Total", "Vegetal Products", "Animal Products",
    "Cereals - Excluding Beer", "Sugar Crops", "Sugar & Sweeteners",
    "Starchy Roots",
}


def main():
    df = pd.read_csv(os.path.join(DATA_DIR, FBS_FILE))
    df = df[~df["Item"].isin(EXCLUDE_ITEMS)]

    max_year = df["Year"].max()
    recent = df[df["Year"] > max_year - RECENT_YEARS]

    wide = recent.pivot_table(index=["Item", "Year"], columns="Element", values="Value").reset_index()

    required = ["Production", "Losses", "Food", "Domestic supply quantity"]
    missing = [c for c in required if c not in wide.columns]
    if missing:
        raise ValueError(f"Missing expected FBS elements: {missing}")

    wide = wide.dropna(subset=required)
    wide = wide[wide["Production"] > 0]  # avoid divide-by-zero / meaningless ratios

    wide["loss_rate_pct"] = wide["Losses"] / wide["Production"] * 100
    wide["sellable_share_pct"] = wide["Food"] / wide["Domestic supply quantity"] * 100

    ref = (
        wide.groupby("Item")
        .agg(
            loss_rate_pct=("loss_rate_pct", "mean"),
            sellable_share_pct=("sellable_share_pct", "mean"),
            n_years=("Year", "nunique"),
            latest_production_1000t=("Production", "last"),
        )
        .round(2)
    )
    fallback_loss = ref["loss_rate_pct"].mean()
    fallback_sellable = ref["sellable_share_pct"].mean()

    ref.to_csv(os.path.join(OUT_DIR, "supply_chain_reference.csv"))
    with open(os.path.join(OUT_DIR, "fallback_rates.txt"), "w") as f:
        f.write(f"{fallback_loss}\n{fallback_sellable}\n")

    print(f"Reference table: {len(ref)} crops, averaged over the {RECENT_YEARS} most recent years "
          f"({int(max_year - RECENT_YEARS + 1)}-{int(max_year)})")
    print(f"Fallback (all-crop average) loss rate: {fallback_loss:.2f}%, "
          f"sellable share: {fallback_sellable:.2f}%")
    print(ref.sort_values("loss_rate_pct", ascending=False).head(10))


if __name__ == "__main__":
    main()