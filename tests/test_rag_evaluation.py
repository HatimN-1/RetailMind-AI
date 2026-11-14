import json
from retailmind import rag_evaluation, retrieval


def test_evaluation_reproducible_cases_and_real_counts(monkeypatch):
    monkeypatch.setenv('RETAILMIND_RETRIEVAL', 'local')
    monkeypatch.delenv('RETAILMIND_OLLAMA_MODEL', raising=False)
    result = rag_evaluation.evaluate('tfidf')
    assert result['queries'] >= 15
    assert len(result['results']) == result['queries'] == result['successful_queries']
    assert 0 <= result['recall_at_3'] <= result['recall_at_5'] <= 1
    assert result['unauthorized_requests_refused'] == result['security_probes']
    assert all(item['preserved'] for item in result['transaction_identifiers'])
    assert result['controlled_sql_provenance_valid']
    expected = {s for row in result['results'] for s in row['expected_sources']}
    assert expected == {d['source'].split('/')[-1] for d in retrieval.corpus()}


def test_vector_evaluation_never_substitutes_tfidf(tmp_path, monkeypatch):
    monkeypatch.setenv('RETAILMIND_RETRIEVAL', 'local')
    monkeypatch.delenv('RETAILMIND_OLLAMA_MODEL', raising=False)
    path = tmp_path / 'questions.json'
    path.write_text(json.dumps([{'question': 'Airflow', 'expected_sources': ['04_airflow_retry.md']}]))
    monkeypatch.setattr(retrieval, 'search_qdrant', lambda *a: (_ for _ in ()).throw(ConnectionError()))
    result = rag_evaluation.evaluate('qdrant', path)
    assert result['successful_queries'] == 0
    assert result['retrieval_errors'] == 1
    assert result['recall_at_3'] == result['recall_at_5'] == 0
    assert result['warmup_error'] == 'ConnectionError'
