"""Business logic shared by the v1 and legacy routes.

Every public function here is synchronous and blocking (ML inference, OCR
subprocesses); routes offload them with ``run_in_threadpool``. The functions
return the legacy flat response bodies verbatim — the v1 routes wrap the same
dicts in the envelope and add ``risk_index`` — and raise
:class:`~backend.app.errors.AppError` on every deliberate failure, so both
route generations render the same failure the same way.

All service messages are authored strings: they never interpolate an upstream
exception, a filesystem path or an environment value. Unexpected exceptions are
chained (``from exc``) so the server log keeps the traceback while the client
gets a fixed, safe message.
"""
from __future__ import annotations

from backend.app import errors as E
from backend.app.validation import normalize_message, normalize_url, validate_image_upload
from ml.features_module_a import BENCHMARK_NOTICE, ModuleAIncompatibleError, ModuleAUnavailableError
from ml.features_module_d import SAFETY_ACTIONS
from ml.ocr_module_c import analyze_image
from ml.predict_module_a import predict_module_a
from ml.predict_module_b import check_url
from ml.predict_module_c import analyze_message
from ml.predict_module_d import ModuleDUnavailableError, compute_unified_score

#: Refusal message for any transaction-bearing combined request. Kept identical
#: on every route generation so the fusion boundary is unmistakable.
FUSION_DISABLED_MESSAGE = (
    'Transaction fusion is disabled: Module A is now a source-unit '
    'amount-only benchmark, incompatible with the existing combined policy. '
    'Use the Module A benchmark endpoint for benchmark inputs, or submit URL/text '
    'without a transaction.'
)

BENCHMARK_SCOPE = 'ieee_cis_amount_only_benchmark'


def risk_index(score: float) -> int:
    """Render a 0-1 score as an integer 0-100 for mobile clients.

    Explicitly uncalibrated: it rescales the number, it does not calibrate it.
    """
    return max(0, min(100, int(round(float(score) * 100))))


def refuse_transaction_fusion() -> E.TransactionFusionDisabled:
    """The single refusal every combined route uses."""
    return E.TransactionFusionDisabled(FUSION_DISABLED_MESSAGE)


# -----------------------------------------------------------------------------
# Module B — URL safety
# -----------------------------------------------------------------------------
def analyze_url(url_raw: str | None) -> dict:
    """Offline-safe URL analysis. Raises 400/422/500 AppErrors."""
    url = normalize_url(url_raw)
    try:
        # Offline-safe: skip live page fetching (deterministic, no egress).
        result = check_url(url, fetch_live_page=False)
    except Exception as exc:
        raise E.InternalError(
            'URL analysis failed unexpectedly. Please retry.', module='module_b',
        ) from exc
    return {
        'score': result['score'],
        'reasons': result['reasons'],
        'ml_status': result.get('ml_status', ''),
    }


# -----------------------------------------------------------------------------
# Module C — message text
# -----------------------------------------------------------------------------
def require_assessed(result: dict) -> dict:
    """Refuse to present an unassessed text result as a success.

    This runs at every response boundary — not only inside ``analyze_text`` —
    so the guarantee holds however the dict was produced. A ``text_assessed``
    of ``False`` with a zero score must never look like a clean verdict.
    """
    if result.get('text_assessed') is False:
        raise E.MessageNotAssessed('Message model unavailable; text risk was not assessed.')
    return result


def require_image_assessed(result: dict) -> dict:
    """Same guarantee for screenshot results.

    Non-``ok`` OCR statuses (``insufficient_text``, ``invalid_image``,
    ``ocr_unavailable``) carry their own explicit outcomes and only ``ok``
    implies an assessment happened.
    """
    if result.get('ocr_status') == 'ok' and result.get('text_assessed') is False:
        raise E.MessageNotAssessed('Message model unavailable; text risk was not assessed.')
    return result


def analyze_text(text_raw: str | None) -> dict:
    """Message analysis over the full raw Module C result.

    Returns the complete result dict (including ``text_score`` and
    ``embedded_url_score`` for the fusion layer); routes shape it for their
    own response contract. Raises 400/422/503/500 AppErrors.
    """
    text = normalize_message(text_raw)
    try:
        result = analyze_message(text, fetch_live_page=False)
    except Exception as exc:
        raise E.InternalError(
            'Message analysis failed unexpectedly. Please retry.', module='module_c',
        ) from exc
    return require_assessed(result)


# -----------------------------------------------------------------------------
# Module C — screenshot image
# -----------------------------------------------------------------------------
def analyze_image_content(content: bytes, *, declared_type: str | None,
                          filename: str | None) -> dict:
    """Screenshot pipeline over already-read, bounded bytes.

    The caller is responsible for the bounded read (see
    :func:`backend.app.validation.read_upload_bounded`); this function stays
    synchronous so routes can offload the whole blocking unit at once.
    """
    if not content:
        raise E.UnreadableImage('Uploaded image file is empty.')
    validate_image_upload(content, declared_type=declared_type, filename=filename)
    try:
        result = analyze_image(content, fetch_live_page=False)
    except Exception as exc:
        raise E.InternalError(
            'Screenshot analysis failed unexpectedly. Please retry.', module='module_c',
        ) from exc
    status = result.get('ocr_status', '')
    if status == 'invalid_image':
        raise E.UnreadableImage(
            'Unreadable image file. Please upload a valid PNG/JPEG chat screenshot.'
        )
    if status == 'ocr_unavailable':
        raise E.OcrUnavailable(
            'OCR engine unavailable on the server. '
            "As a fallback, paste the chat text directly in 'text'."
        )
    return require_image_assessed(result)


# -----------------------------------------------------------------------------
# Module A — amount-only benchmark
# -----------------------------------------------------------------------------
def run_benchmark(payload: dict) -> dict:
    """Source-unit benchmark scoring. Raises 422/503/500 AppErrors."""
    try:
        score = predict_module_a(payload)
    except ModuleAIncompatibleError as exc:
        raise E.ArtifactIncompatible(str(exc), module='module_a') from None
    except ModuleAUnavailableError as exc:
        raise E.ModelUnavailable(str(exc), module='module_a') from None
    except ValueError as exc:
        if payload.get('amount_unit') != 'ieee_cis_source':
            raise E.AmountUnitRejected(str(exc), module='module_a') from None
        raise E.ValidationFailed(str(exc), module='module_a') from None
    score = float(score)
    if not 0.0 <= score <= 1.0:
        # `predict_module_a` already guards this; the branch exists so a future
        # regression can never emit an out-of-range benchmark score.
        raise E.ModelUnavailable('Module A returned an invalid benchmark score.',
                                 module='module_a')
    return {'score': score, 'analysis_scope': BENCHMARK_SCOPE, 'explanation': BENCHMARK_NOTICE}


# -----------------------------------------------------------------------------
# Module D — unified result over URL and/or message evidence
# -----------------------------------------------------------------------------
def analyze_combined(*, url: str | None, text: str | None,
                     active_call: bool | None) -> dict:
    """Combine Module B and C evidence. Raises 400/422/503/500 AppErrors.

    The text channel goes through :func:`analyze_text` (resolved as a module
    global), the same function the message routes use, so there is exactly one
    text-analysis path and one assessed-guarantee for every caller.
    """
    mod_b = None
    modules: dict = {}

    if url is not None and url.strip() != '':
        cleaned = normalize_url(url)
        try:
            mod_b = check_url(cleaned, fetch_live_page=False)
        except Exception as exc:
            raise E.InternalError(
                'URL analysis failed unexpectedly. Please retry.', module='module_b',
            ) from exc
        modules['module_b'] = mod_b

    mod_c = None
    if text is not None and text.strip() != '':
        cleaned = normalize_message(text)
        full = require_assessed(analyze_text(cleaned))
        mod_c = dict(full)
        mod_c['text'] = cleaned  # context for Module D token attribution
        modules['module_c'] = {k: v for k, v in mod_c.items() if k != 'text'}

    try:
        # Module A is a source-unit benchmark, never a combined-policy input.
        unified = compute_unified_score(None, mod_b, mod_c, active_call=active_call)
    except ModuleDUnavailableError as exc:
        raise E.ArtifactIncompatible(
            'Unified scoring is temporarily unavailable. Please retry.', module='module_d',
        ) from exc
    except (ValueError, TypeError) as exc:
        raise E.FusionInputError(str(exc)) from None

    return {
        'tier': unified['tier'],
        'risk_level': unified['risk_level'],
        'score': unified['score'],
        'explanation': unified['explanation'],
        'analyzed_modules': unified['analyzed_modules'],
        'contributing_modules': unified['contributing_modules'],
        'unavailable_modules': unified['unavailable_modules'],
        'evidence': unified['evidence'],
        'warnings': unified['warnings'],
        'fusion_version': unified['fusion_version'],
        'limitations': unified['limitations'],
        'recommended_action': unified['recommended_action'],
        'details': unified.get('details', {}),
        'modules': modules,
    }


def _mobile_summary(*, risk_level: str, score: float,
                    contributing_modules: list, partial: bool) -> str:
    """One-line mobile summary built from structured fusion output (no parsing)."""
    names = sorted({'URL' for c in contributing_modules if c == 'module_b'}
                   | {'message' for c in contributing_modules if c == 'module_c'}
                   | ({'transaction'} if 'module_a' in contributing_modules else set()))
    basis = ' and '.join(names) + ' evidence' if names else 'available evidence'
    summary = f'{risk_level} risk (risk score {float(score):.2f}): based on {basis}.'
    if partial:
        summary += ' Partial evidence only.'
    return summary


# -----------------------------------------------------------------------------
# Mobile — one entry point over URL and/or message text and/or screenshot
# -----------------------------------------------------------------------------
def analyze_mobile(*, url: str | None, message: str | None,
                   image: dict | None, active_call: bool | None) -> dict:
    """Mobile combined analysis. Raises 400/422/503/500 AppErrors.

    Every channel reuses the single-channel service functions
    (:func:`analyze_url`, :func:`analyze_text`, :func:`analyze_image_content`)
    and the shared Module D fusion layer — no analysis logic lives here.
    When both message text and a screenshot are supplied, each is analyzed
    and the higher-scoring text result feeds fusion (with the maximum
    embedded-URL evidence folded once); both full findings are returned.
    """
    has_url = url is not None and url.strip() != ''
    has_message = message is not None and message.strip() != ''
    has_image = image is not None
    if not (has_url or has_message or has_image):
        raise E.MissingInput(
            'Provide at least one of: url, message text, or a screenshot image.'
        )

    mod_b = analyze_url(url) if has_url else None

    candidates: list = []  # (source, full_c_result, text_for_attribution)
    if has_message:
        cleaned = normalize_message(message)
        full = require_assessed(analyze_text(cleaned))
        candidates.append(('message', full, cleaned))
    if has_image:
        content = image.get('content', b'')
        full = require_image_assessed(analyze_image_content(
            content, declared_type=image.get('declared_type'),
            filename=image.get('filename')))
        candidates.append(('image', full, full.get('ocr_text')))

    mod_c = None
    message_result = None
    image_result = None
    for source, full, _text in candidates:
        if source == 'message':
            message_result = full
        else:
            image_result = full
    if candidates:
        # Worst-of text channels; URL evidence merged once via max, mirroring
        # the fusion layer's single-count rule.
        _source, primary, primary_text = max(candidates, key=lambda item: item[1]['score'])
        embedded_max = 0.0
        for _, full, _ in candidates:
            try:
                embedded_max = max(embedded_max, float(full.get('embedded_url_score') or 0.0))
            except (TypeError, ValueError):
                continue
        mod_c = dict(primary)
        mod_c['embedded_url_score'] = max(
            float(primary.get('embedded_url_score') or 0.0), embedded_max)
        if isinstance(primary_text, str) and primary_text.strip():
            mod_c['text'] = primary_text  # context for Module D token attribution

    try:
        # Module A is a source-unit benchmark, never a combined-policy input.
        unified = compute_unified_score(None, mod_b, mod_c, active_call=active_call)
    except ModuleDUnavailableError as exc:
        raise E.ArtifactIncompatible(
            'Unified scoring is temporarily unavailable. Please retry.', module='module_d',
        ) from exc
    except (ValueError, TypeError) as exc:
        raise E.FusionInputError(str(exc)) from None

    partial = any(m in unified['unavailable_modules'] for m in ('module_b', 'module_c'))
    return {
        'tier': unified['tier'],
        'risk_level': unified['risk_level'],
        'score': unified['score'],
        'summary': _mobile_summary(
            risk_level=unified['risk_level'], score=unified['score'],
            contributing_modules=unified['contributing_modules'], partial=partial),
        'explanation': unified['explanation'],
        'analyzed_modules': unified['analyzed_modules'],
        'contributing_modules': unified['contributing_modules'],
        'unavailable_modules': unified['unavailable_modules'],
        'evidence': unified['evidence'],
        'warnings': unified['warnings'],
        'fusion_version': unified['fusion_version'],
        'limitations': unified['limitations'],
        'recommended_action': unified['recommended_action'],
        'safety_actions': list(SAFETY_ACTIONS[unified['risk_level']]),
        'url_result': mod_b,
        'message_result': message_result,
        'image_result': image_result,
        'details': unified.get('details', {}),
    }
