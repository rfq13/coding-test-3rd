import pytest
from typing import Any, List
from sqlalchemy.orm import Session

from app.services.document_processor import DocumentProcessor
from app.models.fund import Fund
from app.models.transaction import CapitalCall, Distribution, Adjustment


class FakePage:
    def __init__(self, text: str, tables: List[List[List[str]]]):
        self._text = text
        self._tables = tables

    def extract_text(self) -> str:
        return self._text

    def extract_tables(self):
        return self._tables


class FakePDF:
    def __init__(self, pages: List[FakePage]):
        self.pages = pages

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class DummyVectorStore:
    def __init__(self, *args, **kwargs):
        self.added: List[Any] = []

    async def add_document(self, content: str, metadata: dict):
        self.added.append({"content": content, "metadata": metadata})


import asyncio

def test_process_document_parses_and_saves_tables(monkeypatch, db_session: Session):
    # Seed fund
    fund = Fund(name="Fund A")
    db_session.add(fund)
    db_session.commit()
    db_session.refresh(fund)

    # Build fake PDF with one page
    # Table headers suggest distributions; include two data rows
    raw_table = [
        ["Distribution Date", "Amount", "Type", "Description"],
        ["2023-10-01", "$1,000", "Cash", "Quarterly distribution"],
        ["2023-11-01", "$500", "Cash", "Special distribution"],
    ]
    page = FakePage(text="Some narrative about fund performance.", tables=[raw_table])
    pdf = FakePDF(pages=[page])

    # Patch pdfplumber.open to return our fake PDF
    import app.services.document_processor as dp_mod
    monkeypatch.setattr(dp_mod.pdfplumber, "open", lambda _: pdf)

    # Patch VectorStore used inside DocumentProcessor to a dummy one (no DB)
    dummy_vs = DummyVectorStore()
    monkeypatch.setattr(dp_mod, "VectorStore", lambda: dummy_vs)

    proc = DocumentProcessor(db=db_session)
    result = asyncio.run(proc.process_document("/path/to/fake.pdf", document_id=1, fund_id=fund.id))

    assert result["status"] == "completed"
    stats = result["stats"]
    assert stats["pages"] == 1
    assert stats["tables"] == 1
    assert stats["chunks"] >= 1

    # Verify rows persisted into distributions table
    rows = db_session.query(Distribution).filter(Distribution.fund_id == fund.id).all()
    assert len(rows) == 2
    amounts = sorted(float(r.amount) for r in rows)
    assert amounts == [500.0, 1000.0]

    # Verify VectorStore received chunks
    assert len(dummy_vs.added) >= 1
    # At least one chunk should contain the textual table summary
    assert any("Table(distributions)" in c["content"] for c in dummy_vs.added)


def test_save_parsed_tables_calls_and_adjustments(db_session: Session):
    # Seed fund
    from app.models.fund import Fund
    fund = Fund(name="Fund B")
    db_session.add(fund)
    db_session.commit()
    db_session.refresh(fund)

    proc = DocumentProcessor(db=db_session)

    parsed_tables = [
        {
            "type": "capital_calls",
            "headers": ["Call Date", "Amount", "Type", "Description"],
            "rows": [
                ["2023-01-10", "$2,000", "Capital Call", "Initial"],
                ["2023-02-15", "$500", "Capital Call", "Follow-on"],
            ],
        },
        {
            "type": "adjustments",
            "headers": ["Adjustment Date", "Amount", "Category", "Description"],
            "rows": [
                ["2023-03-01", "$100", "Management Fee", "Fee adjustment"],
            ],
        },
    ]

    # Persist
    proc._save_parsed_tables(db_session, fund_id=fund.id, parsed_tables=parsed_tables)

    # Verify capital calls
    from app.models.transaction import CapitalCall, Adjustment
    calls = db_session.query(CapitalCall).filter(CapitalCall.fund_id == fund.id).all()
    assert len(calls) == 2
    assert sorted(float(c.amount) for c in calls) == [500.0, 2000.0]

    # Verify adjustments
    adjs = db_session.query(Adjustment).filter(Adjustment.fund_id == fund.id).all()
    assert len(adjs) == 1
    assert float(adjs[0].amount) == 100.0