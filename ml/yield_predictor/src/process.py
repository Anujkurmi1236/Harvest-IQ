import pandas as pd
import numpy as np
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data" / "processed" / "req_data"
OUT_DIR = BASE_DIR / "output"
OUT_DIR.mkdir(parents=True, exist_ok=True)

CROPS_FILE = "india_Production_Crops_Livestock_E_All_Data_(Normalized).csv"
FERT_PRODUCT_FILE = "india_Inputs_FertilizersProduct_E_All_Data_(Normalized).csv"
FERT_NUTRIENT_FILE = "india_Inputs_FertilizersNutrient_E_All_Data_(Normalized).csv"
SOIL_FILE = "india_Environment_Soil_nutrient_budget_E_All_Data_(Normalized).csv"
TEMP_FILE = "india_Environment_Temperature_change_E_All_Data_(Normalized).csv"

MAX_ITEM_CATEGORIES = 100  

def load(name):
    path = DATA_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"Missing data file: {path}")
    return pd.read_csv(path)


def build_crop_level_table():
    """
    Pivot Production_Crops_Livestock to one row per (Year, Item), keeping
    only genuine crop yield rows (Unit == 'kg/ha') - this drops livestock
    rows reported in 'No/An' (head count) or carcass-weight units, which
    aren't comparable to crop yield and would corrupt a single regression
    target if mixed in.
    """
    df = load(CROPS_FILE)

    yield_items = df.loc[
        (df["Element"] == "Yield") & (df["Unit"] == "kg/ha"), "Item"
    ].unique()
    df = df[df["Item"].isin(yield_items)].copy()

    df_wide = df.pivot_table(
        index=["Year", "Item"], columns="Element", values="Value", aggfunc="first"
    ).reset_index()
    df_wide.columns.name = None

    flag_map = (
        df.groupby(["Year", "Item"])["Flag"]
        .apply(lambda x: 1 if (x == "A").any() else 0)
        .reset_index()
    )
    flag_map.columns = ["Year", "Item", "Data_Reliability"]
    df_wide = df_wide.merge(flag_map, on=["Year", "Item"], how="left")

    keep_cols = ["Year", "Item", "Data_Reliability"]
    for c in ["Yield", "Area harvested", "Production"]:
        if c in df_wide.columns:
            keep_cols.append(c)
    df_wide = df_wide[keep_cols]

    print(f"Crop-level table: {df_wide.shape}, {df_wide['Item'].nunique()} crops, "
          f"years {df_wide['Year'].min()}-{df_wide['Year'].max()}")
    return df_wide


def build_year_level_table(filename, group_key, prefix):
    """
    Pivot a national (no crop breakdown) dataset to one row per Year.
    Columns become '{prefix}__{group_key value}__{Element}', e.g.
    'fertprod__Urea__Import value'. This keeps every Item/Months x Element
    combination as its own yearly feature instead of forcing an arbitrary
    single target/column choice.
    """
    df = load(filename)
    df["_col"] = prefix + "__" + df[group_key].astype(str) + "__" + df["Element"].astype(str)

    wide = df.pivot_table(index="Year", columns="_col", values="Value", aggfunc="mean")
    wide.columns.name = None
    wide = wide.reset_index()

    print(f"{prefix} year-level table: {wide.shape} (from {filename})")
    return wide


def main():
    crop_tbl = build_crop_level_table()
    fert_product_tbl = build_year_level_table(FERT_PRODUCT_FILE, "Item", "fertprod")
    fert_nutrient_tbl = build_year_level_table(FERT_NUTRIENT_FILE, "Item", "fertnut")
    soil_tbl = build_year_level_table(SOIL_FILE, "Item", "soil")
    temp_tbl = build_year_level_table(TEMP_FILE, "Months", "temp")

    merged = crop_tbl.copy()
    for tbl in [fert_product_tbl, fert_nutrient_tbl, soil_tbl, temp_tbl]:
        merged = merged.merge(tbl, on="Year", how="left")

    # Crop identity - one-hot encode (97 crops, all kept as their own category)
    item_dummies = pd.get_dummies(merged["Item"], prefix="item", dtype=np.float32)
    merged = pd.concat([merged, item_dummies], axis=1)

    target_col = "Yield"
    merged = merged.dropna(subset=[target_col])  # never zero-fill a missing label

    macro_feature_cols = [c for c in merged.columns
                           if c.startswith(("fertprod__", "fertnut__", "soil__", "temp__"))]
    merged[macro_feature_cols] = merged[macro_feature_cols].fillna(0)

    feature_cols = (
        ["Year", "Data_Reliability"]
        + (["Area harvested"] if "Area harvested" in merged.columns else [])
        + macro_feature_cols
        + list(item_dummies.columns)
    )

    merged.to_csv(OUT_DIR / "merged_training_table.csv", index=False)

    X = merged[feature_cols].to_numpy(dtype=np.float32)
    y = merged[target_col].to_numpy(dtype=np.float32)
    years = merged["Year"].to_numpy()

    np.save(OUT_DIR / "X.npy", X)
    np.save(OUT_DIR / "y.npy", y)
    np.save(OUT_DIR / "years.npy", years)
    with open(OUT_DIR / "feature_names.txt", "w") as f:
        f.write("\n".join(feature_cols))

    print(f"\nFinal training table: X={X.shape}, y={y.shape}")
    print(f"Target: {target_col} (kg/ha), rows dropped for missing target: "
          f"{len(crop_tbl) - len(merged)}")
    print(f"Feature groups -> crop-level: {2 + ('Area harvested' in merged.columns)}, "
          f"macro (fert/soil/temp): {len(macro_feature_cols)}, "
          f"crop one-hot: {len(item_dummies.columns)}")


if __name__ == "__main__":
    main()