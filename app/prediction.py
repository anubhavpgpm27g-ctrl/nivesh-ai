import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, balanced_accuracy_score

def _features(df):
    close = df["Close"].astype(float)
    volume = df["Volume"].astype(float).replace(0, np.nan)
    returns = close.pct_change()
    features = pd.DataFrame(index=df.index)
    features["ret_1"] = returns
    features["ret_3"] = close.pct_change(3)
    features["ret_5"] = close.pct_change(5)
    features["volatility_10"] = returns.rolling(10).std()
    features["sma_gap_5"] = close / close.rolling(5).mean() - 1
    features["sma_gap_20"] = close / close.rolling(20).mean() - 1
    features["volume_ratio"] = volume / volume.rolling(20).mean()
    if "High" in df and "Low" in df:
        features["range_pct"] = (df["High"] - df["Low"]) / close
    return features.replace([np.inf, -np.inf], np.nan)

def make_prediction(df):
    """
    Experimental daily-bar classifier: probability the next daily close is higher
    than the current close. Not a price target or validated trading strategy.
    """
    if df is None or len(df) < 100:
        return {"ok": False, "message": "At least 100 daily candles are needed for this experimental model."}
    features = _features(df)
    close = df["Close"].astype(float)
    target = (close.shift(-1) > close).astype(int).rename("target")
    dataset = features.join(target).dropna()
    if len(dataset) < 80:
        return {"ok": False, "message": "Not enough clean observations to train the experimental model."}
    X = dataset.drop(columns=["target"])
    y = dataset["target"]
    split = int(len(dataset) * 0.8)
    if split < 50 or len(dataset) - split < 15:
        return {"ok": False, "message": "Not enough observations for chronological validation."}
    model = Pipeline([("scale", StandardScaler()), ("logreg", LogisticRegression(max_iter=1000, class_weight="balanced"))])
    model.fit(X.iloc[:split], y.iloc[:split])
    test_pred = model.predict(X.iloc[split:])
    bal_acc = balanced_accuracy_score(y.iloc[split:], test_pred)
    acc = accuracy_score(y.iloc[split:], test_pred)
    # Train a fresh model on all labelled rows before the final current row.
    latest_features = features.dropna().iloc[[-1]]
    model.fit(X, y)
    probability_up = float(model.predict_proba(latest_features)[0][list(model.classes_).index(1)])
    return {
        "ok": True,
        "probability_up": probability_up,
        "probability_down": 1 - probability_up,
        "test_accuracy": float(acc),
        "test_balanced_accuracy": float(bal_acc),
        "test_samples": int(len(y.iloc[split:])),
        "as_of": str(latest_features.index[-1]),
        "message": "Experimental logistic-regression estimate using daily historical data. Not a validated trading signal; probabilities may be poorly calibrated."
    }
