"""
TableParser for detecting headers/rows and classifying table types from
pdfplumber-extracted tables.

Enhancements:
- Robust header detection based on density and common header keywords.
- Normalizes row lengths to match headers; drops all-empty rows/columns.
- Classification uses weighted keywords across headers and first rows.
"""
from typing import Any, Dict, List, Tuple


COMMON_HEADER_KEYWORDS = {
    "date", "amount", "type", "description", "category",
    "call", "distribution", "adjustment", "usd", "value"
}


class TableParser:
    """Parse and classify tables extracted from PDFs."""

    def _normalize_cell(self, cell: Any) -> str:
        return str(cell).strip() if cell is not None else ""

    def _row_nonempty_cells(self, row: List[Any]) -> int:
        return sum(1 for c in row if c is not None and str(c).strip())

    def _detect_header_index(self, rows: List[List[Any]]) -> int:
        """Pick a likely header row by keyword presence and density."""
        best_idx = -1
        best_score = -1
        for i, r in enumerate(rows):
            normalized = [self._normalize_cell(c).lower() for c in r]
            density = self._row_nonempty_cells(r)
            keyword_hits = sum(1 for h in normalized if any(k in h for k in COMMON_HEADER_KEYWORDS))
            score = density + keyword_hits * 2
            if score > best_score:
                best_score = score
                best_idx = i
        return best_idx if best_idx >= 0 else 0

    def _drop_empty_columns(self, headers: List[str], rows: List[List[str]]) -> Tuple[List[str], List[List[str]]]:
        keep_indices = [i for i, h in enumerate(headers) if h]
        if not keep_indices:
            # if all headers empty, keep all columns
            keep_indices = list(range(len(headers)))
        new_headers = [headers[i] for i in keep_indices]
        new_rows = [[row[i] if i < len(row) else "" for i in keep_indices] for row in rows]
        return new_headers, new_rows

    def parse_table(self, raw_table: Any) -> Dict[str, Any]:
        """Return a normalized representation of a table.

        pdfplumber returns tables as List[List[str|None]]. We detect the best
        header row and normalize subsequent rows to the same width.
        """
        headers: List[str] = []
        data_rows: List[List[str]] = []

        if isinstance(raw_table, list) and raw_table:
            header_idx = self._detect_header_index(raw_table)
            headers = [self._normalize_cell(c) for c in raw_table[header_idx]]
            width = len(headers)
            for j, r in enumerate(raw_table):
                if j <= header_idx:
                    continue
                if not r or self._row_nonempty_cells(r) == 0:
                    continue
                normalized = [self._normalize_cell(c) for c in r]
                # pad/truncate to header width
                if len(normalized) < width:
                    normalized = normalized + [""] * (width - len(normalized))
                elif len(normalized) > width:
                    normalized = normalized[:width]
                data_rows.append(normalized)

        # drop completely empty columns to reduce noise
        headers, data_rows = self._drop_empty_columns(headers, data_rows)
        return {"headers": headers, "rows": data_rows}

    def classify_table(self, table: Dict[str, Any]) -> str:
        """Classify table type: capital_calls | distributions | adjustments | unknown.

        Uses weighted keywords across headers and first few rows.
        """
        headers = [h.lower() for h in table.get("headers", [])]
        first_rows = [" ".join(r).lower() for r in table.get("rows", [])[:3]]
        blob = " ".join(headers + first_rows)

        scores = {"capital_calls": 0, "distributions": 0, "adjustments": 0}

        # Capital Calls indicators
        for kw in ["capital call", "drawdown", "contribution", "called", "call date"]:
            if kw in blob:
                scores["capital_calls"] += 3
        for kw in ["amount", "date", "type"]:
            if kw in blob:
                scores["capital_calls"] += 1

        # Distributions indicators
        for kw in ["distribution", "proceeds", "return", "paid", "dist."]:
            if kw in blob:
                scores["distributions"] += 3
        for kw in ["amount", "date", "type"]:
            if kw in blob:
                scores["distributions"] += 1

        # Adjustments indicators
        for kw in ["adjustment", "management fee", "fee", "expense", "nav"]:
            if kw in blob:
                scores["adjustments"] += 3
        for kw in ["amount", "date", "category", "description"]:
            if kw in blob:
                scores["adjustments"] += 1

        # Choose by highest score with minimal threshold
        best = max(scores.items(), key=lambda x: x[1])
        return best[0] if best[1] >= 3 else "unknown"

    def parse_tables(self, tables: List[Any]) -> List[Dict[str, Any]]:
        """Batch parse tables, returns list of normalized tables with type."""
        parsed: List[Dict[str, Any]] = []
        for t in tables:
            pt = self.parse_table(t)
            pt["type"] = self.classify_table(pt)
            parsed.append(pt)
        return parsed