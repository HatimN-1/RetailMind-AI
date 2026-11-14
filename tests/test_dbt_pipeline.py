"""Optional integration: dbt builds its DuckDB marts from a Spark-shaped Parquet folder."""

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

from retailmind.etl import run as pandas_etl
from retailmind.generate import generate


@pytest.mark.integration
def test_dbt_build_from_parquet(tmp_path, monkeypatch):
    pytest.importorskip("duckdb")
    pytest.importorskip("pyarrow")
    pytest.importorskip("dbt")
    from retailmind import etl

    executable = Path(sys.executable).with_name("dbt.exe" if os.name == "nt" else "dbt")
    if not executable.is_file():
        pytest.skip("dbt CLI executable unavailable")
    source_root = Path(__file__).resolve().parents[1]
    shutil.copytree(source_root / "dbt", tmp_path / "dbt", ignore=shutil.ignore_patterns("target", "logs"))
    (tmp_path / "data" / "marts").mkdir(parents=True)
    raw = tmp_path / "raw.csv"
    clean = tmp_path / "clean.csv"
    parquet = tmp_path / "data" / "curated" / "spark_transactions.parquet"
    parquet.mkdir(parents=True)
    generate(rows=200, seed=42, output=raw)
    monkeypatch.setattr(etl, "REPORTS", tmp_path)
    pandas_etl(source=raw, target=clean)
    pd.read_csv(clean).to_parquet(parquet / "part-test.parquet", index=False)

    # Run a real dbt project in isolation; no production/local project marts are mutated.
    project = tmp_path / "dbt"
    completed = subprocess.run(
        [str(executable), "build", "--project-dir", ".", "--profiles-dir", "."],
        cwd=project, text=True, capture_output=True, timeout=180,
        check=False, env=os.environ.copy(),
    )
    assert completed.returncode == 0, completed.stdout[-3000:] + "\n" + completed.stderr[-3000:]
    checked = subprocess.run(
        [sys.executable, str(source_root / "scripts" / "verify_dbt.py"), "--root", str(tmp_path)],
        cwd=source_root, text=True, capture_output=True, timeout=30,
        check=False,
    )
    assert checked.returncode == 0, checked.stdout + "\n" + checked.stderr
    assert '"transactions": 200' in checked.stdout
