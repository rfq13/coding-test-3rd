from decimal import Decimal
from datetime import date

from app.services.document_processor import DocumentProcessor


dp = DocumentProcessor(db=None)


def test_parse_date_common_formats():
    assert dp._parse_date("2023-10-01") == date(2023, 10, 1)
    assert dp._parse_date("01/10/2023") == date(2023, 10, 1)
    # Ambiguous formats default to day-first (DD/MM/YYYY)
    assert dp._parse_date("10/01/2023") == date(2023, 1, 10)
    assert dp._parse_date("01-10-2023") == date(2023, 10, 1)
    assert dp._parse_date("Oct 01, 2023") == date(2023, 10, 1)
    assert dp._parse_date("01 Oct 2023") == date(2023, 10, 1)


def test_parse_date_digits_only():
    assert dp._parse_date("20231001") == date(2023, 10, 1)
    assert dp._parse_date("2023/10/01") == date(2023, 10, 1)


def test_parse_date_invalid_returns_none():
    assert dp._parse_date("") is None
    assert dp._parse_date("not a date") is None


def test_parse_amount_basic():
    assert dp._parse_amount("100") == Decimal("100")
    assert dp._parse_amount("1,000.50") == Decimal("1000.50")
    assert dp._parse_amount("$2,345") == Decimal("2345")


def test_parse_amount_negative_parentheses():
    assert dp._parse_amount("($1,234.56)") == Decimal("-1234.56")


def test_parse_amount_commas_as_decimal():
    # When only commas present, normalize to decimal point
    assert dp._parse_amount("1,23") == Decimal("1.23")


def test_parse_amount_invalid_returns_none():
    assert dp._parse_amount("") is None
    assert dp._parse_amount("abc") is None