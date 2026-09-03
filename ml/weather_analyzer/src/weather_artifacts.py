import json
import os
import numpy as np
import pandas as pd
from pathlib import Path
 
PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = PROJECT_ROOT / "ml/weather_analyzer/data/req_data"
OUT_DIR = PROJECT_ROOT / "ml/weather_analyzer/output"
 
TEMP_FILE = "india_Environment_Temperature_change_E_All_Data_(Normalized).csv"
LAND_COVER_FILE = "env_land_cover.csv"
EMISSIONS_FILE = "india_climate_data.csv"
 
 
def load(name):
    path = DATA_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"Required input file not found: {path}")
    return pd.read_csv(path)
 
 
def build_temp_trend_model():
    merged = pd.read_csv(OUT_DIR / "merged_weather_table.csv")
    years = merged["Year"].to_numpy(dtype=float)
    temps = merged["Annual_Temperature_Change"].to_numpy(dtype=float)
 
    slope, intercept = np.polyfit(years, temps, 1)
 
    model = {
        "slope": float(slope),
        "intercept": float(intercept),
        "year_min": int(years.min()),
        "year_max": int(years.max()),
        # measured via walk-forward CV in train_weather_model.py - treat as the
        # typical error size, not a per-prediction guarantee, and treat it as a
        # floor: extrapolating further from year_max than any CV fold did makes
        # the true error larger than this, not smaller
        "typical_error_degC": 0.120,
    }
    with open(OUT_DIR / "temp_trend_model.json", "w") as f:
        json.dump(model, f, indent=2)
 
    print(f"Temperature trend: {slope:.5f} degC/year, intercept {intercept:.3f} "
          f"(fit on {model['year_min']}-{model['year_max']})")
    return model
 
 
def build_stress_components():
    """
    Save each component as its own sparse (Year -> value) series, keeping
    genuine gaps as gaps rather than the 0-filled version used for ML
    features - a stress index built on fabricated zeros would be wrong.
    """
    temp_df = load(TEMP_FILE)
    calendar_months = ["January", "February", "March", "April", "May", "June",
                        "July", "August", "September", "October", "November", "December"]
    temp_annual = (
        temp_df[temp_df["Months"].isin(calendar_months)]
        .groupby("Year")["Value"].mean()
        .rename("temp_change")
    )
 
    cover_df = load(LAND_COVER_FILE)
    barren = (
        cover_df[(cover_df["Item"] == "Terrestrial barren land") &
                 (cover_df["Element"] == "Area from CCI_LC")]
        .set_index("Year")["Value"].rename("barren_land")
    )
    tree_cover = (
        cover_df[(cover_df["Item"] == "Tree-covered areas") &
                 (cover_df["Element"] == "Area from CCI_LC")]
        .set_index("Year")["Value"].rename("tree_cover")
    )
 
    em_df = load(EMISSIONS_FILE)
    emissions = (
        em_df[(em_df["Item"] == "Agrifood systems") &
              (em_df["Element"] == "Emissions Share (CO2eq) (AR5)")]
        .set_index("Year")["Value"].rename("emissions_share")
    )
 
    components = pd.concat([temp_change_abs(temp_annual), barren, tree_cover, emissions], axis=1)
    components.index.name = "Year"
    components.to_csv(os.path.join(OUT_DIR, "stress_components.csv"))
 
    ranges = {
        "temp_change_abs": (
            float(components["temp_change_abs"].min()),
            float(components["temp_change_abs"].max()),
        ),
        "barren_land": (
            float(components["barren_land"].min()),
            float(components["barren_land"].max()),
        ),
        "tree_cover": (
            float(components["tree_cover"].min()),
            float(components["tree_cover"].max()),
        ),
        "emissions_share": (
            float(components["emissions_share"].min()),
            float(components["emissions_share"].max()),
        ),
    }
    with open(os.path.join(OUT_DIR, "stress_index_ranges.json"), "w") as f:
        json.dump(ranges, f, indent=2)
 
    print(f"Stress components: {components.shape}, coverage per column:")
    print(components.notna().sum())
    return components
 
 
def temp_change_abs(series):
    return series.abs().rename("temp_change_abs")
 
 
def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    build_temp_trend_model()
    build_stress_components()
 
 
if __name__ == "__main__":
    main()