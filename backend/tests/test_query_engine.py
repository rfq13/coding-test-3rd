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


def test_query_engine_intent_and_response(monkeypatch, db_session: Session):
    # Seed fund
    fund = Fund(name="Fund Q")
    db_session.add(fund)
    db_session.commit()
    db_session.refresh(fund)

    qe = QueryEngine(db_session)

    # Mock intent classifier to force calculation intent
    async def fake_classify_intent(q: str) -> str:
        return "calculation" if "dpi" in q.lower() else "retrieval"

    monkeypatch.setattr(qe, "_classify_intent", fake_classify_intent)

    # Mock vector store hybrid_search
    async def fake_hybrid_search(query: str, k: int, filter_metadata=None, weights=None):
        return [
            {"id": 1, "document_id": 10, "fund_id": fund.id, "content": "Context A", "score": 0.9},
            {"id": 2, "document_id": 11, "fund_id": fund.id, "content": "Context B", "score": 0.8},
        ]

    monkeypatch.setattr(qe.vector_store, "hybrid_search", fake_hybrid_search)

    # Mock metrics calculator
    monkeypatch.setattr(qe.metrics_calculator, "calculate_all_metrics", lambda fid: {"pic": 100.0, "dpi": 1.2, "irr": 15.0, "total_distributions": 120.0, "tvpi": None, "rvpi": None, "nav": None})

    # Mock LLM to deterministic output
    qe.llm = DummyLLM("Answer with **important numbers** and sources")

    res = asyncio.run(qe.process_query("What is the current DPI for this fund?", fund_id=fund.id))
    assert "Answer" in res["answer"]
    assert res["metrics"]["dpi"] == 1.2
    assert len(res["sources"]) == 2
    assert res["sources"][0]["metadata"]["document_id"] == 10


def test_query_engine_general_intent(monkeypatch, db_session: Session):
    # Seed fund
    fund = Fund(name="Fund G")
    db_session.add(fund)
    db_session.commit()
    db_session.refresh(fund)

    qe = QueryEngine(db_session)

    # Mock intent classifier to general
    async def fake_classify_intent(q: str) -> str:
        return "general"

    monkeypatch.setattr(qe, "_classify_intent", fake_classify_intent)

    # Mock vector store hybrid_search
    async def fake_hybrid_search(query: str, k: int, filter_metadata=None, weights=None):
        return [
            {"id": 1, "document_id": 100, "fund_id": fund.id, "content": "Overview", "score": 0.5},
            {"id": 2, "document_id": 101, "fund_id": fund.id, "content": "Strategy", "score": 0.4},
        ]

    monkeypatch.setattr(qe.vector_store, "hybrid_search", fake_hybrid_search)

    # Mock LLM
    qe.llm = DummyLLM("General fund overview response")

    res = asyncio.run(qe.process_query("Tell me about the fund", fund_id=fund.id))
    assert "General fund overview" in res["answer"]
    assert res["metrics"] is None
    assert len(res["sources"]) == 2