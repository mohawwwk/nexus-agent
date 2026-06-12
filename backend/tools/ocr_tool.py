import io
from PIL import Image
import pytesseract


def run_ocr(image_bytes: bytes, filename: str = "") -> dict:
    """
    Extract text from an image using Tesseract OCR.
    Returns extracted text and confidence score.
    """
    try:
        image = Image.open(io.BytesIO(image_bytes))

        # Get OCR data with confidence
        data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
        text = pytesseract.image_to_string(image).strip()

        # Calculate average confidence (filter out -1 values)
        confidences = [c for c in data["conf"] if c != -1]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

        return {
            "success": True,
            "text": text,
            "confidence": round(avg_confidence, 1),
            "filename": filename,
        }
    except Exception as e:
        return {
            "success": False,
            "text": "",
            "confidence": 0.0,
            "filename": filename,
            "error": str(e),
        }
