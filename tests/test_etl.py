import pandas as pd
from retailmind.generate import generate
from retailmind.etl import run


def test_deduplicates_and_checks(tmp_path, monkeypatch):
    from retailmind import etl
    monkeypatch.setattr(etl, "REPORTS", tmp_path)
    raw = tmp_path / "raw.csv"
    clean = tmp_path / "clean.csv"
    generate(200, 42, raw)
    result = run(raw, clean)
    df = pd.read_csv(clean)
    assert len(df) == 200
    assert result["dropped_rows"] == 1
    assert df.transaction_id.is_unique
    assert df.total_amount.ge(0).all()
