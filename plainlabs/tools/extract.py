"""Deterministic text extraction. Parsing accuracy is a safety input, so this
stays plain code (pypdf / tesseract), never the model reading an image."""
from pathlib import Path


def extract_text(path: str | Path) -> str:
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return _from_pdf(path)
    if suffix in {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}:
        return _from_image(path)
    if suffix in {".txt", ".text"}:
        return path.read_text()
    raise ValueError(f"Unsupported file type: {suffix}")


def _from_pdf(path: Path) -> str:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def _from_image(path: Path) -> str:
    import pytesseract
    from PIL import Image

    return pytesseract.image_to_string(Image.open(path))
