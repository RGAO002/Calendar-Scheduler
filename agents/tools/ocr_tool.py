"""OCR tool for agent use."""
from __future__ import annotations
import json
import io
import uuid


def run_ocr(file_bytes: bytes, filename: str, store: bool = True) -> str:
    """Run OCR on a document and optionally store results.

    Args:
        file_bytes: Raw file bytes
        filename: Original filename
        store: Whether to store in MinIO and record in Supabase

    Returns: JSON string with extracted text and metadata
    """
    from ocr.processor import OCRProcessor

    processor = OCRProcessor()
    result = processor.process(file_bytes, filename)

    output = {
        "text": result.text,
        "confidence": result.confidence,
        "method": result.method,
        "filename": filename,
        "text_length": len(result.text),
    }

    if store:
        try:
            from services.minio_client import get_minio, ensure_bucket
            from db.queries import insert_ocr_document

            # Upload original to MinIO
            ensure_bucket("evlin-uploads")
            obj_key = f"ocr/{uuid.uuid4()}/{filename}"
            get_minio().put_object(
                "evlin-uploads", obj_key,
                io.BytesIO(file_bytes), len(file_bytes),
            )

            # Record in Supabase
            doc = insert_ocr_document({
                "original_filename": filename,
                "minio_key": obj_key,
                "extracted_text": result.text,
                "confidence": result.confidence,
                "status": "completed",
            })
            output["stored"] = True
            output["document_id"] = doc.get("id")
        except Exception as e:
            output["stored"] = False
            output["store_error"] = str(e)

    return json.dumps(output, indent=2)
