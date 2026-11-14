.PHONY: install demo api ui test deep spark index
install:
	python -m pip install -e '.[dev]'
demo:
	python -m retailmind.bootstrap --rows 5000
api:
	python -m uvicorn retailmind.api:app --reload --port 8000
ui:
	cd frontend && npm run dev
test:
	python -m pytest -q
deep:
	python -m retailmind.train --torch
spark:
	python -m retailmind.spark_etl
index:
	python -m retailmind.cli index
