"""
Module C — screenshot OCR extension (Iteration 7).

Wires image uploads into the existing text pipeline:

    image file -> extract_text_from_image() -> analyze_message()

Requires the `pytesseract` Python wrapper AND the Tesseract OCR engine
binary (e.g. `choco install tesseract`, `apt install tesseract-ocr`,
`brew install tesseract`). Both are optional at import time — they are only
needed when OCR actually runs, so text-only flows keep working without them.

IMPORTANT — failure contract: OCR on blurry/low-contrast screenshots often
returns empty or garbled text. `analyze_image()` NEVER reports such cases as
low-risk. Callers MUST check `ocr_status` before interpreting `score`:
  - "ok"                -> OCR text was usable; score/signature are meaningful.
  - "insufficient_text" -> readable text too short/garbled; NOT a clean verdict.
  - "ocr_unavailable"   -> pytesseract/Tesseract missing or crashed; NOT clean.
  - "invalid_image"     -> file missing/unreadable; NOT clean.
"""

import io
import os
import re

try:
    from ml.predict_module_c import analyze_message
except ImportError:  # fallback for direct script execution
    from predict_module_c import analyze_message

# Heuristic for "enough text to analyze": guards against blurry/garbled OCR
# output being misreported as a low-risk (clean) message.
MIN_OCR_TEXT_CHARS = 20
MIN_OCR_WORDS = 3

CLEARER_SCREENSHOT_HINT = (
    "Could not extract enough text from the screenshot — "
    "please try a clearer screenshot (good lighting, hold steady, "
    "crop tightly to the chat text). You can also paste the chat "
    "text directly for analysis."
)


def _load_image(image_file):
    """Open image_file (path, bytes, file-like, or PIL Image) -> PIL Image."""
    # Local import keeps Pillow optional at module import time.
    try:
        from PIL import Image
    except ImportError as e:
        raise RuntimeError(
            "Pillow is required for screenshot analysis but is not installed "
            "(pip install pillow)."
        ) from e

    if isinstance(image_file, Image.Image):
        return image_file
    if isinstance(image_file, (bytes, bytearray)):
        return Image.open(io.BytesIO(bytes(image_file)))
    if hasattr(image_file, "read"):
        # File-like object (e.g. FastAPI UploadFile.file).
        try:
            image_file.seek(0)
        except Exception:
            pass
        return Image.open(io.BytesIO(image_file.read()))
    if isinstance(image_file, (str, os.PathLike)):
        path = os.fspath(image_file)
        if not os.path.exists(path):
            raise FileNotFoundError(f"Screenshot image not found: {path}")
        return Image.open(path)
    raise TypeError(
        "image_file must be a file path, bytes, file-like object, "
        f"or PIL Image — got {type(image_file).__name__}"
    )


def extract_text_from_image(image_file) -> str:
    """
    Run Tesseract OCR on an uploaded screenshot and return raw text.

    Parameters:
    -----------
    image_file : str | os.PathLike | bytes | file-like | PIL.Image

    Returns:
    --------
    str: OCR-extracted text (may be empty for blank/unreadable images).

    Raises:
    -------
    RuntimeError: pytesseract/Tesseract missing or OCR engine failed.
    FileNotFoundError: path input does not exist.
    TypeError / OSError: unsupported input or unreadable image data.
    """
    # Validate path inputs BEFORE touching the OCR stack so missing files
    # are always reported as invalid_image, even where OCR is unavailable.
    if isinstance(image_file, (str, os.PathLike)) and not os.path.exists(
        os.fspath(image_file)
    ):
        raise FileNotFoundError(f"Screenshot image not found: {image_file}")

    # Local import keeps the wrapper optional until OCR is actually used.
    try:
        import pytesseract
    except ImportError as e:
        raise RuntimeError(
            "pytesseract is required for screenshot analysis but is not "
            "installed (pip install pytesseract) and the Tesseract OCR "
            "engine binary must also be installed."
        ) from e

    image = _load_image(image_file)

    # MVP preprocessing: grayscale. (Contrast/deskew upgrades are future work.)
    if image.mode != "L":
        image = image.convert("L")

    try:
        text = pytesseract.image_to_string(image)
    except Exception as e:
        raise RuntimeError(
            "OCR engine failed — Tesseract binary may be missing or the "
            f"image may be unreadable ({e})."
        ) from e

    return (text or "").strip()


def has_enough_text(text: str) -> bool:
    """Heuristic: is the OCR output substantial enough to analyze safely?"""
    if not text:
        return False
    stripped = text.strip()
    if len(stripped) < MIN_OCR_TEXT_CHARS:
        return False
    words = [w for w in re.split(r"\s+", stripped) if re.search(r"[A-Za-z0-9]", w)]
    return len(words) >= MIN_OCR_WORDS


def _failure_result(reason: str, ocr_status: str, ocr_text: str = "") -> dict:
    """Failure envelope — explicitly NOT a low-risk verdict (see ocr_status)."""
    return {
        "score": 0.0,
        "signature": "none",
        "reasons": [reason],
        "ml_status": "not_applicable (no analyzable text extracted)",
        "ocr_text": ocr_text,
        "ocr_status": ocr_status,
    }


def analyze_image(image_file, fetch_live_page: bool = False) -> dict:
    """
    Full screenshot pipeline: OCR -> analyze_message().

    Returns analyze_message()'s dict plus:
      - "ocr_text": str (raw OCR output, "" on failure)
      - "ocr_status": "ok" | "insufficient_text" | "ocr_unavailable" | "invalid_image"

    When OCR yields too little/garbled text, returns the "clearer screenshot"
    response instead of a (false) low-risk score.
    """
    try:
        ocr_text = extract_text_from_image(image_file)
    except (FileNotFoundError, TypeError, OSError) as e:
        return _failure_result(
            f"Could not read the uploaded image ({e}). "
            "Please upload a valid PNG/JPG chat screenshot.",
            ocr_status="invalid_image",
        )
    except RuntimeError as e:
        return _failure_result(
            f"OCR unavailable ({e}). As a fallback, please paste the chat "
            "text directly for analysis.",
            ocr_status="ocr_unavailable",
        )

    if not has_enough_text(ocr_text):
        return _failure_result(
            CLEARER_SCREENSHOT_HINT,
            ocr_status="insufficient_text",
            ocr_text=ocr_text,
        )

    result = analyze_message(ocr_text, fetch_live_page=fetch_live_page)
    result["ocr_text"] = ocr_text
    result["ocr_status"] = "ok"
    return result


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m ml.ocr_module_c <screenshot.png>")
    else:
        import json

        print(json.dumps(analyze_image(sys.argv[1]), indent=2))
