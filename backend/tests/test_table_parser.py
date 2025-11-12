import pytest

from app.services.table_parser import TableParser


def test_classify_capital_calls():
    tp = TableParser()
    table = {
        "headers": ["Call Date", "Amount", "Type", "Description"],
        "rows": [["2023-01-01", "$100", "Capital Call", "Initial call"]],
    }
    assert tp.classify_table(table) == "capital_calls"


def test_classify_distributions():
    tp = TableParser()
    table = {
        "headers": ["Distribution Date", "Amount", "Type", "Description"],
        "rows": [["2023-02-01", "$250", "Cash", "Quarterly distribution"]],
    }
    assert tp.classify_table(table) == "distributions"


def test_classify_adjustments():
    tp = TableParser()
    table = {
        "headers": ["Adjustment Date", "Amount", "Category", "Description"],
        "rows": [["2023-03-01", "$50", "Management Fee", "Fee adjustment"]],
    }
    assert tp.classify_table(table) == "adjustments"


def test_classify_unknown_when_low_signal():
    tp = TableParser()
    table = {
        "headers": ["Col1", "Col2", "Col3"],
        "rows": [["x", "y", "z"], ["", "", ""]],
    }
    assert tp.classify_table(table) in {"unknown", "adjustments", "distributions", "capital_calls"}


def test_parse_table_detects_header_and_drops_empty_columns():
    tp = TableParser()
    raw_table = [
        ["", "", ""],
        ["Distribution Date", "Amount", "Type", "Description", ""],
        ["2023-10-01", "$1,000", "Cash", "Quarterly distribution", ""],
        ["2023-11-01", "$500", "Cash", "Special distribution", ""],
        ["", "", "", "", ""],
    ]

    parsed = tp.parse_table(raw_table)
    assert parsed["headers"] == ["Distribution Date", "Amount", "Type", "Description"]
    assert len(parsed["rows"]) == 2
    assert parsed["rows"][0] == ["2023-10-01", "$1,000", "Cash", "Quarterly distribution"]