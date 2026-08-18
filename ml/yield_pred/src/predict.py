"""
Final inference wrapper for the crop yield model.

The trained pipeline needs ~196 numeric inputs (Year, Data_Reliability,
Area harvested, plus ~193 national fertilizer/soil/temperature features)
and 1 categorical input (Item). A user predicting yield only knows the crop
and the year - they don't have fertilizer import volumes or soil nutrient
flow numbers on hand. So this wrapper:

1. Builds a Year -> macro-features lookup table from the training data
   (each macro feature is a national yearly aggregate, so it's the same
   value for every crop in that year anyway - see build_training_data.py).
2. Builds a per-crop median Area harvested, used only if the caller
   doesn't supply one.
3. Loads crop_error_stats.csv (each crop's own held-out-year MAPE, saved
   by the notebook) and uses THAT crop's real error rate to turn the point
   prediction into a range - a global 79% MAPE is meaningless for a crop
   whose own test-year error was actually 2.5%. Crops with fewer than 3
   held-out test rows, or crops absent from the test years entirely, fall
   back to the overall pooled MAPE and are flagged low_confidence=True.
4. Exposes predict_yield(item, year, area_harvested=None) as the single
   entry point, plus list_crops() so the caller can see valid crop names.

If `year` is beyond the range of the fertilizer/soil/temperature data
(these datasets don't extend as far as the crop production data), the
closest available year's macro context is reused, with a printed note -
this is a real accuracy limitation, not silently ignored.
"""

from pathlib import Path
import sys
from typing import Optional
import pandas as pd
import joblib

SCRIPT_DIR = Path(__file__).resolve().parent
OUT_DIR = SCRIPT_DIR.parent / "output"
DATA_PATH = OUT_DIR / "merged_training_table.csv"
PIPELINE_PATH = OUT_DIR / "yield_pipeline.joblib"
ERROR_STATS_PATH = OUT_DIR / "crop_error_stats.csv"

_state = {}


def _load():
    if _state:
        return (_state["pipeline"], _state["macro_lookup"], _state["area_lookup"],
                _state["valid_items"], _state["error_stats"], _state["fallback_mape"])

    pipeline = joblib.load(PIPELINE_PATH)
    df = pd.read_csv(DATA_PATH)

    macro_cols = [c for c in df.columns
                  if c.startswith(("fertprod__", "fertnut__", "soil__", "temp__"))]
    macro_lookup = (
        df[["Year"] + macro_cols]
        .drop_duplicates(subset="Year")
        .set_index("Year")
        .sort_index()
    )

    area_lookup = df.groupby("Item")["Area harvested"].median()
    valid_items = sorted(df["Item"].unique())

    error_stats = pd.read_csv(ERROR_STATS_PATH, index_col="Item")
    fallback_mape = float(
        (error_stats["mape"] * error_stats["n_test_rows"]).sum()
        / error_stats["n_test_rows"].sum()
    )

    _state.update(pipeline=pipeline, macro_lookup=macro_lookup, area_lookup=area_lookup,
                  valid_items=valid_items, error_stats=error_stats, fallback_mape=fallback_mape)
    return pipeline, macro_lookup, area_lookup, valid_items, error_stats, fallback_mape


def list_crops():
    """Return the list of crop names the model was trained on."""
    _, _, _, valid_items, _, _ = _load()
    return valid_items


def predict_yield(item: str, year: int, area_harvested: Optional[float] = None,
                   data_reliability: int = 1) -> dict:
    """
    Predict crop Yield (kg/ha), returned with a fluctuation range built from
    THIS crop's own held-out-year accuracy - not a single blanket error rate
    across all 96 crops, which would badly overstate uncertainty for an
    easy crop and understate it for a hard one.

    Never raises for bad input and never prints - both are dead ends inside
    an agent/orchestration loop (a raised exception can crash the graph,
    and a print() is invisible to whatever is calling this). Problems and
    context notes are returned as fields in the dict instead, so a calling
    agent (or the CLI below) can decide what to do with them.

    item: crop name - must match one of list_crops() exactly.
    year: the year to predict for.
    area_harvested: optional; if omitted, the historical median area
        harvested for this crop is used as a stand-in.
    data_reliability: 1 = treat as officially-reported-quality context, 0 =
        estimated/mirrored. Leave at 1 unless you have a specific reason.

    Returns a dict. On success:
        ok, predicted_yield_kg_ha, low_kg_ha, high_kg_ha, typical_error_pct,
        n_test_rows, low_confidence, notes (list of str)
    On failure (e.g. unknown crop):
        ok=False, error (str), valid_items (list, only on unknown-crop errors)
    """
    pipeline, macro_lookup, area_lookup, valid_items, error_stats, fallback_mape = _load()
    notes = []

    if item not in valid_items:
        return {
            "ok": False,
            "error": f"Unknown crop '{item}'.",
            "valid_items": valid_items,
        }

    lookup_year = year
    if year not in macro_lookup.index:
        lookup_year = (macro_lookup.index.max() if year > macro_lookup.index.max()
                        else macro_lookup.index.min())
        notes.append(f"No fertilizer/soil/temperature data for {year}; "
                     f"used {lookup_year}'s macro context as a stand-in.")

    if area_harvested is None:
        area_harvested = float(area_lookup.get(item, area_lookup.median()))
        notes.append(f"No area_harvested given; used this crop's historical "
                      f"median ({area_harvested:.0f} ha).")

    row = {
        "Year": year,
        "Data_Reliability": data_reliability,
        "Area harvested": area_harvested,
        "Item": item,
    }
    for col, val in macro_lookup.loc[lookup_year].items():
        row[col] = val  # type: ignore

    X = pd.DataFrame([row])
    prediction = float(pipeline.predict(X)[0])

    if item in error_stats.index and not bool(error_stats.loc[item, "low_confidence"]):
        mape_val = error_stats.loc[item, "mape"]
        n_rows_val = error_stats.loc[item, "n_test_rows"]
        typical_error_pct = float(mape_val)  # type: ignore
        n_test_rows = int(n_rows_val)  # type: ignore
        low_confidence = False
    else:
        typical_error_pct = fallback_mape
        if item in error_stats.index:
            n_rows_val = error_stats.loc[item, "n_test_rows"]
            n_test_rows = int(n_rows_val)  # type: ignore
        else:
            n_test_rows = 0
        low_confidence = True
        notes.append(f"Only {n_test_rows} held-out test row(s) for this crop; "
                      f"using the overall pooled error rate instead of a crop-specific one.")

    margin = prediction * (typical_error_pct / 100)

    return {
        "ok": True,
        "item": item,
        "year": year,
        "predicted_yield_kg_ha": round(prediction, 1),
        "low_kg_ha": round(max(prediction - margin, 0), 1),
        "high_kg_ha": round(prediction + margin, 1),
        "typical_error_pct": round(typical_error_pct, 1),
        "n_test_rows": n_test_rows,
        "low_confidence": low_confidence,
        "notes": notes,
    }


def _cli():
    import argparse
    parser = argparse.ArgumentParser(description="Predict crop yield (kg/ha).")
    parser.add_argument("--item", help="Crop name, e.g. 'Rice'")
    parser.add_argument("--year", type=int)
    parser.add_argument("--area", type=float, default=None,
                         help="Area harvested (ha); defaults to this crop's historical median")
    parser.add_argument("--list-crops", action="store_true",
                         help="Print valid crop names and exit")
    args = parser.parse_args()

    if args.list_crops:
        for name in list_crops():
            print(name)
        sys.exit(0)

    if args.item is None or args.year is None:
        parser.error("--item and --year are required unless using --list-crops")

    result = predict_yield(args.item, args.year, args.area)

    if not result["ok"]:
        print(f"\nError: {result['error']}")
        sys.exit(1)

    confidence_note = " (low confidence)" if result["low_confidence"] else ""
    print(f"\n{result['item']} — {result['year']}")
    print(f"  Predicted: {result['predicted_yield_kg_ha']:.1f} kg/ha")
    print(f"  Likely range: {result['low_kg_ha']:.1f} - {result['high_kg_ha']:.1f} kg/ha "
          f"(± {result['typical_error_pct']:.1f}%, based on {result['n_test_rows']} test years"
          f"{confidence_note})")
    for note in result["notes"]:
        print(f"  Note: {note}")


if __name__ == "__main__":
    _cli()