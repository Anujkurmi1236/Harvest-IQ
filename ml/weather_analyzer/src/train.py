import os
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
 
OUT_DIR = "ml/weather_analyzer/output"
MIN_TRAIN_YEARS = 20 
 
def load_data():
    X = np.load(os.path.join(OUT_DIR, "X.npy"))
    y = np.load(os.path.join(OUT_DIR, "y.npy"))
    years = np.load(os.path.join(OUT_DIR, "years.npy"))
    with open(os.path.join(OUT_DIR, "feature_names.txt")) as f:
        feature_names = f.read().splitlines()
    return X, y, years, feature_names
 
 
def make_model():
    return xgb.XGBRegressor(
        n_estimators=150,
        learning_rate=0.05,
        max_depth=3,
        subsample=0.8,
        colsample_bytree=0.5,
        reg_lambda=5.0,
        objective="reg:squarederror",
        random_state=42,
    )
 
 
def walk_forward_cv(X, y, years):
    order = np.argsort(years)
    X, y, years = X[order], y[order], years[order]
 
    preds, actuals, pred_years = [], [], []
    for i in range(len(years)):
        if years[i] - years[0] < MIN_TRAIN_YEARS:
            continue
        train_mask = years < years[i]
        if train_mask.sum() < MIN_TRAIN_YEARS:
            continue
 
        model = make_model()
        model.fit(X[train_mask], y[train_mask])
        pred = model.predict(X[i:i + 1])[0]
 
        preds.append(pred)
        actuals.append(y[i])
        pred_years.append(years[i])
 
    return np.array(pred_years), np.array(actuals), np.array(preds)
 
 
def main():
    X, y, years, feature_names = load_data()
    print(f"Dataset: {X.shape[0]} rows, {X.shape[1]} features "
          f"(years {int(years.min())}-{int(years.max())})")
    print(f"Feature-to-row ratio: {X.shape[1] / X.shape[0]:.1f} features per row - "
          f"high overfitting risk, hence walk-forward CV + heavy regularization below.\n")
 
    pred_years, actuals, preds = walk_forward_cv(X, y, years)
 
    rmse = np.sqrt(mean_squared_error(actuals, preds))
    mae = mean_absolute_error(actuals, preds)
    r2 = r2_score(actuals, preds)
 
    print(f"=== Walk-forward CV performance ({len(pred_years)} test years, "
          f"{int(pred_years.min())}-{int(pred_years.max())}) ===")
    print(f"RMSE: {rmse:.3f} °C")
    print(f"MAE:  {mae:.3f} °C")
    print(f"R2:   {r2:.3f}")
 
    naive_preds = []
    order = np.argsort(years)
    y_sorted, years_sorted = y[order], years[order]
    for py in pred_years:
        hist = y_sorted[years_sorted < py]
        naive_preds.append(hist[-5:].mean() if len(hist) >= 5 else hist.mean())
    naive_preds = np.array(naive_preds)
    naive_rmse = np.sqrt(mean_squared_error(actuals, naive_preds))
    print(f"\nNaive baseline (5-year rolling mean) RMSE: {naive_rmse:.3f} °C "
          f"{'- model beats naive' if rmse < naive_rmse else '- model does NOT beat the naive baseline, use with caution'}")
 
    # final model trained on all available data, for deployment via predict.py
    final_model = make_model()
    final_model.fit(X, y)
    final_model.save_model(os.path.join(OUT_DIR, "weather_model.json"))
 
    importances = pd.Series(final_model.feature_importances_, index=feature_names)
    top_features = importances.sort_values(ascending=False).head(15)
    print("\n=== Top 15 features (final model, trained on all data) ===")
    for name, score in top_features.items():
        print(f"{score:.4f}  {name}")
 
    pd.DataFrame({"year": pred_years, "actual": actuals, "predicted": preds}).to_csv(
        os.path.join(OUT_DIR, "walk_forward_predictions.csv"), index=False
    )
    top_features.to_csv(os.path.join(OUT_DIR, "top_feature_importances.csv"))
    print(f"\nSaved final model to {OUT_DIR}/weather_model.json")
 
 
if __name__ == "__main__":
    main()