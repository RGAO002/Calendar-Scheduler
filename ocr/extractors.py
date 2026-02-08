"""Specialized text extractors for different document formats."""
from __future__ import annotations
from pathlib import Path


def extract_pdf_metadata(pdf_bytes: bytes) -> dict:
    """Extract metadata from a PDF file."""
    import fitz

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    metadata = doc.metadata or {}
    info = {
        "title": metadata.get("title", ""),
        "author": metadata.get("author", ""),
        "subject": metadata.get("subject", ""),
        "page_count": doc.page_count,
        "is_encrypted": doc.is_encrypted,
    }
    doc.close()
    return info


def extract_tables_from_pdf(pdf_bytes: bytes) -> list[list[list[str]]]:
    """Extract tables from a PDF using PyMuPDF."""
    import fitz

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    all_tables = []

    for page in doc:
        tabs = page.find_tables()
        for tab in tabs:
            table_data = tab.extract()
            if table_data:
                all_tables.append(table_data)

    doc.close()
    return all_tables


def extract_images_from_pdf(pdf_bytes: bytes) -> list[bytes]:
    """Extract embedded images from a PDF."""
    import fitz

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    images = []

    for page in doc:
        for img_info in page.get_images(full=True):
            xref = img_info[0]
            base_image = doc.extract_image(xref)
            if base_image:
                images.append(base_image["image"])

    doc.close()
    return images
