"""TrueIntent FastAPI backend — Modules A-D wiring.

Run from the repo (matches Makefile / run-backend scripts):
    cd backend && ..\\venv\\Scripts\\uvicorn app.main:app --port 8000
"""

import os
import sys
import urllib.parse

# Make the repo-root `ml` package importable whether uvicorn starts in
# `backend/` (Makefile) or the repo root, and likewise for pytest.
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from backend.app.schemas import (
    CombinedRequest,
    CombinedResponse,
    MessageCheckResponse,
    TransactionCheckRequest,
    TransactionCheckResponse,
    UrlCheckRequest,
    UrlCheckResponse,
)
from ml.ocr_module_c import analyze_image
from ml.predict_module_a import predict_module_a
from ml.predict_module_b import check_url
from ml.predict_module_c import analyze_message
from ml.predict_module_d import compute_unified_score

app = FastAPI(title="TrueIntent API", version="0.1.0")

# CORS: allow any local frontend port (Vite :5173, CRA :3000, etc.).
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ALLOWED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/webp", "image/bmp"}
MAX_IMAGE_BYTES = 10 * 1024 * 1024  # 10 MB


def _normalize_url_or_400(url: str) -> str:
    """Reject malformed URLs with a clear 422 (never a stack trace)."""
    candidate = (url or "").strip()
    if not candidate:
        raise HTTPException(status_code=422, detail="url must be a non-empty string.")
    if any(ch.isspace() for ch in candidate):
        raise HTTPException(status_code=422, detail=f"Invalid URL (contains whitespace): '{url}'.")
    parsed = urllib.parse.urlparse(
        candidate if "://" in candidate else "http://" + candidate
    )
    host = (parsed.hostname or "").strip()
    if not host or ("." not in host and host != "localhost"):
        raise HTTPException(
            status_code=422,
            detail=f"Invalid URL (could not parse a domain from '{url}'). "
            "Expected something like 'https://example.com/login'.",
        )
    return candidate


@app.get("/")
def root():
    return {"status": "ok", "service": "TrueIntent API", "version": "0.1.0"}


@app.get("/health")
def health():
    return {"status": "ok"}


# -----------------------------------------------------------------------------
# Module B — URL safety
# -----------------------------------------------------------------------------
@app.post("/check-url", response_model=UrlCheckResponse)
def post_check_url(body: UrlCheckRequest):
    url = _normalize_url_or_400(body.url)
    try:
        # Offline-safe: skip live page fetching (deterministic, no egress).
        result = check_url(url, fetch_live_page=False)
    except Exception:
        raise HTTPException(
            status_code=500, detail="URL analysis failed unexpectedly. Please retry."
        )
    return UrlCheckResponse(
        score=result["score"], reasons=result["reasons"],
        ml_status=result.get("ml_status", ""),
    )


# -----------------------------------------------------------------------------
# Module C — Message text or screenshot image (exactly one)
# -----------------------------------------------------------------------------
@app.post("/check-message", response_model=MessageCheckResponse)
async def post_check_message(
    text: str | None = Form(default=None),
    image: UploadFile | None = File(default=None),
):
    has_text = text is not None and text.strip() != ""
    if has_text and image is not None:
        raise HTTPException(
            status_code=400,
            detail="Provide either 'text' or 'image', not both.",
        )
    if not has_text and image is None:
        raise HTTPException(
            status_code=400,
            detail="Provide either message 'text' (form field) or an 'image' upload.",
        )

    if image is not None:
        if image.content_type not in ALLOWED_IMAGE_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported image type '{image.content_type}'. "
                "Upload a PNG or JPEG chat screenshot.",
            )
        try:
            content = await image.read()
        except Exception:
            raise HTTPException(status_code=400, detail="Could not read the uploaded file.")
        if not content:
            raise HTTPException(status_code=400, detail="Uploaded image file is empty.")
        if len(content) > MAX_IMAGE_BYTES:
            raise HTTPException(
                status_code=400,
                detail="Uploaded image exceeds the 10 MB size limit.",
            )
        try:
            result = analyze_image(content, fetch_live_page=False)
        except Exception:
            raise HTTPException(
                status_code=500, detail="Screenshot analysis failed unexpectedly. Please retry."
            )
        status = result.get("ocr_status", "")
        if status == "invalid_image":
            raise HTTPException(
                status_code=400,
                detail="Unreadable image file. Please upload a valid PNG/JPEG chat screenshot.",
            )
        if status == "ocr_unavailable":
            raise HTTPException(
                status_code=503,
                detail="OCR engine unavailable on the server. "
                "As a fallback, paste the chat text directly in 'text'.",
            )
        return MessageCheckResponse(
            score=result["score"], signature=result["signature"],
            reasons=result["reasons"], ml_status=result.get("ml_status", ""),
            ocr_text=result.get("ocr_text"), ocr_status=status,
        )

    # Text flow.
    try:
        result = analyze_message(text.strip(), fetch_live_page=False)
    except Exception:
        raise HTTPException(
            status_code=500, detail="Message analysis failed unexpectedly. Please retry."
        )
    result["text"] = text.strip()
    return MessageCheckResponse(
        score=result["score"], signature=result["signature"],
        reasons=result["reasons"], ml_status=result.get("ml_status", ""),
    )


# -----------------------------------------------------------------------------
# Module A — Transaction + call state
# -----------------------------------------------------------------------------
@app.post("/check-transaction", response_model=TransactionCheckResponse)
def post_check_transaction(body: TransactionCheckRequest):
    payload = body.model_dump(exclude_none=True)
    try:
        score = predict_module_a(payload)
    except FileNotFoundError:
        raise HTTPException(
            status_code=503,
            detail="Transaction model artifact missing on the server. "
            "Run ml/train_module_a.py first.",
        )
    except Exception:
        raise HTTPException(
            status_code=500, detail="Transaction analysis failed unexpectedly. Please retry."
        )
    return TransactionCheckResponse(score=float(score))


# -----------------------------------------------------------------------------
# Module D — Unified result over any subset of inputs
# -----------------------------------------------------------------------------
@app.post("/check-combined", response_model=CombinedResponse)
def post_check_combined(body: CombinedRequest):
    mod_a = mod_b = mod_c = None
    modules: dict = {}

    if body.transaction is not None:
        payload = body.transaction.model_dump(exclude_none=True)
        try:
            score_a = float(predict_module_a(payload))
        except FileNotFoundError:
            raise HTTPException(
                status_code=503,
                detail="Transaction model artifact missing on the server.",
            )
        except Exception:
            raise HTTPException(status_code=500, detail="Transaction analysis failed.")
        mod_a = {"score": score_a, "transaction": payload}
        modules["module_a"] = {"score": score_a}

    if body.url is not None and body.url.strip() != "":
        url = _normalize_url_or_400(body.url)
        try:
            mod_b = check_url(url, fetch_live_page=False)
        except Exception:
            raise HTTPException(status_code=500, detail="URL analysis failed.")
        modules["module_b"] = mod_b

    if body.text is not None and body.text.strip() != "":
        try:
            mod_c = analyze_message(body.text.strip(), fetch_live_page=False)
        except Exception:
            raise HTTPException(status_code=500, detail="Message analysis failed.")
        mod_c["text"] = body.text.strip()  # context for Module D token attribution
        modules["module_c"] = {k: v for k, v in mod_c.items() if k != "text"}

    try:
        unified = compute_unified_score(mod_a, mod_b, mod_c)
    except (ValueError, TypeError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="Unified scoring failed.")

    return CombinedResponse(
        tier=unified["tier"], score=unified["score"],
        explanation=unified["explanation"],
        details=unified.get("details", {}), modules=modules,
    )
