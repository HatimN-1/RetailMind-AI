"""Offline unit tests: actual Qdrant local storage, deterministic embedding stub."""
import re
import numpy as np
import pytest
from retailmind import retrieval as r


class Tokenizer:
    def num_special_tokens_to_add(self, pair=False):
        return 2

    def __call__(self, text, **kwargs):
        return {'offset_mapping': [m.span() for m in re.finditer(r'\S+', text)]}


class Embeddings:
    tokenizer = Tokenizer()
    max_seq_length = 128

    def get_sentence_embedding_dimension(self):
        return 4

    def encode(self, texts, **kwargs):
        return np.array([[1 + t.lower().count('airflow'), 1 + t.lower().count('spark'),
                          1 + t.lower().count('quality'), 1] for t in texts], dtype=float)


@pytest.fixture
def rag(tmp_path, monkeypatch):
    pytest.importorskip('qdrant_client')
    docs = tmp_path / 'docs'
    docs.mkdir()
    (docs / 'airflow.md').write_text('# Airflow\nInspect Airflow task logs before retry.', encoding='utf-8')
    (docs / 'spark.md').write_text('# Spark\nInspect Spark schema and failed casts.', encoding='utf-8')
    monkeypatch.setattr(r, 'DOCS_DIR', docs)
    monkeypatch.setattr(r, '_embeddings_model', lambda **kw: Embeddings())
    monkeypatch.setenv('QDRANT_PATH', str(tmp_path / 'index'))
    monkeypatch.delenv('QDRANT_URL', raising=False)
    return docs


def test_token_chunks_offsets_overlap_and_stable_ids(monkeypatch):
    monkeypatch.setenv('RAG_CHUNK_TOKENS', '16')
    monkeypatch.setenv('RAG_CHUNK_OVERLAP', '3')
    document = {'source': 'docs/runbooks/a.md', 'text': ' '.join(f'word{i}' for i in range(60))}
    pieces = r.chunks([document], Embeddings())
    assert len(pieces) > 1
    assert pieces == r.chunks([document], Embeddings())
    assert pieces[1]['start_char'] < pieces[0]['end_char']
    for p in pieces:
        assert p['text'] == document['text'][p['start_char']:p['end_char']]
        assert len(p['text'].split()) <= 16


def test_index_reindex_search_and_stale_detection(rag):
    first = r.index_qdrant()
    assert first['dimension'] == 4
    assert r.index_qdrant()['status'] == 'unchanged'
    assert r.index_status()['chunks'] == first['chunks']
    assert r.search_qdrant('Airflow Airflow', 1)[0]['source'].endswith('airflow.md')
    (rag / 'spark.md').unlink()
    with pytest.raises(ValueError, match='stale'):
        r.search_qdrant('Spark')
    assert r.index_qdrant()['chunks'] == 1
    assert all(p['source'].endswith('airflow.md') for p in r.search_qdrant('Spark'))


def test_failed_index_keeps_active_alias(rag, monkeypatch):
    r.index_qdrant()
    (rag / 'spark.md').write_text('New Spark documentation.', encoding='utf-8')
    from qdrant_client import QdrantClient
    original = QdrantClient.upsert

    def fail(*args, **kwargs):
        raise RuntimeError('simulated upload failure')

    monkeypatch.setattr(QdrantClient, 'upsert', fail)
    with pytest.raises(RuntimeError):
        r.index_qdrant()
    with r._client() as client:
        assert client.count(r.COLLECTION, exact=True).count == 2
    monkeypatch.setattr(QdrantClient, 'upsert', original)
    assert r.index_qdrant()['status'] == 'indexed'


def test_timeout_after_alias_swap_keeps_new_collection(rag, monkeypatch):
    r.index_qdrant()
    (rag / 'spark.md').write_text('Updated Spark schema checks.', encoding='utf-8')
    from qdrant_client import QdrantClient
    original = QdrantClient.update_collection_aliases

    def swap_then_timeout(self, **kwargs):
        original(self, **kwargs)
        raise TimeoutError('response lost after committed swap')

    monkeypatch.setattr(QdrantClient, 'update_collection_aliases', swap_then_timeout)
    with pytest.raises(TimeoutError):
        r.index_qdrant()
    assert r.index_status()['index_ready']
    assert r.search_qdrant('Spark schema')[0]['text'] == 'Updated Spark schema checks.'


def test_cli_index_error_is_sanitized(monkeypatch, capsys):
    from retailmind import cli
    monkeypatch.setattr('sys.argv', ['retailmind', 'index'])
    monkeypatch.setattr(r, 'index_qdrant', lambda: (_ for _ in ()).throw(RuntimeError('private-url-or-secret')))
    with pytest.raises(SystemExit) as error:
        cli.main()
    assert error.value.code == 1
    stderr = capsys.readouterr().err
    assert 'index_failed' in stderr and 'private-url-or-secret' not in stderr


def test_empty_corpus_does_not_load_model(rag, monkeypatch):
    for p in rag.glob('*.md'):
        p.unlink()
    monkeypatch.setattr(r, '_embeddings_model', lambda **kw: pytest.fail('must not load'))
    assert r.index_qdrant()['status'] == 'empty_corpus'
    assert r.search_local('airflow') == r.search_qdrant('airflow') == []


def test_unavailable_qdrant_explicit_fallback(monkeypatch):
    monkeypatch.setenv('RETAILMIND_RETRIEVAL', 'qdrant')
    monkeypatch.setattr(r, '_qdrant_client', lambda: (_ for _ in ()).throw(ConnectionError()))
    result = r.retrieve('Airflow task logs')
    assert result['backend'] == 'tfidf' and result['warnings']
    assert result['sources'] and all(x['backend'] == 'tfidf' for x in result['sources'])


def test_investigation_cannot_create_a_local_index(tmp_path, monkeypatch):
    missing = tmp_path / 'must_not_be_created'
    monkeypatch.setenv('QDRANT_PATH', str(missing))
    monkeypatch.delenv('QDRANT_URL', raising=False)
    monkeypatch.setenv('RETAILMIND_RETRIEVAL', 'qdrant')
    assert r.retrieve('Airflow')['backend'] == 'tfidf'
    assert r.index_status()['status'] == 'not_indexed'
    assert not missing.exists()


def test_bad_configuration_and_dimensions(monkeypatch):
    monkeypatch.setenv('RAG_CHUNK_OVERLAP', '96')
    with pytest.raises(ValueError):
        r.chunks([])
    monkeypatch.delenv('RAG_CHUNK_OVERLAP')
    bad = Embeddings()
    bad.get_sentence_embedding_dimension = lambda: 7
    with pytest.raises(ValueError, match='dimensions'):
        r._vectors(bad, ['hello'])


@pytest.mark.integration
def test_real_multilingual_embeddings():
    import os
    if os.getenv('RETAILMIND_INTEGRATION') != '1':
        pytest.skip('Opt-in: requires indexed corpus and cached real model')
    results = r.search_qdrant('Que vérifier après un échec du DAG Airflow ?', 3)
    assert results and any('airflow' in item['source'] for item in results)
    dbt = r.search_qdrant('Quelles vérifications effectuer après un test dbt échoué ?', 3)
    assert dbt and all('05_data_quality' in item['source'] for item in dbt)
    model = r._embeddings_model()
    assert r._vectors(model, ['test']).shape == (1, 384)
