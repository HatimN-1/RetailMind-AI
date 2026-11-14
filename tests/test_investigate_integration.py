"""FastAPI integration: real agent/SQL, controlled optional service failures."""
import logging
from contextlib import closing
import sqlite3
from uuid import UUID
import pytest
from fastapi.testclient import TestClient
from retailmind import api, retrieval


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv('RETAILMIND_RETRIEVAL', 'local')
    monkeypatch.setenv('RETAILMIND_OLLAMA_MODEL', '')
    return TestClient(api.app)


@pytest.mark.parametrize('graph', [False, True])
def test_post_investigate_preserves_actual_transaction_and_frontend_contract(client, graph):
    if graph:
        pytest.importorskip('langgraph')
    existing = client.get('/transactions?limit=1').json()[0]['transaction_id']
    response = client.post('/investigate', json={'question': f'Analyse {existing}', 'use_langgraph': graph})
    assert response.status_code == 200
    data = response.json()
    assert data['evidence'][0]['transaction_id'] == existing
    assert data['sql_proofs'][0]['rows'] == data['evidence']
    assert data['sql_proofs'][0]['parameters'] == [existing]
    assert data['answer'] and data['observations']
    assert len(data['steps']) == 9
    assert data['workflow_backend'] == ('langgraph' if graph else 'sequential')
    assert not data['ollama_used'] and not data['ollama_attempted']
    UUID(data['correlation_id'])


def test_airflow_documentary_api_without_ollama(client):
    data = client.post('/investigate', json={'question': 'Que vérifier après un échec Airflow ?'}).json()
    assert data['intent'] == 'pipeline' and data['evidence'] == []
    assert any('airflow' in s['source'] and s['score'] > 0 and s['chunk_id'] for s in data['sources'])
    assert data['recommendations'] and not data['ollama_used']


def test_real_local_lock_produces_actionable_fallback_and_releases_after_request(client, monkeypatch, tmp_path):
    qdrant = pytest.importorskip('qdrant_client')
    path = tmp_path / 'qdrant'
    monkeypatch.setenv('RETAILMIND_RETRIEVAL', 'qdrant')
    monkeypatch.setenv('QDRANT_PATH', str(path))
    monkeypatch.delenv('QDRANT_URL', raising=False)
    with closing(qdrant.QdrantClient(path=str(path))):
        response = client.post('/investigate', json={'question': 'Airflow task logs'})
        data = response.json()
        status = client.get('/rag/status').json()
    assert response.status_code == 200
    assert data['retrieval_backend'] == 'tfidf'
    assert 'verrouill' in data['warnings'][0]
    diagnostic = data['retrieval_diagnostics'][0]
    assert diagnostic['code'] == status['diagnostic']['code'] == 'qdrant_locked'
    assert diagnostic['error_type'] == 'RuntimeError'
    assert diagnostic['correlation_id'] == data['correlation_id']
    assert data['sources'] and data['answer']
    # The failed open did not delete metadata or retain the external lock.
    with closing(qdrant.QdrantClient(path=str(path))):
        pass


def test_embedding_cache_failure_keeps_sql_and_names_actual_error(client, monkeypatch):
    monkeypatch.setenv('RETAILMIND_RETRIEVAL', 'qdrant')

    def unavailable(*args, **kwargs):
        raise OSError('private path and token must never be echoed')

    monkeypatch.setattr(retrieval, 'search_qdrant', unavailable)
    data = client.post('/investigate', json={'question': 'Analyse TX-0000001'}).json()
    assert data['evidence'] and data['sql_proofs']
    assert data['retrieval_backend'] == 'tfidf'
    assert data['retrieval_diagnostics'][0]['error_type'] == 'OSError'
    assert 'cache' in data['warnings'][0] and 'private path' not in str(data)


@pytest.mark.parametrize('exception,status,code', [
    (ValueError, 422, 'investigation_configuration_invalid'),
    (TimeoutError, 504, 'investigation_timeout'),
    (sqlite3.OperationalError, 503, 'warehouse_unavailable'),
    (ImportError, 400, 'investigation_dependency_missing'),
    (RuntimeError, 500, 'investigation_failed'),
])
def test_api_exceptions_have_correlated_server_trace_and_safe_json(client, monkeypatch, caplog,
                                                                 exception, status, code):
    marker = 'sensitive-exception-value-do-not-log'

    def broken(*args, **kwargs):
        raise exception(marker)

    monkeypatch.setattr(api, 'investigate', broken)
    with caplog.at_level(logging.ERROR, logger='retailmind.api'):
        response = client.post('/investigate', json={'question': 'Airflow task logs'})
    data = response.json()
    assert response.status_code == status
    assert data['code'] == code and data['error_type'] == exception.__name__
    assert data['correlation_id'] == response.headers['X-Correlation-ID']
    UUID(data['correlation_id'])
    assert data['correlation_id'] in caplog.text and 'broken' in caplog.text
    assert marker not in str(data) and marker not in caplog.text
    assert 'Airflow task logs' not in caplog.text


def test_pydantic_errors_remain_standard_422(client):
    response = client.post('/investigate', json={'question': '  ', 'use_langgraph': True})
    assert response.status_code == 422
    assert response.json()['detail'][0]['loc'] == ['body', 'question']
    assert client.post('/investigate', json={'question': 'Airflow', 'use_langgraph': 'true'}).status_code == 422
