"""
Celery tasks related to document processing
"""
from typing import Dict, Any
from app.celery_app import celery_app
from app.db.session import SessionLocal
from app.models.document import Document
from app.models.fund import Fund  # ensure mapper initialization
from app.models.transaction import CapitalCall, Distribution, Adjustment  # ensure mapper initialization
from app.services.document_processor import DocumentProcessor


@celery_app.task(name="app.tasks.process_document")
def process_document_task(document_id: int, file_path: str, fund_id: int) -> Dict[str, Any]:
    """Process document asynchronously via Celery.

    Returns minimal result dict with status and optional error.
    """
    db = SessionLocal()
    try:
        # Set status to processing
        document = db.query(Document).filter(Document.id == document_id).first()
        if document:
            document.parsing_status = "processing"
            db.commit()

        # Run processing
        processor = DocumentProcessor(db)
        # DocumentProcessor.process_document is async; run synchronously via event loop wrapper
        import asyncio
        result = asyncio.run(processor.process_document(file_path, document_id, fund_id))

        # Update status
        if document:
            document.parsing_status = result.get("status", "failed")
            if result.get("status") == "failed":
                document.error_message = result.get("error")
            db.commit()

        return {"status": result.get("status", "failed"), "error": result.get("error")}
    except Exception as e:
        # Mark failed
        document = db.query(Document).filter(Document.id == document_id).first()
        if document:
            document.parsing_status = "failed"
            document.error_message = str(e)
            db.commit()
        return {"status": "failed", "error": str(e)}
    finally:
        db.close()