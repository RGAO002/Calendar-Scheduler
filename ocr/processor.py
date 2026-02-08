"""OCR processing pipeline using PyMuPDF and EasyOCR."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path


@dataclass
class OCRResult:
    text: str
    confidence: float
    method: str  # "pymupdf" or "easyocr"


class OCRProcessor:
    """Process documents with OCR.

    Strategy:
    1. For PDFs: Try PyMuPDF text extraction first (handles text-based PDFs)
    2. If no text found: Convert pages to images and run EasyOCR
    3. For images: Run EasyOCR directly
    """

    def __init__(self):
        self._easyocr_reader = None

    def _get_easyocr_reader(self):
        """Lazy-load EasyOCR reader."""
        if self._easyocr_reader is None:
            import easyocr
            self._easyocr_reader = easyocr.Reader(["en"], gpu=False, verbose=False)
        return self._easyocr_reader

    def process(self, file_bytes: bytes, filename: str) -> OCRResult:
        """Process a file and extract text.

        Args:
            file_bytes: Raw file bytes
            filename: Original filename for format detection

        Returns: OCRResult with extracted text, confidence, and method used
        """
        ext = Path(filename).suffix.lower()

        if ext == ".pdf":
            return self._process_pdf(file_bytes)
        elif ext in (".png", ".jpg", ".jpeg", ".tiff", ".tif"):
            return self._process_image(file_bytes)
        else:
            raise ValueError(f"Unsupported file format: {ext}")

    def _process_pdf(self, pdf_bytes: bytes) -> OCRResult:
        """Process a PDF file."""
        import fitz  # PyMuPDF

        doc = fitz.open(stream=pdf_bytes, filetype="pdf")

        # Step 1: Try text extraction
        text_parts = []
        for page in doc:
            page_text = page.get_text().strip()
            if page_text:
                text_parts.append(page_text)

        full_text = "\n\n".join(text_parts)

        if len(full_text.strip()) > 50:
            doc.close()
            return OCRResult(
                text=full_text,
                confidence=99.0,
                method="pymupdf",
            )

        # Step 2: PDF is image-based - convert to images and OCR
        images = []
        for page in doc:
            pix = page.get_pixmap(dpi=300)
            images.append(pix.tobytes("png"))
        doc.close()

        if not images:
            return OCRResult(text="", confidence=0.0, method="easyocr")

        return self._ocr_images(images)

    def _process_image(self, image_bytes: bytes) -> OCRResult:
        """Process a single image file."""
        return self._ocr_images([image_bytes])

    def _ocr_images(self, image_list: list[bytes]) -> OCRResult:
        """Run EasyOCR on a list of image bytes."""
        reader = self._get_easyocr_reader()

        all_text = []
        all_confidences = []

        for img_bytes in image_list:
            results = reader.readtext(img_bytes)
            page_texts = []
            for (bbox, text, conf) in results:
                page_texts.append(text)
                all_confidences.append(conf)

            all_text.append(" ".join(page_texts))

        full_text = "\n\n".join(all_text)
        avg_confidence = (
            sum(all_confidences) / len(all_confidences) * 100
            if all_confidences
            else 0.0
        )

        return OCRResult(
            text=full_text,
            confidence=round(avg_confidence, 1),
            method="easyocr",
        )
