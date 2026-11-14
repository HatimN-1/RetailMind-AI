"""Offline anomaly detection: temporal holdout, Isolation Forest and optional PyTorch autoencoder.

The injected labels are ONLY used to evaluate the models, never as an input feature.
"""
from __future__ import annotations
import json
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.metrics import average_precision_score, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.preprocessing import StandardScaler
from retailmind.settings import CURATED, MODELS, REPORTS, ensure_dirs

NUMERIC = ["quantity", "unit_price", "discount_pct", "total_amount"]
CATEGORICAL = ["category", "region", "channel", "payment_status"]


def feature_frame(df: pd.DataFrame, columns: list[str] | None = None) -> pd.DataFrame:
    out = pd.get_dummies(df[NUMERIC + CATEGORICAL], columns=CATEGORICAL, dtype=float)
    if columns is not None:
        out = out.reindex(columns=columns, fill_value=0.0)
    return out.astype(float)


def evaluate(y: np.ndarray, score: np.ndarray, threshold: float) -> dict:
    predicted = (score >= threshold).astype(int)
    values = {"precision": float(precision_score(y, predicted, zero_division=0)),
              "recall": float(recall_score(y, predicted, zero_division=0)),
              "f1": float(f1_score(y, predicted, zero_division=0)),
              "anomalies_predicted": int(predicted.sum())}
    if len(np.unique(y)) > 1:
        values["average_precision"] = float(average_precision_score(y, score))
        values["roc_auc"] = float(roc_auc_score(y, score))
    else:
        values.update({"average_precision": None, "roc_auc": None})
    return values


def run(train_torch: bool = False, epochs: int = 12, seed: int = 42) -> dict:
    ensure_dirs()
    np.random.seed(seed)
    frame = pd.read_csv(CURATED / "transactions_clean.csv").sort_values("event_timestamp")
    cut = int(0.75 * len(frame))
    if cut < 30 or cut >= len(frame):
        raise ValueError("Need at least 50 curated transactions")
    train, test = frame.iloc[:cut].copy(), frame.iloc[cut:].copy()
    columns = feature_frame(train).columns.tolist()
    x_train = feature_frame(train, columns).to_numpy(dtype=np.float32)
    x_test = feature_frame(test, columns).to_numpy(dtype=np.float32)
    scaler = StandardScaler().fit(x_train)
    train_norm = scaler.transform(x_train)
    test_norm = scaler.transform(x_test)
    model = IsolationForest(n_estimators=140, contamination="auto", random_state=seed, n_jobs=-1)
    model.fit(train_norm)
    train_scores = -model.score_samples(train_norm)
    test_scores = -model.score_samples(test_norm)
    # Train-only quantile; no threshold tuning on the test labels.
    threshold = float(np.quantile(train_scores, 0.95))
    y_test = test["is_anomaly"].to_numpy(dtype=int)
    metrics = {"protocol": "time_ordered_train_75pct_test_25pct",
               "dataset": "synthetic_labeled_transactions", "train_rows": len(train), "test_rows": len(test),
               "training_labels_used": False, "test_labels_used_for_scoring_only": True,
               "isolation_forest": evaluate(y_test, test_scores, threshold),
               "isolation_forest_threshold": threshold}
    joblib.dump({"model": model, "scaler": scaler, "columns": columns, "threshold": threshold},
                MODELS / "isolation_forest.joblib")
    predictions = test[["transaction_id", "event_timestamp", "is_anomaly", "anomaly_type"]].copy()
    predictions["anomaly_score"] = test_scores
    predictions["predicted_anomaly"] = (test_scores >= threshold).astype(int)
    predictions.to_csv(REPORTS / "holdout_predictions.csv", index=False)
    if train_torch:
        metrics["autoencoder_pytorch"] = train_autoencoder(
            train_norm, test_norm, y_test, epochs=epochs, seed=seed)
    (REPORTS / "model_evaluation.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    return metrics


def train_autoencoder(train_x: np.ndarray, test_x: np.ndarray, y_test: np.ndarray,
                      epochs: int = 12, seed: int = 42) -> dict:
    try:
        import torch
        from torch import nn
    except ImportError as exc:
        raise RuntimeError("PyTorch not found: pip install -e '.[deep]'") from exc
    torch.manual_seed(seed)
    torch.set_num_threads(min(torch.get_num_threads(), 4))
    dimension = train_x.shape[1]
    model = nn.Sequential(nn.Linear(dimension, 24), nn.ReLU(), nn.Linear(24, 8),
                          nn.ReLU(), nn.Linear(8, 24), nn.ReLU(), nn.Linear(24, dimension))
    optimizer = torch.optim.Adam(model.parameters(), lr=0.002)
    x = torch.from_numpy(train_x.astype(np.float32))
    model.train()
    for _ in range(epochs):
        for batch in torch.split(x[torch.randperm(len(x))], 256):
            optimizer.zero_grad()
            loss = ((model(batch)-batch)**2).mean()
            loss.backward()
            optimizer.step()
    model.eval()
    with torch.no_grad():
        train_scores = ((model(x)-x)**2).mean(dim=1).numpy()
        test_tensor = torch.from_numpy(test_x.astype(np.float32))
        test_scores = ((model(test_tensor)-test_tensor)**2).mean(dim=1).numpy()
    threshold = float(np.quantile(train_scores, 0.95))
    torch.save({"state_dict": model.state_dict(), "input_dim": dimension,
                "threshold": threshold}, MODELS / "autoencoder.pt")
    return {**evaluate(y_test, test_scores, threshold), "epochs": epochs,
            "threshold": threshold, "architecture": "MLP_autoencoder_24_8_24",
            "note": "Reconstruction error; labels used only for holdout evaluation."}


def predict(rows: list[dict]) -> list[dict]:
    path = MODELS / "isolation_forest.joblib"
    if not path.exists():
        raise FileNotFoundError("Model unavailable: run python -m retailmind.train")
    state = joblib.load(path)  # only load trusted locally produced artifacts
    frame = pd.DataFrame(rows)
    x = feature_frame(frame, state["columns"]).to_numpy(dtype=np.float32)
    scores = -state["model"].score_samples(state["scaler"].transform(x))
    return [{"score": float(s), "is_anomaly": bool(s >= state["threshold"]),
             "threshold": float(state["threshold"])} for s in scores]


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--torch", action="store_true", help="Train additional PyTorch autoencoder")
    parser.add_argument("--epochs", type=int, default=12)
    args = parser.parse_args()
    print(json.dumps(run(train_torch=args.torch, epochs=args.epochs), indent=2))

if __name__ == "__main__":
    main()
