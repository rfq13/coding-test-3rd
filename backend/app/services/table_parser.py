"""
Simple TableParser implementation to unblock document processing.

This provides minimal parsing of pdfplumber-extracted tables and a
keyword-based classifier to detect likely table types.
"""
from typing import Any, Dict, List


class TableParser:
    """Parse and classify tables extracted from PDFs."""

    def parse_table(self, raw_table: Any) -> Dict[str, Any]:
        """Return a normalized representation of a table.

        pdfplumber typically returns tables as List[List[str|None]].
        We will treat the first non-empty row as headers and the rest as rows.

        Args:
            raw_table: Table object from pdfplumber or similar

        Returns:
            Dict with headers and rows keys.
        """
        headers: List[str] = []
        rows: List[List[str]] = []

        if isinstance(raw_table, list) and raw_table:
            # Find first non-empty row as headers
            for r in raw_table:
                if r and any(cell and str(cell).strip() for cell in r):
                    headers = [str(cell).strip() if cell is not None else "" for cell in r]
                    break
            # Remaining non-empty rows
            started = False if not headers else True
            for r in raw_table:
                if not started:
                    # skip until we hit headers row
                    if r and [str(c).strip() if c is not None else "" for c in r] == headers:
                        started = True
                    continue
                # Collect rows after headers
                if r and any(cell and str(cell).strip() for cell in r):
                    rows.append([str(cell).strip() if cell is not None else "" for cell in r])

        return {"headers": headers, "rows": rows}

    def classify_table(self, table: Dict[str, Any]) -> str:
        """Classify table type: 'capital_calls', 'distributions', 'adjustments', or 'unknown'."""
        text_blob = " ".join(table.get("headers", []))[:1024].lower()
        # Basic keyword heuristics
        if ("capital" in text_blob and "call" in text_blob) or ("called" in text_blob):
            return "capital_calls"
        if "distribution" in text_blob or "distributed" in text_blob or "dist." in text_blob:
            return "distributions"
        if "adjustment" in text_blob or "fee" in text_blob or "expense" in text_blob:
            return "adjustments"
        return "unknown"

    def parse_tables(self, tables: List[Any]) -> List[Dict[str, Any]]:
        """Batch parse tables, returns list of normalized tables."""
        parsed = []
        for t in tables:
            pt = self.parse_table(t)
            pt["type"] = self.classify_table(pt)
            parsed.append(pt)
        return parsed