import io
from pypdf import PdfReader
from typing import Optional


def extract_pdf_text(pdf_bytes: bytes, filename: str = "") -> dict:
    """
    Extract text from a PDF. Falls back gracefully if text extraction fails.
    Returns extracted text and page count.
    """
    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        pages_text = []
        for i, page in enumerate(reader.pages):
            page_text = page.extract_text() or ""
            pages_text.append(page_text.strip())

        full_text = "\n\n".join(f"[Page {i+1}]\n{t}" for i, t in enumerate(pages_text) if t)

        if not full_text.strip():
            return {
                "success": True,
                "text": "",
                "page_count": len(reader.pages),
                "filename": filename,
                "note": "PDF appears to be scanned/image-based. OCR would be needed for text extraction.",
            }

        return {
            "success": True,
            "text": full_text,
            "page_count": len(reader.pages),
            "filename": filename,
        }
    except Exception as e:
        return {
            "success": False,
            "text": "",
            "page_count": 0,
            "filename": filename,
            "error": str(e),
        }
