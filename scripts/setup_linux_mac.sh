#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'
python -m retailmind.bootstrap --rows 5000
printf '\nLaunch in two terminals:\nuvicorn retailmind.api:app --reload\ncd frontend && npm install && npm run dev\n'
