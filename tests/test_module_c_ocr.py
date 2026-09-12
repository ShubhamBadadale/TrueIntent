"""Module C screenshot/OCR tests.

NOTE ON TEST IMAGES: no real chat screenshots exist in the repo yet, so the
evidence-based test below (`test_user_provided_screenshot`) SKIPS until 1-2
real sample screenshots are placed in `data/raw/screenshots/`. The user
explicitly approved a clearly-labeled SYNTHETIC fixture
(`tests/data/synthetic_chat_fear_authority.png`, header-stamped "SYNTHETIC
TEST FIXTURE - NOT REAL EVIDENCE") for the end-to-end OCR test — it is never
presented as real evidence. All other tests use a blank control image and
mocked OCR output only.
"""

import glob
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest

PIL = pytest.importorskip("PIL", reason="Pillow required for screenshot tests")

from ml import ocr_module_c
from ml.ocr_module_c import analyze_image, has_enough_text


def _make_blank_png(path: str, size=(400, 200)) -> str:
    """Blank white control image (contains no text by construction)."""
    from PIL import Image

    Image.new("RGB", size, color="white").save(path)
    return path


def test_blank_image_does_not_return_false_low_risk(tmp_path):
    """Blurry/blank input must yield the clearer-screenshot response, not 'safe'."""
    img = _make_blank_png(str(tmp_path / "blank.png"))

    res = analyze_image(img, fetch_live_page=False)

    assert res["signature"] == "none"
    assert res["score"] == 0.0
    # Must NOT look like a clean verdict: ocr_status explains why.
    assert res["ocr_status"] in ("insufficient_text", "ocr_unavailable", "invalid_image")
    assert any("clearer screenshot" in r.lower() or "ocr" in r.lower() for r in res["reasons"]), (
        f"Expected clearer-screenshot/OCR guidance, got {res['reasons']}"
    )


def test_mocked_scam_ocr_text_flows_into_analyze_message(monkeypatch):
    """OCR output becomes the analyze_message() input (mocked OCR, no image needed)."""
    monkeypatch.setattr(
        ocr_module_c,
        "extract_text_from_image",
        lambda _img: (
            "You are under investigation for money laundering. "
            "Stay on the line and do not disconnect."
        ),
    )

    res = analyze_image("dummy.png", fetch_live_page=False)

    assert res["ocr_status"] == "ok"
    assert "under investigation" in res["ocr_text"].lower()
    assert res["signature"] == "fear_authority", f"Got {res}"
    assert res["score"] >= 0.5, f"Got {res}"


def test_mocked_garbled_ocr_returns_insufficient_text(monkeypatch):
    """Garbled one-char OCR noise must trigger the clearer-screenshot response."""
    monkeypatch.setattr(ocr_module_c, "extract_text_from_image", lambda _img: "x | . -")

    res = analyze_image("dummy.png", fetch_live_page=False)

    assert res["ocr_status"] == "insufficient_text"
    assert res["score"] == 0.0
    assert res["signature"] == "none"
    assert any("clearer screenshot" in r.lower() for r in res["reasons"])


def test_missing_file_returns_invalid_image():
    """Nonexistent path must not crash; returns invalid_image (not low-risk)."""
    res = analyze_image("does_not_exist_12345.png", fetch_live_page=False)

    assert res["ocr_status"] == "invalid_image"
    assert res["score"] == 0.0
    assert isinstance(res["reasons"], list) and len(res["reasons"]) > 0


def test_has_enough_text_heuristic():
    assert has_enough_text("You are under investigation, stay on the line please.") is True
    assert has_enough_text("") is False
    assert has_enough_text("   ") is False
    assert has_enough_text("x | . -") is False
    assert has_enough_text("hi ok") is False


def test_user_provided_screenshot():
    """Real evidence test — SKIPPED until sample screenshots are provided.

    To activate: place 1-2 real chat screenshots in `data/raw/screenshots/`
    (resolved relative to the repo root; gitignored, no PII committed).
    See test module docstring.
    """
    _root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    patterns = [
        os.path.join(_root, "data", "raw", "screenshots", "*.png"),
        os.path.join(_root, "data", "raw", "screenshots", "*.jpg"),
        os.path.join(_root, "data", "raw", "screenshots", "*.jpeg"),
    ]
    found = [p for pat in patterns for p in glob.glob(pat)]
    if not found:
        pytest.skip(
            "No sample screenshots in data/raw/screenshots/ yet — "
            "provide 1-2 real chat screenshots to activate this test."
        )
    for path in found:
        res = analyze_image(path, fetch_live_page=False)
        assert set(("score", "signature", "reasons", "ocr_text", "ocr_status")) <= set(res)
        assert isinstance(res["score"], float) and 0.0 <= res["score"] <= 1.0
        assert res["signature"] in ("fear_authority", "greed_opportunity", "none")


def test_synthetic_fixture_end_to_end():
    """End-to-end OCR on the user-approved SYNTHETIC fixture (NOT real evidence).

    Fixture `tests/data/synthetic_chat_fear_authority.png` is programmatically
    generated, filename- and header-labeled SYNTHETIC. Skips where the
    Tesseract engine binary / pytesseract is unavailable.
    """
    try:
        import shutil

        import pytesseract

        if shutil.which("tesseract") is None:
            pytesseract.get_tesseract_version()  # raises if binary unreachable
    except Exception:
        pytest.skip("Tesseract OCR engine binary / pytesseract not available.")

    path = os.path.join(
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..")),
        "tests", "data", "synthetic_chat_fear_authority.png",
    )
    assert os.path.exists(path), "Synthetic fixture image missing."

    res = analyze_image(path, fetch_live_page=False)

    assert res["ocr_status"] == "ok", f"OCR failed on clean fixture: {res}"
    assert res["signature"] == "fear_authority", f"Got {res}"
    assert res["score"] >= 0.5, f"Got {res}"
