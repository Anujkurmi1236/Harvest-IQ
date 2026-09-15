"""
Final inference wrapper for the market price forecaster.

Predicts a price INDEX LEVEL for a crop/year, but does it by predicting the
year-over-year % growth rate and compounding it onto the last known real
value - not by predicting the level directly (see build_price_training_data.py
for why: raw level is dominated by 35 years of inflation trend).

For years beyond the last known data, this recursively forecasts one year
at a time: predict next year's growth -> compute the new level and lag
features -> predict the year after that -> repeat. Each additional step
compounds uncertainty, so the confidence range widens with distance from
the last known year (sqrt(steps) scaling on this crop's own test-set MAE -
a standard approximation for compounding independent errors, not an exact
guarantee).

Same ok/error/notes contract as yield_pred/predict.py and
weather_model/predict.py, so all three sit interchangeably in the same
LangGraph orchestration.
"""

from pathlib import Path
import sys
from typing import cast
import numpy as np
import pandas as pd
import xgboost as xgb

SCRIPT_DIR = Path(__file__).resolve().parent
OUT_DIR = SCRIPT_DIR.parent / "output"
N_LAGS = 3

_state = {}


def _load():
    if _state:
        return (_state["model"], _state["series"], _state["error_stats"],
                _state["fallback_mae"], _state["feature_names"])

    model = xgb.XGBRegressor()
    model.load_model(OUT_DIR / "price_growth_model_final.json")

    with open(OUT_DIR / "feature_names.txt") as f:
        feature_names = f.read().splitlines()

    series = pd.read_csv(OUT_DIR / "full_index_series.csv")
    error_stats = pd.read_csv(OUT_DIR / "crop_price_error_stats.csv", index_col="Item")
    fallback_mae = float(
        (error_stats["mae_pp"] * error_stats["n_test_rows"]).sum()
        / error_stats["n_test_rows"].sum()
    )

    _state.update(model=model, series=series, error_stats=error_stats,
                  fallback_mae=fallback_mae, feature_names=feature_names)
    return model, series, error_stats, fallback_mae, feature_names


def _feature_row(year, level_history, growth_history):
    """Build one row of model inputs from the growth history seen so far."""
    lags = (growth_history[-N_LAGS:] + [np.nan] * N_LAGS)[:N_LAGS]  # most recent first, padded
    row = {
        "Year": year,
        "pct_change": growth_history[-1],
        "pct_change_lag1": lags[0] if len(growth_history) >= 1 else np.nan,
        "pct_change_lag2": lags[1] if len(growth_history) >= 2 else np.nan,
        "pct_change_lag3": lags[2] if len(growth_history) >= 3 else np.nan,
        "rolling_mean_growth_3yr": float(np.mean(growth_history[-3:])),
    }
    return row


def predict_price(item: str, year: int) -> dict:
    """
    Forecast the Producer Price Index level for a crop/year.

    item: crop name - must match the FAOSTAT India price dataset's Item names.
    year: target year. If <= the last year with real data, the actual
        historical value is returned directly (no forecasting needed). If
        beyond it, forecasts recursively one year at a time.

    Returns a dict. On success:
        ok, item, year, predicted_index_level, is_historical (bool - True if
        this is real data, not a forecast), predicted_growth_pct (only for
        forecasted years), low_index_level, high_index_level,
        typical_error_pp, steps_ahead, low_confidence, notes
    On failure: ok=False, error, valid_items (only for unknown-crop errors)
    """
    model, series, error_stats, fallback_mae, feature_names = _load()
    notes = []

    valid_items = series["Item"].unique().tolist()
    if item not in valid_items:
        return {"ok": False, "error": f"Unknown crop '{item}'.", "valid_items": valid_items}

    item_hist = series[series["Item"] == item].sort_values("Year")
    known = item_hist.dropna(subset=["index_level"])
    last_known_year = int(known["Year"].max())
    last_known_level = float(known.loc[known["Year"] == last_known_year, "index_level"].iloc[0])

    if year <= last_known_year:
        row = known[known["Year"] == year]
        if row.empty:
            return {"ok": False, "error": f"No recorded price data for {item} in {year}."}
        return {
            "ok": True,
            "item": item,
            "year": year,
            "predicted_index_level": round(float(row["index_level"].iloc[0]), 2),
            "is_historical": True,
            "notes": [],
        }

    # recursive multi-step forecast from last_known_year+1 up to `year`
    growth_history = known["pct_change"].dropna().tail(N_LAGS).tolist()
    if len(growth_history) < 1:
        return {"ok": False, "error": f"Not enough growth history for {item} to forecast."}

    level = last_known_level
    steps = year - last_known_year
    for step_year in range(last_known_year + 1, year + 1):
        row = _feature_row(step_year, [level], growth_history)
        item_col = f"item_{item}"
        row_full = {c: 0.0 for c in feature_names}
        row_full.update(row)
        if item_col in feature_names:
            row_full[item_col] = 1.0
        X_row = pd.DataFrame([row_full], columns=feature_names)
        predicted_growth = float(model.predict(X_row)[0])

        level = level * (1 + predicted_growth / 100)
        growth_history.append(predicted_growth)
        growth_history = growth_history[-N_LAGS:]

    if item in error_stats.index and not bool(error_stats.loc[item, "low_confidence"]):
        typical_error_pp = float(cast(float, error_stats.loc[item, "mae_pp"]))
        low_confidence = False
    else:
        typical_error_pp = fallback_mae
        low_confidence = True
        notes.append("This crop had little/no held-out test data; using the pooled "
                      "average error rate instead of a crop-specific one.")

    compounded_error_pp = typical_error_pp * np.sqrt(steps)
    low_level = level * (1 - compounded_error_pp / 100)
    high_level = level * (1 + compounded_error_pp / 100)

    if steps > 1:
        notes.append(f"Forecast is {steps} years beyond the last known data point "
                      f"({last_known_year}); each extra year compounds uncertainty.")

    return {
        "ok": True,
        "item": item,
        "year": year,
        "predicted_index_level": round(level, 2),
        "is_historical": False,
        "last_known_year": last_known_year,
        "last_known_index_level": round(last_known_level, 2),
        "low_index_level": round(float(max(low_level, 0)), 2),
        "high_index_level": round(float(high_level), 2),
        "typical_error_pp": round(typical_error_pp, 2),
        "steps_ahead": steps,
        "low_confidence": low_confidence,
        "notes": notes,
    }


def _cli():
    import argparse
    parser = argparse.ArgumentParser(description="Forecast crop price index level.")
    parser.add_argument("--item", required=True)
    parser.add_argument("--year", required=True, type=int)
    args = parser.parse_args()

    result = predict_price(args.item, args.year)
    if not result["ok"]:
        print(f"\nError: {result['error']}")
        sys.exit(1)

    print(f"\n{result['item']} — {result['year']}")
    if result["is_historical"]:
        print(f"  Actual (historical) index level: {result['predicted_index_level']}")
    else:
        print(f"  Predicted index level: {result['predicted_index_level']} "
              f"(range {result['low_index_level']} - {result['high_index_level']}, "
              f"± {result['typical_error_pp']:.1f}pp x sqrt({result['steps_ahead']}) compounded)")
        for note in result["notes"]:
            print(f"  Note: {note}")


if __name__ == "__main__":
    _cli()