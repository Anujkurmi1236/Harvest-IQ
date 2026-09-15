"""
Train the final price-growth model on ALL available data (not just the
train split used for evaluation) - this is the model predict.py actually
serves. Evaluation numbers already came from train_price_model.py; this
script exists purely to produce the deployable artifact.
"""

import os
import numpy as np
import xgboost as xgb
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
OUT_DIR = BASE_DIR / "output"


def main():
    X = np.load(os.path.join(OUT_DIR, "X.npy"))
    y = np.load(os.path.join(OUT_DIR, "y.npy"))

    model = xgb.XGBRegressor(
        n_estimators=400, learning_rate=0.03, max_depth=4,
        subsample=0.8, colsample_bytree=0.7, reg_lambda=3.0,
        objective="reg:squarederror", random_state=42,
    )
    model.fit(X, y)
    model.save_model(os.path.join(OUT_DIR, "price_growth_model_final.json"))
    print(f"Trained final model on {X.shape[0]} rows, saved to "
          f"{OUT_DIR}/price_growth_model_final.json")


if __name__ == "__main__":
    main()