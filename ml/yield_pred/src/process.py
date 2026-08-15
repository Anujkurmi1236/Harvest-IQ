import pandas as pd
import numpy as np
import os
from pathlib import Path


def process_fertilizer_product_data():
    """
    Process Fertilizer Product data: predict 'Import value' using Year, Import quantity, and Data Reliability.
    FIXED: Reliability is now computed per (Year, Area, Item) combination, not just Year.
    """
    df = pd.read_csv("ml/yield_pred/data/processed/req_data/india_Inputs_FertilizersProduct_E_All_Data_(Normalized).csv")

    df_wide = df.pivot_table(
        index=["Year", "Area", "Item"],
        columns="Element",
        values="Value",
        aggfunc="first"  # In case of duplicates, take the first value
    ).reset_index()

    # Flatten column names if they become multi-index
    df_wide.columns.name = None
    
    # Create Data_Reliability feature: 1 = Official ('A'), 0 = Estimated/Mirrored ('X')
    # Map flags from original data to wide format by (Year, Area, Item)
    flag_map = df.groupby(['Year', 'Area', 'Item'])['Flag'].apply(
        lambda x: 1 if (x == 'A').any() else 0
    ).reset_index()
    flag_map.columns = ['Year', 'Area', 'Item', 'Data_Reliability']
    
    df_wide = df_wide.merge(flag_map, on=['Year', 'Area', 'Item'], how='left')
    df_wide = df_wide.fillna(0)

    # Define X and y
    feature_cols = ['Year', 'Import quantity', 'Data_Reliability']
    target_col = 'Import value'
    
    # Validate required columns exist
    missing_cols = [col for col in feature_cols + [target_col] if col not in df_wide.columns]
    if missing_cols:
        raise ValueError(f"Missing columns after pivot: {missing_cols}")

    X = df_wide[feature_cols].to_numpy(dtype=np.float32)
    y = df_wide[target_col].to_numpy(dtype=np.float32)

    # Ensure output directory exists
    os.makedirs('ml/yield_pred/data/features', exist_ok=True)
    
    # Save
    np.save('ml/yield_pred/data/features/india_input_fertilizer_product_features.npy', X)
    np.save('ml/yield_pred/data/features/india_input_fertilizer_product_target.npy', y)

    print(f"Fertilizer Product - Shape: {X.shape}")
    print(f"Fertilizer Product - Features: {feature_cols}")


def process_fertilizer_nutrient_data():
    """
    Process Fertilizer Nutrient data: predict based on available elements.
    """
    df = pd.read_csv("ml/yield_pred/data/processed/req_data/india_Inputs_FertilizersNutrient_E_All_Data_(Normalized).csv")

    df_wide = df.pivot_table(
        index=["Year", "Area", "Item"],
        columns="Element",
        values="Value",
        aggfunc="first"
    ).reset_index()
    df_wide.columns.name = None
    
    # Create Data_Reliability feature
    flag_map = df.groupby(['Year', 'Area', 'Item'])['Flag'].apply(
        lambda x: 1 if (x == 'A').any() else 0
    ).reset_index()
    flag_map.columns = ['Year', 'Area', 'Item', 'Data_Reliability']
    
    df_wide = df_wide.merge(flag_map, on=['Year', 'Area', 'Item'], how='left')
    df_wide = df_wide.fillna(0)

    # Use available Import columns if they exist
    feature_cols = ['Year', 'Data_Reliability']
    target_col = None
    
    # Check for Import value or similar target
    available_cols = df_wide.columns.tolist()
    if 'Import value' in available_cols:
        target_col = 'Import value'
        if 'Import quantity' in available_cols:
            feature_cols.insert(1, 'Import quantity')
    
    if target_col is None:
        print("Warning: No 'Import value' column found. Skipping fertilizer nutrient processing.")
        return
    
    os.makedirs('ml/yield_pred/data/features', exist_ok=True)
    
    X = df_wide[feature_cols].to_numpy(dtype=np.float32)
    y = df_wide[target_col].to_numpy(dtype=np.float32)

    np.save('ml/yield_pred/data/features/india_input_fertilizer_nutrient_features.npy', X)
    np.save('ml/yield_pred/data/features/india_input_fertilizer_nutrient_target.npy', y)

    print(f"Fertilizer Nutrient - Shape: {X.shape}")
    print(f"Fertilizer Nutrient - Features: {feature_cols}")


def process_production_crops_data():
    """
    Process Production Crops & Livestock data.
    """
    df = pd.read_csv("ml/yield_pred/data/processed/req_data/india_Production_Crops_Livestock_E_All_Data_(Normalized).csv")

    df_wide = df.pivot_table(
        index=["Year", "Area", "Item"],
        columns="Element",
        values="Value",
        aggfunc="first"
    ).reset_index()
    df_wide.columns.name = None
    
    # Create Data_Reliability feature
    flag_map = df.groupby(['Year', 'Area', 'Item'])['Flag'].apply(
        lambda x: 1 if (x == 'A').any() else 0
    ).reset_index()
    flag_map.columns = ['Year', 'Area', 'Item', 'Data_Reliability']
    
    df_wide = df_wide.merge(flag_map, on=['Year', 'Area', 'Item'], how='left')
    df_wide = df_wide.fillna(0)

    os.makedirs('ml/yield_pred/data/features', exist_ok=True)
    
    # Production is typically the target; use other available metrics as features
    feature_cols = ['Year', 'Data_Reliability']
    target_col = None
    
    available_cols = df_wide.columns.tolist()
    if 'Production' in available_cols:
        target_col = 'Production'
    
    if target_col is None:
        print("Warning: No 'Production' column found. Skipping production crops processing.")
        return
    
    X = df_wide[feature_cols].to_numpy(dtype=np.float32)
    y = df_wide[target_col].to_numpy(dtype=np.float32)

    np.save('ml/yield_pred/data/features/india_production_crops_features.npy', X)
    np.save('ml/yield_pred/data/features/india_production_crops_target.npy', y)

    print(f"Production Crops - Shape: {X.shape}")
    print(f"Production Crops - Features: {feature_cols}")


def process_environment_data():
    """
    Process Environment (Temperature & Soil Nutrient) data.
    Handles datasets with 'Months' instead of 'Item'.
    """
    datasets = [
        ("Temperature", "india_Environment_Temperature_change_E_All_Data_(Normalized).csv"),
        ("Soil_Nutrient", "india_Environment_Soil_nutrient_budget_E_All_Data_(Normalized).csv")
    ]
    
    os.makedirs('ml/yield_pred/data/features', exist_ok=True)
    
    for name, filename in datasets:
        filepath = f"ml/yield_pred/data/processed/req_data/{filename}"
        
        if not os.path.exists(filepath):
            print(f"Warning: File not found {filepath}")
            continue
        
        df = pd.read_csv(filepath)
        
        # Environment data uses 'Months' instead of 'Item'
        # Determine the grouping key dynamically
        groupby_key = None
        if 'Item' in df.columns:
            groupby_key = 'Item'
        elif 'Months' in df.columns:
            groupby_key = 'Months'
        else:
            print(f"Warning: No 'Item' or 'Months' column found in {name} data.")
            continue
        
        df_wide = df.pivot_table(
            index=["Year", "Area", groupby_key],
            columns="Element",
            values="Value",
            aggfunc="first"
        ).reset_index()
        df_wide.columns.name = None
        
        # Create Data_Reliability feature
        flag_map = df.groupby(['Year', 'Area', groupby_key])['Flag'].apply(
            lambda x: 1 if (x == 'A').any() else 0
        ).reset_index()
        flag_map.columns = ['Year', 'Area', groupby_key, 'Data_Reliability']
        
        df_wide = df_wide.merge(flag_map, on=['Year', 'Area', groupby_key], how='left')
        df_wide = df_wide.fillna(0)
        
        # Use Year and Reliability as baseline features
        feature_cols = ['Year', 'Data_Reliability']
        
        # Include first available numeric column as target
        available_cols = [c for c in df_wide.columns if c not in ['Year', 'Area', groupby_key, 'Data_Reliability']]
        if not available_cols:
            print(f"Warning: No numeric columns found in {name} data.")
            continue
        
        target_col = available_cols[0]
        
        X = df_wide[feature_cols].to_numpy(dtype=np.float32)
        y = df_wide[target_col].to_numpy(dtype=np.float32)
        
        np.save(f'ml/yield_pred/data/features/india_environment_{name}_features.npy', X)
        np.save(f'ml/yield_pred/data/features/india_environment_{name}_target.npy', y)
        
        print(f"Environment {name} - Shape: {X.shape}")
        print(f"Environment {name} - Target: {target_col}")


def process_all_data():
    """
    Process all available datasets and generate .npy files.
    """
    print("Starting data processing for all datasets...\n")
    
    process_fertilizer_product_data()
    print()
    
    process_fertilizer_nutrient_data()
    print()
    
    process_production_crops_data()
    print()
    
    process_environment_data()
    
    print("\n✓ All data processing completed!")