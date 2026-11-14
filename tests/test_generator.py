import pandas as pd
from retailmind.generate import generate


def test_seed_deterministic(tmp_path):
    a = tmp_path / "a.csv"
    b = tmp_path / "b.csv"
    x = generate(rows=200, seed=42, output=a)
    y = generate(rows=200, seed=42, output=b)
    assert a.read_bytes() == b.read_bytes()
    assert x["source_rows"] == 201
    assert y["injected_duplicates"] == 1


def test_synthetic_anomaly_labels(tmp_path):
    file = tmp_path / "in.csv"
    generate(rows=500, seed=42, output=file)
    frame = pd.read_csv(file).drop_duplicates("transaction_id")
    assert len(frame) == 500
    assert 0 < int(frame.is_anomaly.sum()) < 100
    assert set(frame.anomaly_type).issuperset({"normal"})
