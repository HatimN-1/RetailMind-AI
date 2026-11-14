"""Sandbox generated outputs so tests never overwrite the packaged demo data."""
from __future__ import annotations
import os
import subprocess
import sys
from pathlib import Path
import pytest


@pytest.fixture(scope="session")
def sandbox(tmp_path_factory):
    path = tmp_path_factory.mktemp("retailmind_test")
    env = {**os.environ, "RETAILMIND_HOME": str(path)}
    subprocess.run([sys.executable, "-m", "retailmind.bootstrap", "--rows", "350", "--seed", "51"],
                   env=env, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return Path(path), env
