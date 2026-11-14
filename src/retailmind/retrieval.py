"""Bounded runbook retrieval. Only the local CLI writes the vector index."""
from __future__ import annotations
from contextlib import contextmanager
from functools import lru_cache
import hashlib
import json
import logging
import os
from pathlib import Path
import re
import threading
import uuid
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from retailmind.settings import ROOT
from retailmind.diagnostics import log_failure

DOCS_DIR = ROOT / 'docs' / 'runbooks'
COLLECTION = 'retailmind_runbooks_v3'
DEFAULT_MODEL = 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'
DEFAULT_REVISION = 'e8f8c211226b894fcb81acc59f3b34ba3efd5f42'
_LOCK = threading.RLock()
logger = logging.getLogger(__name__)


def corpus() -> list[dict]:
    """Allow only Markdown beneath the dedicated directory; reject linked files."""
    documents = []
    total_bytes = 0
    for path in sorted(DOCS_DIR.rglob('*.md')):
        if path.is_symlink() or DOCS_DIR.resolve() not in path.resolve().parents:
            continue
        total_bytes += path.stat().st_size
        if path.stat().st_size > 1_000_000 or total_bytes > 4_000_000 or len(documents) >= 200:
            raise ValueError('Corpus exceeds the document/size budget')
        content = path.read_text(encoding='utf-8')
        if content.strip():
            documents.append({'source': 'docs/runbooks/' + path.relative_to(DOCS_DIR).as_posix(),
                              'title': path.stem.replace('_', ' '), 'text': content})
    return documents


def _config() -> dict:
    size, overlap = int(os.getenv('RAG_CHUNK_TOKENS', '96')), int(os.getenv('RAG_CHUNK_OVERLAP', '16'))
    if not 16 <= size <= 512 or not 0 <= overlap < size // 2:
        raise ValueError('Invalid RAG chunk size/overlap')
    model = os.getenv('EMBEDDING_MODEL', DEFAULT_MODEL)
    return {'model': model,
            'revision': os.getenv('EMBEDDING_REVISION') or (DEFAULT_REVISION if model == DEFAULT_MODEL else None),
            'chunk_tokens': size, 'overlap': overlap, 'schema': 3}


def chunks(documents: list[dict], model=None) -> list[dict]:
    """Actual tokenizer windows for dense mode, whitespace windows for TF-IDF.
    Prefer sentence/paragraph boundaries, preserving exact offsets and overlap.
    """
    config = _config()
    size, overlap = config['chunk_tokens'], config['overlap']
    if model is not None:
        size = min(size, model.max_seq_length - model.tokenizer.num_special_tokens_to_add(False))
    if size <= overlap:
        raise ValueError('Embedding context too short for configured overlap')
    result = []
    for document in documents:
        content = document['text']
        offsets = (model.tokenizer(content, add_special_tokens=False, return_offsets_mapping=True,
                                   verbose=False)['offset_mapping']
                   if model is not None else [m.span() for m in re.finditer(r'\S+', content)])
        start = 0
        while start < len(offsets):
            end = min(start + size, len(offsets))
            if end < len(offsets):
                for candidate in range(end, start + size // 2, -1):
                    gap = content[offsets[candidate - 1][1]:offsets[candidate][0]]
                    if '\n' in gap or content[offsets[candidate - 1][1] - 1] in '.!?':
                        end = candidate
                        break
            left, right = offsets[start][0], offsets[end - 1][1]
            excerpt = content[left:right]
            ident = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{document['source']}:{left}:{right}:{excerpt}"))
            result.append({**document, 'text': excerpt, 'chunk_id': ident,
                           'start_char': left, 'end_char': right,
                           'start_line': content[:left].count('\n') + 1,
                           'end_line': content[:right].count('\n') + 1})
            if len(result) > 10000:
                raise ValueError('Corpus exceeds the chunk budget')
            if end == len(offsets):
                break
            start = max(start + 1, end - overlap)
    return result


def search_local(question: str, limit: int = 3) -> list[dict]:
    documents = chunks(corpus())
    if not documents:
        return []
    vectorizer = TfidfVectorizer(ngram_range=(1, 2), strip_accents='unicode')
    try:
        vectors = vectorizer.fit_transform([d['text'] for d in documents])
    except ValueError:
        return []
    scores = cosine_similarity(vectorizer.transform([question]), vectors)[0]
    matches = sorted(enumerate(scores), key=lambda pair: pair[1], reverse=True)[:limit]
    return [{**documents[i], 'score': round(float(score), 6), 'backend': 'tfidf'}
            for i, score in matches if score > 0]


def _qdrant_client():
    from qdrant_client import QdrantClient
    url = os.getenv('QDRANT_URL')
    return (QdrantClient(url=url, timeout=5, api_key=os.getenv('QDRANT_API_KEY')) if url else
            QdrantClient(path=os.getenv('QDRANT_PATH', str(ROOT / 'data' / 'qdrant_local'))))


@contextmanager
def _client(create: bool = False):
    # Local mode is exclusive across processes; serialize threads and release locks.
    with _LOCK:
        path = Path(os.getenv('QDRANT_PATH', str(ROOT / 'data' / 'qdrant_local')))
        if not create and not os.getenv('QDRANT_URL') and not (path / 'meta.json').is_file():
            raise FileNotFoundError('Local Qdrant index missing; run the local admin index command')
        client = _qdrant_client()
        try:
            yield client
        finally:
            client.close()


@lru_cache(maxsize=2)
def _load_model(name: str, revision: str | None, download: bool):
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(name, revision=revision, trust_remote_code=False, device='cpu',
                               cache_folder=os.getenv('RETAILMIND_MODEL_CACHE', str(ROOT / 'data' / 'embedding_cache')),
                               local_files_only=not download)


def _embeddings_model(download: bool = False):
    config = _config()
    return _load_model(config['model'], config['revision'], download)


def _fingerprint(documents: list[dict]) -> str:
    return hashlib.sha256(json.dumps([_config(), documents], sort_keys=True,
                                    ensure_ascii=False).encode('utf-8')).hexdigest()


def _vectors(model, texts: list[str]) -> np.ndarray:
    vectors = np.asarray(model.encode(texts, normalize_embeddings=True, show_progress_bar=False), dtype=float)
    dimension = (model.get_embedding_dimension() if hasattr(model, 'get_embedding_dimension')
                 else model.get_sentence_embedding_dimension())
    if vectors.shape != (len(texts), dimension) or not np.isfinite(vectors).all():
        raise ValueError('Invalid embedding dimensions or non-finite values')
    return vectors


def index_qdrant() -> dict:
    """CLI only: build staging, verify count, atomically switch the alias.
    Old versions are retained for manual rollback; identical content is reused.
    """
    from qdrant_client.models import (Distance, VectorParams, PointStruct, CreateAlias,
                                     CreateAliasOperation, DeleteAlias, DeleteAliasOperation)
    documents = corpus()
    if not documents:
        return {'documents': 0, 'chunks': 0, 'status': 'empty_corpus', 'index_unchanged': True}
    try:
        model = _embeddings_model()
    except OSError:
        model = _embeddings_model(download=True)
    pieces = chunks(documents, model)
    vectors = _vectors(model, [d['text'] for d in pieces])
    dim = int(vectors.shape[1])
    fingerprint = _fingerprint(documents)
    summary = {'documents': len(documents), 'chunks': len(pieces), 'dimension': dim,
               'embedding_model': _config()['model'], 'max_seq_length': model.max_seq_length,
               'fingerprint': fingerprint, 'backend': 'qdrant'}
    with _client(create=True) as client:
        aliases = {a.alias_name: a.collection_name for a in client.get_aliases().aliases}
        active = aliases.get(COLLECTION)
        if active:
            points, _ = client.scroll(active, limit=1, with_payload=True, with_vectors=False)
            if (points and points[0].payload.get('index_fingerprint') == fingerprint
                    and client.count(active, exact=True).count == len(pieces)):
                return {**summary, 'status': 'unchanged'}
        staging = COLLECTION + '_' + uuid.uuid4().hex
        client.create_collection(staging, vectors_config=VectorParams(size=dim, distance=Distance.COSINE))
        switch_attempted = False
        try:
            for offset in range(0, len(pieces), 64):
                client.upsert(staging, wait=True, points=[
                    PointStruct(id=d['chunk_id'], vector=v.tolist(), payload={
                        **d, 'index_fingerprint': fingerprint, 'embedding_config': _config(),
                        'dimension': dim, 'max_seq_length': model.max_seq_length})
                    for d, v in zip(pieces[offset:offset + 64], vectors[offset:offset + 64])])
            if client.count(staging, exact=True).count != len(pieces):
                raise RuntimeError('Incomplete index; previous alias preserved')
            operations = ([DeleteAliasOperation(delete_alias=DeleteAlias(alias_name=COLLECTION))] if active else [])
            operations.append(CreateAliasOperation(create_alias=CreateAlias(
                alias_name=COLLECTION, collection_name=staging)))
            switch_attempted = True
            client.update_collection_aliases(change_aliases_operations=operations)
        except Exception:
            # A remote timeout can occur after a successful alias swap. Never delete
            # that possibly-active collection; keep both versions for inspection.
            if not switch_attempted:
                client.delete_collection(staging)
            raise
    return {**summary, 'status': 'indexed'}


def search_qdrant(question: str, limit: int = 3) -> list[dict]:
    from qdrant_client.models import Filter, FieldCondition, MatchAny
    documents = corpus()
    if not documents:
        return []
    with _client() as client:
        points, _ = client.scroll(COLLECTION, limit=1, with_payload=True, with_vectors=False)
        if not points or points[0].payload.get('index_fingerprint') != _fingerprint(documents):
            raise ValueError('Missing/stale index or different embedding configuration; run retailmind index')
        model = _embeddings_model()  # Never download during an HTTP request.
        vector = _vectors(model, [question])[0]
        if len(vector) != points[0].payload['dimension']:
            raise ValueError('Embedding dimension mismatch; reindex required')
        # Preserve explicit technology names: dense multilingual similarity alone can
        # confuse a failed dbt test with a failed payment. Scope to documents actually
        # mentioning that component, then rank their chunks by real vector similarity.
        components = re.findall(r'\b(?:dbt|airflow|pyspark|spark)\b', question.lower())
        scoped = [d['source'] for d in documents if any(
            re.search(r'\b' + re.escape(term) + r'\b', d['text'], re.I) for term in components)]
        query_filter = Filter(must=[FieldCondition(key='source', match=MatchAny(any=scoped))]) if scoped else None
        result = client.query_points(collection_name=COLLECTION, query=vector.tolist(), with_payload=True,
                                     query_filter=query_filter,
                                     limit=limit, score_threshold=float(os.getenv('RAG_MIN_SCORE', '0.2'))).points
        allowed = {d['source']: d['text'] for d in documents}
        matches = []
        for point in result:
            payload = point.payload or {}
            source, left, right = payload.get('source'), payload.get('start_char'), payload.get('end_char')
            if (source not in allowed or not isinstance(left, int) or not isinstance(right, int)
                    or allowed[source][left:right] != payload.get('text')):
                raise ValueError('Index provenance mismatch')
            matches.append({**payload, 'score': float(point.score), 'backend': 'qdrant',
                            'strategy': 'component_scoped_semantic' if scoped else 'semantic'})
        return matches


def _failure_details(exc: Exception) -> dict:
    # Match only known library/internal conditions; never expose the exception
    # value, which may include configured URLs, keys or local filesystem paths.
    message = str(exc).lower()
    if isinstance(exc, RuntimeError) and 'already accessed' in message:
        code, hint = 'qdrant_locked', ('Le stockage Qdrant local est verrouillé par une autre instance. '
                                    'Fermer les autres API/CLI qui utilisent cet index, puis réessayer.')
    elif isinstance(exc, FileNotFoundError) and 'index missing' in message:
        code, hint = 'index_missing', 'Index Qdrant local absent. Exécuter la commande locale retailmind index.'
    elif isinstance(exc, ValueError) and any(word in message for word in ('stale', 'dimension mismatch', 'provenance')):
        code, hint = 'index_incompatible', 'Index Qdrant périmé ou incompatible avec le modèle/corpus. Réindexer localement.'
    elif isinstance(exc, ImportError):
        code, hint = 'rag_dependency_missing', 'Une dépendance RAG manque dans le Python qui exécute FastAPI.'
    elif isinstance(exc, OSError):
        code, hint = 'rag_local_io_error', ('Impossible de charger les embeddings locaux ou de lire le stockage. '
                                         'Vérifier le cache du modèle et les permissions ; indexer depuis la CLI si nécessaire.')
    else:
        code, hint = 'qdrant_unavailable', 'Recherche Qdrant indisponible. Vérifier le service, le modèle et les journaux FastAPI.'
    return {'code': code, 'error_type': type(exc).__name__, 'message': hint}


def retrieve(question: str, limit: int = 3, *, correlation_id: str | None = None) -> dict:
    if not isinstance(question, str) or not question.strip() or len(question) > 2000 or not 1 <= limit <= 5:
        raise ValueError('Invalid retrieval request')
    configured = os.getenv('RETAILMIND_RETRIEVAL', 'local').lower()
    if configured not in {'local', 'tfidf', 'qdrant'}:
        raise ValueError('Unknown retrieval backend')
    if not corpus():
        return {'sources': [], 'backend': 'none', 'warnings': ['Corpus documentaire vide : aucune recherche effectuée.']}
    if configured == 'qdrant':
        try:
            return {'sources': search_qdrant(question, limit), 'backend': 'qdrant', 'warnings': []}
        except Exception as exc:
            diagnostic = {**_failure_details(exc), 'correlation_id': correlation_id or str(uuid.uuid4())}
            log_failure(logger, exc, code=diagnostic['code'], correlation_id=diagnostic['correlation_id'],
                        level=logging.WARNING)
            return {'sources': search_local(question, limit), 'backend': 'tfidf',
                    'diagnostics': [diagnostic],
                    'warnings': [f"{diagnostic['message']} Fallback TF-IDF ({diagnostic['error_type']})."]}
    return {'sources': search_local(question, limit), 'backend': 'tfidf', 'warnings': []}


def search(question: str, limit: int = 3) -> list[dict]:
    return retrieve(question, limit)['sources']


def index_status() -> dict:
    """Read-only probe: no encoding, model downloads or index writes."""
    documents = corpus()
    result = {'configured_backend': os.getenv('RETAILMIND_RETRIEVAL', 'local'), 'documents': len(documents),
              'chunks': 0, 'qdrant_available': False, 'index_ready': False, 'embedding_model': _config()['model']}
    path = Path(os.getenv('QDRANT_PATH', str(ROOT / 'data' / 'qdrant_local')))
    if not os.getenv('QDRANT_URL') and not (path / 'meta.json').is_file():
        return {**result, 'status': 'not_indexed'}
    try:
        with _client() as client:
            result['qdrant_available'] = True
            if COLLECTION not in {a.alias_name for a in client.get_aliases().aliases}:
                return {**result, 'status': 'not_indexed'}
            result['chunks'] = client.count(COLLECTION, exact=True).count
            points, _ = client.scroll(COLLECTION, limit=1, with_payload=True, with_vectors=False)
            result['index_ready'] = bool(points and points[0].payload.get('index_fingerprint') == _fingerprint(documents))
            return {**result, 'status': 'ready' if result['index_ready'] else 'stale'}
    except Exception as exc:
        return {**result, 'status': 'unavailable', 'error_type': type(exc).__name__,
                'diagnostic': _failure_details(exc)}
