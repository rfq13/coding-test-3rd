"""
Document processing service using pdfplumber

TODO: Implement the document processing pipeline
- Extract tables from PDF using pdfplumber
- Classify tables (capital calls, distributions, adjustments)
- Extract and chunk text for vector storage
- Handle errors and edge cases
"""
from typing import Dict, List, Any
import pdfplumber
# Try to import a specific PDF syntax error for better handling
try:
    from pdfminer.pdfparser import PDFSyntaxError as _PDFSyntaxError  # type: ignore
except Exception:
    _PDFSyntaxError = Exception
from app.core.config import settings
from app.services.table_parser import TableParser
from app.services.vector_store import VectorStore
from sqlalchemy.orm import Session
from app.models.transaction import CapitalCall, Distribution, Adjustment
from datetime import datetime, date
from decimal import Decimal
import re

class DocumentProcessor:
    """Process PDF documents and extract structured data"""
    
    def __init__(self, db: Session | None = None):
        self.table_parser = TableParser()
        self.db = db
    
    async def process_document(self, file_path: str, document_id: int, fund_id: int) -> Dict[str, Any]:
        """
        Process a PDF document
        
        TODO: Implement this method
        - Open PDF with pdfplumber
        - Extract tables from each page
        - Parse and classify tables using TableParser
        - Extract text and create chunks
        - Store chunks in vector database
        - Return processing statistics
        
        Args:
            file_path: Path to the PDF file
            document_id: Database document ID
            fund_id: Fund ID
            
        Returns:
            Processing result with statistics
        """
        stats = {
            "pages": 0,
            "tables": 0,
            "chunks": 0,
            "pages_skipped": 0,
            "errors": [],
        }
        try:
            vector_store = VectorStore()
            text_content: List[Dict[str, Any]] = []
            try:
                with pdfplumber.open(file_path) as pdf:
                    stats["pages"] = len(pdf.pages)
                    for idx, page in enumerate(pdf.pages, start=1):
                        try:
                            # Extract text
                            page_text = page.extract_text() or ""
                            if page_text.strip():
                                text_content.append({
                                    "text": page_text,
                                    "page": idx,
                                })

                            # Extract and parse tables
                            raw_tables = page.extract_tables() or []
                            parsed_tables = self.table_parser.parse_tables(raw_tables)
                            stats["tables"] += len(parsed_tables)
                            # Persist parsed tables to SQL if DB session available
                            if self.db and parsed_tables:
                                self._save_parsed_tables(self.db, fund_id, parsed_tables)
                            # Optionally, store table summaries as text chunks
                            for t_i, t in enumerate(parsed_tables):
                                # Convert table to a simple textual representation
                                header_line = " | ".join(t.get("headers", []))
                                rows_lines = [" | ".join(r) for r in t.get("rows", [])][:10]
                                table_text = f"Table({t.get('type','unknown')})\n{header_line}\n" + "\n".join(rows_lines)
                                if table_text.strip():
                                    text_content.append({
                                        "text": table_text,
                                        "page": idx,
                                        "section": "table",
                                        "table_type": t.get("type", "unknown"),
                                        "table_index": t_i,
                                    })
                        except Exception as page_err:
                            # Skip problematic pages but continue processing others
                            stats["pages_skipped"] += 1
                            stats["errors"].append(f"page_{idx}: {str(page_err)}")
                            continue
            except _PDFSyntaxError as e:
                return {"status": "failed", "error": f"malformed_pdf: {str(e)}", "stats": stats}
            except Exception as e:
                # Other exceptions while opening the PDF
                return {"status": "failed", "error": f"pdf_open_error: {str(e)}", "stats": stats}

            # Chunk text content
            chunks = self._chunk_text(text_content)

            # Store chunks in vector database
            for c_i, chunk in enumerate(chunks):
                metadata = {
                    "document_id": document_id,
                    "fund_id": fund_id,
                    "page": chunk.get("page"),
                    "section": chunk.get("section", "text"),
                    "chunk_index": c_i,
                    "table_type": chunk.get("table_type"),
                }
                await vector_store.add_document(chunk["content"], metadata)

            stats["chunks"] = len(chunks)
            return {"status": "completed", "stats": stats}
        except Exception as e:
            return {"status": "failed", "error": str(e), "stats": stats}
    
    def _chunk_text(self, text_content: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Chunk text content for vector storage
        
        TODO: Implement intelligent text chunking
        - Split text into semantic chunks
        - Maintain context overlap
        - Preserve sentence boundaries
        - Add metadata to each chunk
        
        Args:
            text_content: List of text content with metadata
            
        Returns:
            List of text chunks with metadata
        """
        chunks: List[Dict[str, Any]] = []
        max_len = getattr(settings, "CHUNK_SIZE", 1000)
        overlap = getattr(settings, "CHUNK_OVERLAP", 200)
        step = max(1, max_len - overlap)

        for item in text_content:
            text = item.get("text", "")
            if not text:
                continue
            # Normalize whitespace
            text = "\n".join([line.strip() for line in text.splitlines() if line.strip()])

            start = 0
            while start < len(text):
                end = min(len(text), start + max_len)
                content = text[start:end]
                # Avoid extremely tiny fragments
                if len(content.strip()) < 20:
                    break
                chunk_meta = {
                    "page": item.get("page"),
                    "section": item.get("section", "text"),
                    "table_type": item.get("table_type"),
                }
                chunks.append({"content": content, **chunk_meta})
                if end == len(text):
                    break
                start += step

        return chunks

    # --- Table saving helpers ---
    def _save_parsed_tables(self, db: Session, fund_id: int, parsed_tables: List[Dict[str, Any]]) -> None:
        """Save parsed tables into corresponding SQL tables using simple heuristics.

        We try to map common columns: date, amount, type, description.
        Rows that fail parsing are skipped silently.
        """
        for table in parsed_tables:
            ttype = table.get("type", "unknown")
            headers = [h.lower() for h in table.get("headers", [])]
            rows = table.get("rows", [])
            colmap = self._infer_column_indices(headers)
            if not rows:
                continue
            try:
                if ttype == "capital_calls":
                    for r in rows:
                        data = self._extract_row_data(r, colmap)
                        if not data:
                            continue
                        db.add(CapitalCall(
                            fund_id=fund_id,
                            call_date=data.get("date") or datetime.utcnow().date(),
                            call_type=data.get("type"),
                            amount=data.get("amount") or Decimal("0"),
                            description=data.get("description")
                        ))
                    db.commit()
                elif ttype == "distributions":
                    for r in rows:
                        data = self._extract_row_data(r, colmap)
                        if not data:
                            continue
                        db.add(Distribution(
                            fund_id=fund_id,
                            distribution_date=data.get("date") or datetime.utcnow().date(),
                            distribution_type=data.get("type"),
                            is_recallable=False,
                            amount=data.get("amount") or Decimal("0"),
                            description=data.get("description")
                        ))
                    db.commit()
                elif ttype == "adjustments":
                    for r in rows:
                        data = self._extract_row_data(r, colmap)
                        if not data:
                            continue
                        db.add(Adjustment(
                            fund_id=fund_id,
                            adjustment_date=data.get("date") or datetime.utcnow().date(),
                            adjustment_type=data.get("type"),
                            category=None,
                            amount=data.get("amount") or Decimal("0"),
                            is_contribution_adjustment=False,
                            description=data.get("description")
                        ))
                    db.commit()
            except Exception:
                # Skip table on error to avoid breaking pipeline
                db.rollback()

    def _infer_column_indices(self, headers: List[str]) -> Dict[str, int]:
        """Infer likely column indices for date, amount, type, description."""
        idxs: Dict[str, int] = {}
        for i, h in enumerate(headers):
            hl = h.lower()
            if any(k in hl for k in ["date", "tgl", "call date", "distribution date", "adjustment date"]):
                idxs.setdefault("date", i)
            if any(k in hl for k in ["amount", "amt", "nominal", "usd", "$", "value"]):
                idxs.setdefault("amount", i)
            if any(k in hl for k in ["type", "category", "class", "desc", "description"]):
                if "type" not in idxs:
                    idxs["type"] = i
                idxs.setdefault("description", i)
        return idxs

    def _extract_row_data(self, row: List[str], colmap: Dict[str, int]) -> Dict[str, Any] | None:
        """Extract row data using colmap, with basic parsing for date and amount."""
        if not row:
            return None
        data: Dict[str, Any] = {}
        # Date
        di = colmap.get("date")
        if di is not None and di < len(row):
            data["date"] = self._parse_date(row[di])
        # Amount
        ai = colmap.get("amount")
        if ai is not None and ai < len(row):
            data["amount"] = self._parse_amount(row[ai])
        # Type / Description
        ti = colmap.get("type")
        if ti is not None and ti < len(row):
            data["type"] = (row[ti] or "").strip() or None
        di = colmap.get("description")
        if di is not None and di < len(row):
            data["description"] = (row[di] or "").strip() or None

        # Validation & cleaning rules
        # - Require at least amount or a non-empty type/description
        has_signal = (
            data.get("amount") is not None or
            (data.get("type") and len(data.get("type")) > 0) or
            (data.get("description") and len(data.get("description")) > 0)
        )
        if not has_signal:
            return None

        # Truncate overly long description to avoid bloating
        if data.get("description") and len(data["description"]) > 1000:
            data["description"] = data["description"][:1000]

        return data

    def _parse_date(self, s: str) -> date | None:
        s = (s or "").strip()
        if not s:
            return None
        # Try multiple common formats
        fmts = ["%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y", "%b %d, %Y", "%d %b %Y"]
        for f in fmts:
            try:
                return datetime.strptime(s, f).date()
            except Exception:
                continue
        # Fallback: extract digits and try YYYYMMDD
        digits = re.sub(r"[^0-9]", "", s)
        if len(digits) == 8:
            try:
                return datetime.strptime(digits, "%Y%m%d").date()
            except Exception:
                pass
        return None

    def _parse_amount(self, s: str) -> Decimal | None:
        s = (s or "").strip()
        if not s:
            return None
        # Remove currency symbols and thousand separators
        # Handle parentheses for negative values e.g. ($1,234.56)
        negative = False
        if re.search(r"\(.*\)", s):
            negative = True
        cleaned = re.sub(r"[^0-9.,-]", "", s)
        # Normalize separators intelligently:
        # - If both comma and dot present: assume comma thousands, dot decimals -> remove commas
        # - If only comma present: decide based on last group length
        if "," in cleaned and "." in cleaned:
            cleaned = cleaned.replace(",", "")
        elif "," in cleaned and "." not in cleaned:
            # Determine if comma is decimal separator by checking digits after last comma
            last_comma_idx = cleaned.rfind(",")
            fractional_part = cleaned[last_comma_idx + 1:]
            if 1 <= len(fractional_part) <= 2:
                cleaned = cleaned.replace(",", ".")
            else:
                cleaned = cleaned.replace(",", "")
        try:
            val = Decimal(cleaned)
            return -val if negative and val is not None else val
        except Exception:
            # Fallback: strip non-digits and parse
            digits = re.sub(r"[^0-9-]", "", cleaned)
            try:
                val = Decimal(digits)
                return -val if negative and val is not None else val
            except Exception:
                return None
