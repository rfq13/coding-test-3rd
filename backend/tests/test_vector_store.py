import asyncio
import math
import numpy as np
import pytest


class Result:
    def __init__(self, rows=None, scalar_value=None):
        self._rows = rows or []
        self._scalar = scalar_value

    def scalar(self):
        return self._scalar

    def fetchall(self):
        return list(self._rows)

    def __iter__(self):
        return iter(self._rows)


class FakeDB:
    def __init__(self):
        self.statements = []
        self.params_log = []
        self.committed = False
        self.rolled_back = False
        self.analyzed = False
        # configurable returns
        self.count_return = 0
        self.size_return = 0
        self.index_rows = []
        self.similarity_rows = []
        self.lexical_rows = []
        self.pattern_rows = []

    def execute(self, sql, params=None):
        sql_text = getattr(sql, 'text', str(sql))
        self.statements.append(sql_text)
        if params:
            self.params_log.append(params)

        # specific handlers
        if 'ANALYZE document_embeddings' in sql_text:
            self.analyzed = True
            return Result()
        if 'SELECT COUNT(*) FROM document_embeddings' in sql_text:
            return Result(scalar_value=self.count_return)
        if "SELECT pg_total_relation_size('document_embeddings')" in sql_text:
            return Result(scalar_value=self.size_return)
        if 'FROM pg_indexes' in sql_text:
            return Result(rows=self.index_rows)
        if 'embedding <=>' in sql_text:
            return Result(rows=self.similarity_rows)
        if 'ts_rank(' in sql_text:
            return Result(rows=self.lexical_rows)
        if 'similarity(content' in sql_text and 'FROM document_embeddings' in sql_text:
            return Result(rows=self.pattern_rows)
        return Result()

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True


@pytest.mark.asyncio
async def test_rebuild_ivfflat_index_auto_lists_clamped(monkeypatch):
    from app.services.vector_store import VectorStore

    fake = FakeDB()
    fake.count_return = 400  # sqrt(400)=20 -> clamp to 100

    # avoid real embeddings init
    monkeypatch.setattr(VectorStore, '_initialize_embeddings', lambda self: object())

    vs = VectorStore(db=fake)
    vs.rebuild_ivfflat_index(lists=None)

    # Ensure DROP and CREATE index executed and lists clamped to 100
    created_sqls = [s for s in fake.statements if 'CREATE INDEX document_embeddings_embedding_idx' in s]
    assert any('WITH (lists = 100)' in s for s in created_sqls)
    assert any('DROP INDEX IF EXISTS document_embeddings_embedding_idx' in s for s in fake.statements)
    assert fake.analyzed is True
    assert fake.committed is True


def test_get_index_stats_returns_expected(monkeypatch):
    from app.services.vector_store import VectorStore

    fake = FakeDB()
    fake.size_return = 1024
    fake.count_return = 3
    fake.index_rows = [
        ('document_embeddings_embedding_idx', 'CREATE INDEX ...'),
        ('document_embeddings_tsv_idx', 'CREATE INDEX ...'),
    ]

    # avoid real embeddings init
    monkeypatch.setattr(VectorStore, '_initialize_embeddings', lambda self: object())

    vs = VectorStore(db=fake)
    stats = vs.get_index_stats()

    assert stats['table_size_bytes'] == 1024
    assert stats['row_count'] == 3
    assert {'name': 'document_embeddings_embedding_idx', 'def': 'CREATE INDEX ...'} in stats['indexes']
    assert {'name': 'document_embeddings_tsv_idx', 'def': 'CREATE INDEX ...'} in stats['indexes']


@pytest.mark.asyncio
async def test_add_document_inserts_embedding_and_metadata(monkeypatch):
    from app.services.vector_store import VectorStore

    fake = FakeDB()

    # avoid real embeddings init
    monkeypatch.setattr(VectorStore, '_initialize_embeddings', lambda self: object())
    # mock embedding generation
    async def _fake_get_embedding(self, text):
        return np.array([0.1, 0.2], dtype=np.float32)
    monkeypatch.setattr(VectorStore, '_get_embedding', _fake_get_embedding)

    vs = VectorStore(db=fake)
    md = {"document_id": 7, "fund_id": 9, "source": "unit-test"}
    await vs.add_document("Hello world", md)

    # Verify INSERT executed with expected params and commit called
    assert any('INSERT INTO document_embeddings' in s for s in fake.statements)
    assert fake.committed is True
    # last params contain required keys
    assert fake.params_log[-1]['document_id'] == 7
    assert fake.params_log[-1]['fund_id'] == 9
    assert fake.params_log[-1]['content'] == "Hello world"
    # embedding serialized as a Python list string
    assert fake.params_log[-1]['embedding'] == str([0.1, 0.2])


@pytest.mark.asyncio
async def test_similarity_search_filters_and_formats_results(monkeypatch):
    from app.services.vector_store import VectorStore

    fake = FakeDB()
    fake.similarity_rows = [
        (1, 11, 21, 'A', {'a': 1}, 0.9),
        (2, 12, 22, 'B', {'b': 2}, 0.8),
    ]

    monkeypatch.setattr(VectorStore, '_initialize_embeddings', lambda self: object())
    async def _fake_get_embedding2(self, text):
        return np.array([0.5, 0.6], dtype=np.float32)
    monkeypatch.setattr(VectorStore, '_get_embedding', _fake_get_embedding2)

    vs = VectorStore(db=fake)
    res = await vs.similarity_search(
        "query",
        k=2,
        filter_metadata={"document_ids": [1, 2, 3], "fund_id": 5}
    )

    assert len(res) == 2
    assert res[0]['id'] == 1 and isinstance(res[0]['score'], float)
    # Ensure SQL contained expected filters
    search_sqls = [s for s in fake.statements if 'SELECT' in s and 'embedding <=>' in s]
    assert any('document_id IN (1,2,3)' in s for s in search_sqls)
    assert any('fund_id = 5' in s for s in search_sqls)


@pytest.mark.asyncio
async def test_lexical_search_handles_null_score(monkeypatch):
    from app.services.vector_store import VectorStore

    fake = FakeDB()
    fake.lexical_rows = [
        (3, 13, 23, 'C', {'c': 3}, None),
    ]

    monkeypatch.setattr(VectorStore, '_initialize_embeddings', lambda self: object())

    vs = VectorStore(db=fake)
    rows = await vs.lexical_search("q", k=1)
    assert len(rows) == 1
    assert rows[0]['score'] == 0.0


@pytest.mark.asyncio
async def test_pattern_search_threshold_and_filters(monkeypatch):
    from app.services.vector_store import VectorStore

    fake = FakeDB()
    fake.pattern_rows = [
        (4, 14, 24, 'D', {'d': 4}, 0.4),
    ]

    monkeypatch.setattr(VectorStore, '_initialize_embeddings', lambda self: object())

    vs = VectorStore(db=fake)
    rows = await vs.pattern_search("q", k=1, filter_metadata={"document_id": 99}, similarity_threshold=0.3)
    assert len(rows) == 1
    # Ensure SQL contained fuzzy operator and threshold
    pat_sqls = [s for s in fake.statements if 'similarity(content' in s and 'FROM document_embeddings' in s]
    assert any('content % :q' in s for s in pat_sqls)
    assert any('document_id = 99' in s for s in pat_sqls)
    assert any('AND similarity(content, :q) >= :threshold' in s for s in pat_sqls)


@pytest.mark.asyncio
async def test_hybrid_search_rrf_fusion(monkeypatch):
    from app.services.vector_store import VectorStore

    monkeypatch.setattr(VectorStore, '_initialize_embeddings', lambda self: object())
    vs = VectorStore(db=FakeDB())

    async def fake_dense(self, q, k, fm):
        return [
            {"id": 10, "document_id": 1, "fund_id": 1, "content": "d1", "metadata": {}, "score": 0.9},
            {"id": 20, "document_id": 2, "fund_id": 1, "content": "d2", "metadata": {}, "score": 0.8},
        ]

    async def fake_lex(self, q, k, fm):
        return [
            {"id": 20, "document_id": 2, "fund_id": 1, "content": "l2", "metadata": {}, "score": 0.7},
            {"id": 30, "document_id": 3, "fund_id": 1, "content": "l3", "metadata": {}, "score": 0.6},
        ]

    async def fake_pat(self, q, k, fm):
        return [
            {"id": 10, "document_id": 1, "fund_id": 1, "content": "p1", "metadata": {}, "score": 0.5},
            {"id": 30, "document_id": 3, "fund_id": 1, "content": "p3", "metadata": {}, "score": 0.4},
        ]

    monkeypatch.setattr(VectorStore, 'similarity_search', fake_dense)
    monkeypatch.setattr(VectorStore, 'lexical_search', fake_lex)
    monkeypatch.setattr(VectorStore, 'pattern_search', fake_pat)

    out = await vs.hybrid_search("q", k=3)
    # All ids present
    ids = [r['id'] for r in out]
    assert set(ids) == {10, 20, 30}
    # Scores are positive floats and sorted desc
    scores = [r['score'] for r in out]
    assert all(isinstance(s, float) and s > 0 for s in scores)
    assert scores == sorted(scores, reverse=True)


def test_clear_deletes_all_and_by_fund(monkeypatch):
    from app.services.vector_store import VectorStore

    fake = FakeDB()
    monkeypatch.setattr(VectorStore, '_initialize_embeddings', lambda self: object())
    vs = VectorStore(db=fake)

    # by fund_id
    vs.clear(fund_id=5)
    assert any('DELETE FROM document_embeddings WHERE fund_id = :fund_id' in s for s in fake.statements)
    assert fake.committed is True

    # reset
    fake.committed = False

    # all
    vs.clear()
    assert any('DELETE FROM document_embeddings' in s for s in fake.statements)
    assert fake.committed is True