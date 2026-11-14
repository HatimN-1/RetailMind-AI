"""Start a disposable HTTP API and verify V2 routes plus real V3 investigation.
No bootstrap, writes to the warehouse, model training, or infrastructure mutation.
Run after indexing, while the regular API is stopped in Qdrant local mode.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request


def main():
    root = Path(__file__).resolve().parents[1]
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    env = {**os.environ, 'RETAILMIND_RETRIEVAL': 'qdrant', 'RETAILMIND_OLLAMA_MODEL': ''}
    process = subprocess.Popen([sys.executable, '-m', 'uvicorn', 'retailmind.api:app', '--host', '127.0.0.1',
                                '--port', str(port)], cwd=root, env=env,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    base = f'http://127.0.0.1:{port}'

    def request(path, body=None):
        payload = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(base + path, payload, {'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=65) as response:
            return json.load(response)

    try:
        for _ in range(150):
            if process.poll() is not None:
                raise RuntimeError('Disposable API exited before becoming healthy')
            try:
                request('/health')
                break
            except (urllib.error.URLError, TimeoutError):
                time.sleep(0.1)
        else:
            raise TimeoutError('API did not start within 15 seconds')
        routes = ['/health', '/ready', '/metrics', '/analytics', '/transactions', '/transactions-page',
                  '/alerts', '/alerts-page', '/quality', '/model-evaluation', '/rag/status',
                  '/investigation-status', '/rag/documents/04_airflow_retry.md']
        results = {route: bool(request(route)) for route in routes}
        investigation = request('/investigate', {'question': 'Analyse la transaction TX-0003699', 'use_langgraph': True})
        assert investigation['workflow_backend'] == 'langgraph'
        assert investigation['retrieval_backend'] == 'qdrant'
        assert investigation['evidence'][0]['transaction_id'] == 'TX-0003699'
        assert not investigation['ollama_attempted']
        pipeline = request('/investigate', {'question': 'Que vérifier après un échec Airflow ?', 'use_langgraph': True})
        assert any('airflow' in source['source'] for source in pipeline['sources'])
        prediction = request('/predict', {'quantity': 2, 'unit_price': 100, 'discount_pct': 0,
            'total_amount': 200, 'category': 'Books', 'region': 'Fes', 'channel': 'web', 'payment_status': 'paid'})
        report = {'http_routes_ok': results, 'predict_ok': bool(prediction), 'mode': investigation['mode'],
                  'steps': investigation['steps'], 'correlation_id': investigation['correlation_id'],
                  'latency_ms': investigation['latency_ms'], 'transaction_id_preserved': True,
                  'ollama_disabled': True, 'sources_returned': len(pipeline['sources']),
                  'pipeline_sources': [source['source'] for source in pipeline['sources']]}
        output = root / 'docs' / 'evaluation' / 'api_smoke_v3.json'
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
        print(json.dumps(report, indent=2))
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


if __name__ == '__main__':
    main()
