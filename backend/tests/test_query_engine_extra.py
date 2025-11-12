import asyncio
import pytest
from sqlalchemy.orm import Session

from app.services.query_engine import QueryEngine
from app.models.fund import Fund


class DummyLLM:
    def __init__(self, response_text: str):
        self._text = response_text

    def invoke(self, messages):
        class R:
            content = None
        r = R()
        r.content = self._text
        return r


def test_query_engine_definition_intent(monkeypatch, db_session: Session):
    fund = Fund(name="Fund D")
    db_session.add(fund)
    db_session.commit()
    db_session.refresh(fund)

    qe = QueryEngine(db_session)

    async def fake_classify_intent(q: str) -> str:
        return "definition"

    monkeypatch.setattr(qe, "_classify_intent", fake_classify_intent)

    async def fake_hybrid_search(query: str, k: int, filter_metadata=None, weights=None):
        return [
            {"id": 10, "document_id": 200, "fund_id": fund.id, "content": "Definition context", "score": 0.7},
        ]

    monkeypatch.setattr(qe.vector_store, "hybrid_search", fake_hybrid_search)

    qe.llm = DummyLLM("DPI means distributions divided by paid-in capital")

    res = asyncio.run(qe.process_query("What does DPI mean?", fund_id=fund.id))
    assert "DPI" in res["answer"]
    assert res["metrics"] is None
    assert len(res["sources"]) == 1


def test_query_engine_retrieval_filters_by_document_ids(monkeypatch, db_session: Session):
    fund = Fund(name="Fund R")
    db_session.add(fund)
    db_session.commit()
    db_session.refresh(fund)

    qe = QueryEngine(db_session)

    async def fake_classify_intent(q: str) -> str:
        return "retrieval"

    monkeypatch.setattr(qe, "_classify_intent", fake_classify_intent)

    last_filter = {"value": None}

    async def fake_hybrid_search(query: str, k: int, filter_metadata=None, weights=None):
        last_filter["value"] = filter_metadata
        return [
            {"id": 1, "document_id": 999, "fund_id": fund.id, "content": "Filtered doc", "score": 0.6},
        ]

    monkeypatch.setattr(qe.vector_store, "hybrid_search", fake_hybrid_search)

    qe.llm = DummyLLM("Here are the requested items")

    res = asyncio.run(qe.process_query("Show me distributions", fund_id=fund.id, document_ids=[999]))
    assert res["metrics"] is None
    assert last_filter["value"] == {"document_ids": [999]}
    assert res["sources"][0]["metadata"]["document_id"] == 999


@pytest.mark.asyncio
async def test_query_engine_classify_intent_coverage(db_session: Session):
    qe = QueryEngine(db_session)
    assert await qe._classify_intent("Calculate IRR for Fund") == "calculation"
    assert await qe._classify_intent("Define distribution waterfall") == "definition"
    assert await qe._classify_intent("Show me all documents") == "retrieval"
    assert await qe._classify_intent("Hello there!") == "general"