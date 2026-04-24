import io
from pathlib import Path
from backend.core.logging import get_logger

logger = get_logger(__name__)


def extract_text_via_ocr(file_path: str) -> str:
    try:
        import pytesseract
        from PIL import Image
        import fitz  # PyMuPDF
    except ImportError as e:
        raise ImportError(f"OCR dependencies missing: {e}. Install pytesseract, Pillow, PyMuPDF.")

    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    text_parts: list[str] = []

    if path.suffix.lower() == ".pdf":
        doc = fitz.open(str(path))
        for page_num in range(len(doc)):
            page = doc[page_num]
            pix = page.get_pixmap(dpi=300)
            img_bytes = pix.tobytes("png")
            image = Image.open(io.BytesIO(img_bytes))
            page_text = pytesseract.image_to_string(image, config="--psm 6")
            text_parts.append(page_text)
            logger.debug(f"OCR page {page_num + 1}: extracted {len(page_text)} chars")
        doc.close()
    else:
        image = Image.open(str(path))
        text_parts.append(pytesseract.image_to_string(image, config="--psm 6"))

    full_text = "\n".join(text_parts).strip()
    logger.info(f"OCR extracted {len(full_text)} chars from {path.name}")
    return full_text


def is_scanned_pdf(file_path: str) -> bool:
    try:
        import fitz
        doc = fitz.open(file_path)
        total_text = ""
        for page in doc:
            total_text += page.get_text()
        doc.close()
        return len(total_text.strip()) < 100
    except Exception as e:
        logger.warning(f"Could not determine if PDF is scanned: {e}")
        return False
