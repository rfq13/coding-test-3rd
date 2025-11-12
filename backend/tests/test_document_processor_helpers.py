import pytest
from decimal import Decimal
from datetime import date

from app.services.document_processor import DocumentProcessor


def test_parse_amount_various_formats():
    dp = DocumentProcessor()
    # US format
    assert dp._parse_amount("$1,234.56") == Decimal("1234.56")
    # Mixed separators (dot + comma): current implementation assumes dot as decimal
    assert dp._parse_amount("1.234,56") == Decimal("1.23456")
    # Negative with parentheses
    assert dp._parse_amount("($1,000.00)") == Decimal("-1000.00")
    # No digits
    assert dp._parse_amount("foo") is None


def test_parse_date_various_formats():
    dp = DocumentProcessor()
    assert dp._parse_date("2023-12-25") == date(2023, 12, 25)
    assert dp._parse_date("25/12/2023") == date(2023, 12, 25)
    assert dp._parse_date("Dec 25, 2023") == date(2023, 12, 25)
    assert dp._parse_date("20231225") == date(2023, 12, 25)
    assert dp._parse_date("bad") is None


def test_chunk_text_default_settings_creates_overlapping_chunks():
    dp = DocumentProcessor()
    long_text = "A" * 1200
    chunks = dp._chunk_text([{"text": long_text, "page": 1}])
    # With CHUNK_SIZE=1000 and OVERLAP=200, expect 2 chunks
    assert len(chunks) == 2
    assert chunks[0]["page"] == 1
    assert chunks[0]["section"] == "text"
    assert chunks[1]["page"] == 1
    assert len(chunks[0]["content"]) == 1000
    assert len(chunks[1]["content"]) == 400