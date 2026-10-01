"""
Module C — screenshot OCR extension (Iteration 7).

Wires image uploads into the existing text pipeline:

    image file -> extract_text_from_image() -> analyze_message()

Requires the `pytesseract` Python wrapper AND the Tesseract OCR engine
binary (e.g. `choco install tesseract`, `apt install tesseract-ocr`,
`brew install tesseract`). Both are optional at import time — they are only
needed when OCR actually runs, so text-only flows keep working without them.
If the binary is not on PATH, set `TESSERACT_CMD` to its full path (see
`.env.example`).

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
import shutil
import warnings
from pathlib import Path

try:
    from ml.predict_module_c import analyze_message
except ImportError:  # fallback for direct script execution
    from predict_module_c import analyze_message

# Heuristic for "enough text to analyze": guards against blurry/garbled OCR
# output being misreported as a low-risk (clean) message.
MIN_OCR_TEXT_CHARS = 20
MIN_OCR_WORDS = 3

# Tesseract is installed outside PATH on some Windows layouts. Honour the
# conventional TESSERACT_CMD override (see .env.example) instead of guessing.
TESSERACT_CMD_ENV = 'TESSERACT_CMD'
# Extra Tesseract language packs (e.g. "eng+hin"). Read here — not via the
# backend settings module — so standalone ml/ use honours it too.
TESSERACT_LANG_ENV = 'TESSERACT_LANG'
# Read directly for the same reason; backend/app/config.py exposes the same
# variable with the same default, so the two can never disagree.
OCR_TIMEOUT_ENV = 'TRUEINTENT_OCR_TIMEOUT_SECONDS'
DEFAULT_OCR_TIMEOUT_SECONDS = 15


def _ocr_lang() -> str:
    """Tesseract language(s), restricted to the language-code charset.

    Anything else falls back to English rather than reaching the subprocess.
    """
    lang = os.environ.get(TESSERACT_LANG_ENV, 'eng').strip()
    if not lang or re.fullmatch(r'[A-Za-z0-9_+]+', lang) is None:
        return 'eng'
    return lang


def _ocr_timeout_seconds() -> int:
    try:
        raw = (os.environ.get(OCR_TIMEOUT_ENV, '') or '').strip()
        value = int(raw) if raw else DEFAULT_OCR_TIMEOUT_SECONDS
    except ValueError:
        return DEFAULT_OCR_TIMEOUT_SECONDS
    return max(1, min(120, value))


def _default_tesseract_candidates() -> list[Path]:
    """Return common Windows install locations not always added to PATH."""
    candidates: list[Path] = []
    for variable, suffix in (
        ('ProgramFiles', ('Tesseract-OCR', 'tesseract.exe')),
        ('ProgramFiles(x86)', ('Tesseract-OCR', 'tesseract.exe')),
        ('LOCALAPPDATA', ('Programs', 'Tesseract-OCR', 'tesseract.exe')),
    ):
        root = os.environ.get(variable, '').strip()
        if root:
            candidates.append(Path(root).joinpath(*suffix))
    return candidates


def resolve_tesseract_command() -> str | None:
    """Find a usable Tesseract executable.

    An explicit ``TESSERACT_CMD`` remains authoritative. Otherwise check
    ``PATH`` and the standard Windows installer locations. The latter matters
    when the backend is launched from a terminal that was already open while
    Tesseract was installed.
    """
    override = os.environ.get(TESSERACT_CMD_ENV, '').strip()
    if override:
        resolved = shutil.which(override)
        if resolved:
            return resolved
        path = Path(override).expanduser()
        return str(path) if path.is_file() else None

    on_path = shutil.which('tesseract')
    if on_path:
        return on_path
    for path in _default_tesseract_candidates():
        if path.is_file():
            return str(path)
    return None


def configure_tesseract_command():
    """Point pytesseract at the discovered Tesseract executable."""
    command = resolve_tesseract_command()
    if not command:
        return None
    try:
        import pytesseract
    except ImportError:
        return None
    pytesseract.pytesseract.tesseract_cmd = command
    return command

CLEARER_SCREENSHOT_HINT = (
    "Could not extract enough text from the screenshot — "
    "please try a clearer screenshot (good lighting, hold steady, "
    "crop tightly to the chat text). You can also paste the chat "
    "text directly for analysis."
)


def _open_image(image_file):
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


def _load_image(image_file):
    from PIL import Image
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            image = _open_image(image_file)
            if image.width * image.height > 10_000_000:
                raise OSError('Screenshot exceeds 10 million pixels')
            # `is_animated` only exists before load(); `n_frames` after.
            if getattr(image, 'is_animated', False) or getattr(image, 'n_frames', 1) > 1:
                raise OSError('Unsupported image format or animation')
            if image.format not in (None, 'PNG', 'JPEG', 'WEBP', 'BMP'):
                raise OSError('Unsupported image format or animation')
            image.load()
            return image
    except (Image.DecompressionBombWarning, Image.DecompressionBombError) as exc:
        raise OSError('Screenshot dimensions exceed safe limits') from exc


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
    configure_tesseract_command()

    image = _load_image(image_file)

    # MVP preprocessing: grayscale. (Contrast/deskew upgrades are future work.)
    if image.mode != "L":
        image = image.convert("L")

    try:
        text = pytesseract.image_to_string(image, lang=_ocr_lang(),
                                           timeout=_ocr_timeout_seconds())
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
    words = [w for w in re.split(r"\s+", stripped) if any(ch.isalnum() for ch in w)]
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
        "text_assessed": False,
    }


def analyze_image(image_file, fetch_live_page: bool = False) -> dict:
    """
    Full screenshot pipeline: OCR -> analyze_message().

    Returns analyze_message()'s dict plus:
      - "ocr_text": str (raw OCR output, "" on failure)
      - "ocr_status": "ok" | "insufficient_text" | "ocr_unavailable" | "invalid_image"

    When OCR yields too little/garbled text, returns the "clearer screenshot"
    response instead of a (false) low-risk score.

    Failure reasons are fixed, client-safe strings: upstream exception text
    (which may name a local path or binary location) is logged server-side with
    a traceback and never interpolated into the returned reasons.
    """
    import logging

    logger = logging.getLogger(__name__)
    try:
        ocr_text = extract_text_from_image(image_file)
    except (FileNotFoundError, TypeError, OSError) as e:
        logger.warning('Screenshot image could not be read: %s', type(e).__name__)
        logger.debug('Image read failure detail', exc_info=True)
        return _failure_result(
            "Could not read the uploaded image. "
            "Please upload a valid PNG/JPG chat screenshot.",
            ocr_status="invalid_image",
        )
    except RuntimeError as e:
        logger.warning('OCR engine unavailable: %s', type(e).__name__)
        logger.debug('OCR failure detail', exc_info=True)
        return _failure_result(
            "OCR unavailable. As a fallback, please paste the chat "
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
