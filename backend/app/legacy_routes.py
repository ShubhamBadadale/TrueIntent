"""Legacy ``/check-*`` routes: the compatibility contract.

These endpoints return the original flat response bodies and FastAPI's
``{"detail": ...}`` error shape, byte for byte, so the React portal, the
Android companion and every existing client keep working unchanged. They are
thin adapters: validation and analysis live in :mod:`backend.app.services`,
and each failure below is the same :class:`~backend.app.errors.AppError` the
v1 routes render as an envelope.

New clients should use ``/api/v1/*``. These routes are frozen, not extended.
"""
from __future__ import annotations

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from starlette.concurrency import run_in_threadpool

from backend.app import services
from backend.app.errors import AppError, PayloadTooLarge
from backend.app.schemas import (
    CombinedRequest,
    CombinedResponse,
    MessageCheckResponse,
    TransactionCheckRequest,
    TransactionCheckResponse,
    UrlCheckRequest,
    UrlCheckResponse,
)
from backend.app.validation import IMAGE_SIGNATURES, read_upload_bounded

router = APIRouter(tags=['legacy'])


def _legacy_error(exc: AppError) -> HTTPException:
    """Render an AppError exactly as this generation has always done."""
    return HTTPException(status_code=exc.status_code, detail=exc.message)


# -----------------------------------------------------------------------------
# Module B — URL safety
# -----------------------------------------------------------------------------
@router.post('/check-url', response_model=UrlCheckResponse)
def post_check_url(body: UrlCheckRequest):
    try:
        result = services.analyze_url(body.url)
    except AppError as exc:
        raise _legacy_error(exc) from None
    except Exception:
        raise HTTPException(
            status_code=500, detail='URL analysis failed unexpectedly. Please retry.'
        ) from None
    return UrlCheckResponse(
        score=result['score'], reasons=result['reasons'], ml_status=result['ml_status'],
    )


# -----------------------------------------------------------------------------
# Module C — Message text or screenshot image (exactly one)
# -----------------------------------------------------------------------------
@router.post('/check-message', response_model=MessageCheckResponse)
async def post_check_message(
    text: str | None = Form(default=None),
    image: UploadFile | None = File(default=None),
):
    has_text = text is not None and text.strip() != ''
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
        return await _check_message_image(image)

    # Text flow.
    try:
        result = services.require_assessed(services.analyze_text(text.strip()))
    except AppError as exc:
        raise _legacy_error(exc) from None
    except Exception:
        raise HTTPException(
            status_code=500, detail='Message analysis failed unexpectedly. Please retry.'
        ) from None
    return MessageCheckResponse(
        score=result['score'], signature=result['signature'],
        reasons=result['reasons'], ml_status=result['ml_status'],
        intent=result.get('intent'), intent_probabilities=result.get('intent_probabilities', {}),
        rule_evidence=result.get('rule_evidence', []),
        heuristic_evidence=result.get('heuristic_evidence', []),
        text_assessed=result.get('text_assessed', False),
    )


async def _check_message_image(image: UploadFile):
    if image.content_type not in IMAGE_SIGNATURES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported image type '{image.content_type}'. "
            'Upload a PNG or JPEG chat screenshot.',
        )
    try:
        content = await read_upload_bounded(image)
    except PayloadTooLarge as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from None
    except Exception:
        raise HTTPException(status_code=400, detail='Could not read the uploaded file.') from None
    if not content:
        raise HTTPException(status_code=400, detail='Uploaded image file is empty.')
    try:
        result = services.require_image_assessed(
            await run_in_threadpool(
                services.analyze_image_content, content,
                declared_type=image.content_type, filename=image.filename,
            )
        )
    except AppError as exc:
        raise _legacy_error(exc) from None
    except Exception:
        raise HTTPException(
            status_code=500, detail='Screenshot analysis failed unexpectedly. Please retry.'
        ) from None
    return MessageCheckResponse(
        score=result['score'], signature=result['signature'],
        reasons=result['reasons'], ml_status=result.get('ml_status', ''),
        ocr_text=result.get('ocr_text'), ocr_status=result.get('ocr_status'),
        intent=result.get('intent'), intent_probabilities=result.get('intent_probabilities', {}),
        rule_evidence=result.get('rule_evidence', []),
        heuristic_evidence=result.get('heuristic_evidence', []),
        text_assessed=result.get('text_assessed', False),
    )


# -----------------------------------------------------------------------------
# Module A — Transaction + call state
# -----------------------------------------------------------------------------
@router.post('/check-transaction', response_model=TransactionCheckResponse)
def post_check_transaction(body: TransactionCheckRequest):
    try:
        result = services.run_benchmark(body.to_module_a_payload())
    except AppError as exc:
        raise _legacy_error(exc) from None
    except Exception:
        raise HTTPException(
            status_code=500, detail='Transaction analysis failed unexpectedly. Please retry.'
        ) from None
    return TransactionCheckResponse(
        score=result['score'], explanation=result['explanation'],
    )


# -----------------------------------------------------------------------------
# Module D — Unified result over any subset of inputs
# -----------------------------------------------------------------------------
@router.post('/check-combined', response_model=CombinedResponse)
def post_check_combined(body: CombinedRequest):
    if body.transaction is not None:
        raise HTTPException(status_code=422, detail=services.FUSION_DISABLED_MESSAGE)

    try:
        result = services.analyze_combined(
            url=body.url, text=body.text, active_call=body.active_call,
        )
    except AppError as exc:
        # Historical messages preserved: URL/message sub-failures keep the
        # shorter wording this route has always used.
        message = exc.message
        if exc.module == 'module_b' and 'URL analysis failed unexpectedly' in message:
            message = 'URL analysis failed.'
        elif exc.module == 'module_c' and 'Message analysis failed unexpectedly' in message:
            message = 'Message analysis failed.'
        raise HTTPException(status_code=exc.status_code, detail=message) from None
    except Exception:
        raise HTTPException(status_code=500, detail='Unified scoring failed.') from None
    return CombinedResponse(
        tier=result['tier'], risk_level=result['risk_level'], score=result['score'],
        explanation=result['explanation'],
        analyzed_modules=result['analyzed_modules'],
        contributing_modules=result['contributing_modules'],
        unavailable_modules=result['unavailable_modules'],
        evidence=result['evidence'], warnings=result['warnings'],
        fusion_version=result['fusion_version'], limitations=result['limitations'],
        recommended_action=result['recommended_action'],
        details=result.get('details', {}), modules=result.get('modules', {}),
    )
