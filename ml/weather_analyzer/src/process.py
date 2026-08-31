import pandas as pd
import numpy as np
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data" / "processed" / "req_data"
OUT_DIR = BASE_DIR / "output"
OUT_DIR.mkdir(parents=True, exist_ok=True)  

ENV_LAND_COVER_FILE = "env_land_cover.csv"
ENV_LAND_USE_FILE = "env_land_use.csv"
IND_CLIMATE_FILE = "india_climate_data.csv"
ENV_TEMP_CHANGE_FILE = "india_Environment_Temperature_change_E_All_Data_(Normalized).csv"

def load(name):
    path = DATA_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"Missing data file: {path}")
    return pd.read_csv(path)

def build_temperature_target():
    """
    Temperature Change file is monthly (Jan-Dec rows per year, plus some
    seasonal aggregates FAOSTAT includes like 'Meteorological year'). Use
    the calendar-month rows only, averaged to one Annual Temperature Change
    value per Year - this is the target.
    """
    df = load(ENV_TEMP_CHANGE_FILE)
    calendar_months = [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December",
    ]
    monthly = df[df["Months"].isin(calendar_months)]
 
    annual = (
        monthly.groupby("Year")["Value"]
        .mean()
        .rename("Annual_Temperature_Change")
        .reset_index()
    )
    monthly_std = (
        monthly.groupby("Year")["Value"]
        .std()
        .rename("Temperature_Change_Volatility")
        .reset_index()
    )
    annual = annual.merge(monthly_std, on="Year", how="left")
 
    print(f"Temperature target: {annual.shape}, years "
          f"{annual['Year'].min()}-{annual['Year'].max()}")
    return annual

def build_land_cover_table():
    df = load(ENV_LAND_COVER_FILE)
    primary = df[df["Element"] == "Area from CCI_LC"][["Year", "Item", "Value"]]
    fallback = df[df["Element"] == "Area from MODIS"][["Year", "Item", "Value"]]
 
    combined = pd.concat([primary, fallback]).drop_duplicates(subset=["Year", "Item"], keep="first")
    combined["_col"] = "landcover__" + combined["Item"].astype(str)
    wide = combined.pivot_table(index="Year", columns="_col", values="Value", aggfunc="mean").reset_index()
    wide.columns.name = None
    print(f"Land cover table: {wide.shape}, years {wide['Year'].min()}-{wide['Year'].max()} "
          f"(CCI_LC primary, MODIS fills gaps)")
    return wide

def build_land_use_table():
    df = load(ENV_LAND_USE_FILE)
    df["_col"] = "landuse__" + df["Item"].astype(str) + "__" + df["Element"].astype(str)
    wide = df.pivot_table(index="Year", columns="_col", values="Value", aggfunc="mean").reset_index()
    wide.columns.name = None
    print(f"Land use table: {wide.shape}, years {wide['Year'].min()}-{wide['Year'].max()}")
    return wide


def build_emissions_table():
    df = load(IND_CLIMATE_FILE)
    df["_col"] = "emissions__" + df["Item"].astype(str) + "__" + df["Element"].astype(str)
    wide = df.pivot_table(index="Year", columns="_col", values="Value", aggfunc="mean").reset_index()
    wide.columns.name = None
    print(f"Emissions table: {wide.shape}, years {wide['Year'].min()}-{wide['Year'].max()}")
    return wide

def main():
    target_tbl = build_temperature_target()
    land_use_tbl = build_land_use_table()
    land_cover_tbl = build_land_cover_table()
    emissions_tbl = build_emissions_table()
 
    merged = target_tbl.copy()
    for tbl in [land_use_tbl, land_cover_tbl, emissions_tbl]:
        merged = merged.merge(tbl, on="Year", how="left")
 
    target_col = "Annual_Temperature_Change"
    merged = merged.dropna(subset=[target_col])  # never zero-fill a missing label
 
    context_feature_cols = [c for c in merged.columns
                              if c.startswith(("landuse__", "landcover__", "emissions__"))]
    merged[context_feature_cols] = merged[context_feature_cols].fillna(0)
 
    feature_cols = ["Year", "Temperature_Change_Volatility"] + context_feature_cols
 
    merged.to_csv(os.path.join(OUT_DIR, "merged_weather_table.csv"), index=False)
 
    X = merged[feature_cols].to_numpy(dtype=np.float32)
    y = merged[target_col].to_numpy(dtype=np.float32)
    years = merged["Year"].to_numpy()
 
    np.save(os.path.join(OUT_DIR, "X.npy"), X)
    np.save(os.path.join(OUT_DIR, "y.npy"), y)
    np.save(os.path.join(OUT_DIR, "years.npy"), years)
    with open(os.path.join(OUT_DIR, "feature_names.txt"), "w") as f:
        f.write("\n".join(feature_cols))
 
    print(f"\nFinal training table: X={X.shape}, y={y.shape}")
    print(f"Target: {target_col} (deg C), years {int(years.min())}-{int(years.max())}")
    print(f"Context features: {len(context_feature_cols)} "
          f"(land use: {sum(c.startswith('landuse__') for c in context_feature_cols)}, "
          f"land cover: {sum(c.startswith('landcover__') for c in context_feature_cols)}, "
          f"emissions: {sum(c.startswith('emissions__') for c in context_feature_cols)})")
 
 
if __name__ == "__main__":
    main()