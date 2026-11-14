"""Filesystem locations. Override RETAILMIND_HOME for separate test runs."""
from __future__ import annotations
import os
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(os.getenv("RETAILMIND_HOME", Path(__file__).resolve().parents[2])).resolve()
# Process variables take precedence. No secrets are printed or exported to React.
load_dotenv(ROOT / ".env", override=False)
DATA = ROOT / "data"
RAW = DATA / "raw"
CURATED = DATA / "curated"
MARTS = DATA / "marts"
MODELS = DATA / "models"
REPORTS = DATA / "reports"
DB = MARTS / "retailmind.sqlite"


def ensure_dirs() -> None:
    for folder in (RAW, CURATED, MARTS, MODELS, REPORTS):
        folder.mkdir(parents=True, exist_ok=True)
