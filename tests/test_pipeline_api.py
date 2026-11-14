import json
import subprocess
import sys


def _run(env, code):
    return subprocess.run([sys.executable, "-c", code], env=env, check=True,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True).stdout


def test_warehouse_and_ml(sandbox):
    path, env = sandbox
    metrics = json.loads((path / "data/reports/model_evaluation.json").read_text())
    assert metrics["train_rows"] > metrics["test_rows"]
    assert 0 <= metrics["isolation_forest"]["precision"] <= 1
    assert metrics["training_labels_used"] is False
    assert (path / "data/models/isolation_forest.joblib").exists()
    assert (path / "data/marts/retailmind.sqlite").exists()


def test_fastapi_endpoints(sandbox):
    _, env = sandbox
    code = '''
from fastapi.testclient import TestClient
from retailmind.api import app
c=TestClient(app)
assert c.get('/health').json()['warehouse_ready']
assert c.get('/metrics').json()['summary']['orders']==350
assert len(c.get('/alerts?limit=5').json())<=5
assert len(c.get('/transactions?limit=9').json())==9
assert c.get('/quality').status_code==200
assert c.post('/investigate',json={'question':'TX-0000001'}).status_code==200
assert c.post('/predict',json={'quantity':2,'unit_price':100,'discount_pct':0,'total_amount':200,'category':'Books','region':'Fes','channel':'web','payment_status':'paid'}).status_code==200
print('ok')
'''
    assert _run(env, code).strip() == "ok"


def test_readonly_guard(sandbox):
    _, env = sandbox
    code = "from retailmind.warehouse import execute_readonly\ntry: execute_readonly('DELETE FROM transactions')\nexcept ValueError: print('blocked')"
    assert _run(env, code).strip() == "blocked"
