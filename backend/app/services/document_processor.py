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
from app.core.config import settings
from app.services.table_parser import TableParser
from app.services.vector_store import VectorStore

class DocumentProcessor:
    """Process PDF documents and extract structured data"""
    
    def __init__(self):
        self.table_parser = TableParser()
    
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
        }
        try:
            vector_store = VectorStore()
            text_content: List[Dict[str, Any]] = []

            with pdfplumber.open(file_path) as pdf:
                stats["pages"] = len(pdf.pages)
                for idx, page in enumerate(pdf.pages, start=1):
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
