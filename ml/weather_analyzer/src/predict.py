import json
from pathlib import Path
import sys
import numpy as np
import pandas as pd
 
SCRIPT_DIR = Path(__file__).resolve().parent
OUT_DIR = SCRIPT_DIR.parent / "output"
 
_state = {}
 
 
def _load():
    if _state:
        return _state["trend"], _state["components"], _state["ranges"]
 
    with open(OUT_DIR / "temp_trend_model.json") as f:
        trend = json.load(f)
    components = pd.read_csv(OUT_DIR / "stress_components.csv", index_col="Year")
    with open(OUT_DIR / "stress_index_ranges.json") as f:
        ranges = json.load(f)
 
    _state.update(trend=trend, components=components, ranges=ranges)
    return trend, components, ranges
 
 
def _nearest_available(series, year):
    """Return (value, year_used) for the nearest year with real (non-NaN) data."""
    valid = series.dropna()
    if year in valid.index:
        return float(valid.loc[year]), year
    nearest_year = valid.index[np.abs(valid.index.to_numpy() - year).argmin()]
    return float(valid.loc[nearest_year]), int(nearest_year)
 
 
def _normalize(value, lo, hi, invert=False):
    if hi == lo:
        return 50.0
    score = (value - lo) / (hi - lo) * 100
    score = max(0.0, min(100.0, score))
    return 100 - score if invert else score
 
 
def predict_weather(year: int) -> dict:
    """
    Predict Annual Temperature Change and an Environmental Stress Index for
    a given year. Never raises; returns {"ok": False, "error": ...} instead
    so this can be called safely as a LangGraph tool.
 
    Returns a dict:
        ok, year, predicted_temp_change_degC, typical_error_degC,
        environmental_stress_index (0-100, higher = more stress),
        stress_components (breakdown dict for transparency), notes
    """
    trend, components, ranges = _load()
    notes = []
 
    if not isinstance(year, (int, float)):
        return {"ok": False, "error": f"year must be numeric, got {type(year).__name__}"}
    year = int(year)
 
    predicted_temp = trend["slope"] * year + trend["intercept"]
    typical_error = trend["typical_error_degC"]
    if year > trend["year_max"] or year < trend["year_min"]:
        years_out = min(abs(year - trend["year_max"]), abs(year - trend["year_min"]))
        notes.append(
            f"{year} is outside the fitted range ({trend['year_min']}-{trend['year_max']}); "
            f"extrapolated {years_out} year(s) out. Treat typical_error_degC as a floor, "
            f"not a guarantee, this far from the data."
        )
 
    stress_parts = {}
    for col, invert in [("temp_change_abs", False), ("barren_land", False),
                         ("tree_cover", True), ("emissions_share", False)]:
        value, used_year = _nearest_available(components[col], year)
        lo, hi = ranges[col]
        score = _normalize(value, lo, hi, invert=invert)
        stress_parts[col] = round(score, 1)
        if used_year != year:
            notes.append(f"No {col} data for {year}; used {used_year}'s value.")
 
    stress_index = round(sum(stress_parts.values()) / len(stress_parts), 1)
 
    return {
        "ok": True,
        "year": year,
        "predicted_temp_change_degC": round(predicted_temp, 3),
        "typical_error_degC": typical_error,
        "environmental_stress_index": stress_index,
        "stress_components": stress_parts,
        "notes": notes,
    }
 
 
def _cli():
    import argparse
    parser = argparse.ArgumentParser(description="Predict temperature change + environmental stress index.")
    parser.add_argument("--year", required=True, type=int)
    args = parser.parse_args()
 
    result = predict_weather(args.year)
    if not result["ok"]:
        print(f"\nError: {result['error']}")
        sys.exit(1)
 
    print(f"\nYear {result['year']}")
    print(f"  Predicted temperature change: {result['predicted_temp_change_degC']:.3f} °C "
          f"(typical error ± {result['typical_error_degC']:.3f} °C)")
    print(f"  Environmental Stress Index: {result['environmental_stress_index']:.1f} / 100")
    print(f"  Components: {result['stress_components']}")
    for note in result["notes"]:
        print(f"  Note: {note}")
 
 
if __name__ == "__main__":
    _cli()