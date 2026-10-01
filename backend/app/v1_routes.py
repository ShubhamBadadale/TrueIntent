"""``/api/v1`` routes: the mobile-ready contract.

Every success returns ``{"success": true, "data": {...}, "meta": {...}}``;
every failure returns ``{"success": false, "error": {...}, "meta": {...}}``.
See :mod:`backend.app.envelope`.

All handlers are ``async`` and push the blocking ML/OCR work into a threadpool
explicitly — nothing here may ever block the event loop. Failures are raised
as :class:`~backend.app.errors.AppError` by the service layer and rendered by
the application exception handlers in :mod:`backend.app.main`.

Response ``data`` dicts are constructed field by field below (never passed
through from the service layer), so the response models — which forbid extras
— validate exactly what clients receive.
"""
from __future__ import annotations

from fastapi import APIRouter, File, Form, UploadFile
from starlette.concurrency import run_in_threadpool

from backend.app import errors as E
from backend.app import services
from backend.app.config import API_PREFIX
from backend.app.envelope import ErrorEnvelope, success_body
from backend.app.observability import get_request_id
from backend.app.validation import read_upload_bounded
from backend.app.v1_schemas import (
    BenchmarkContractResponse,
    BenchmarkRequest,
    BenchmarkResponse,
    CombinedAnalyzeRequest,
    CombinedAnalyzeResponse,
    ImageAnalyzeResponse,
    MessageAnalyzeRequest,
    MessageAnalyzeResponse,
    MobileAnalyzeRequest,
    MobileAnalyzeResponse,
    UrlAnalyzeRequest,
    UrlAnalyzeResponse,
)
from ml.features_module_a import FEATURE_CONTRACT

router = APIRouter(prefix=API_PREFIX, tags=['v1'])

ERROR_RESPONSES: dict = {
    400: {'model': ErrorEnvelope, 'description': 'Invalid input or unreadable upload'},
    404: {'model': ErrorEnvelope, 'description': 'Unknown endpoint'},
    405: {'model': ErrorEnvelope, 'description': 'Method not allowed'},
    413: {'model': ErrorEnvelope, 'description': 'Body or upload exceeds the configured limit'},
    415: {'model': ErrorEnvelope, 'description': 'Unsupported media type'},
    422: {'model': ErrorEnvelope, 'description': 'Well-formed request the API refuses by design'},
    500: {'model': ErrorEnvelope, 'description': 'Unexpected failure; retry with the request ID'},
    503: {'model': ErrorEnvelope, 'description': 'Model, artifact or OCR engine unavailable'},
}


def _rid() -> str:
    return get_request_id() or 'unknown'


def _mobile_data(result: dict) -> dict:
    """Shape the shared mobile service result for the v1 envelope."""
    data = {
        'tier': result['tier'],
        'risk_level': result['risk_level'],
        'score': result['score'],
        'risk_index': services.risk_index(result['score']),
        'summary': result['summary'],
        'explanation': result['explanation'],
        'analyzed_modules': result['analyzed_modules'],
        'contributing_modules': result['contributing_modules'],
        'unavailable_modules': result['unavailable_modules'],
        'evidence': result['evidence'],
        'warnings': result['warnings'],
        'fusion_version': result['fusion_version'],
        'limitations': result['limitations'],
        'recommended_action': result['recommended_action'],
        'safety_actions': result['safety_actions'],
        'url_findings': None,
        'message_findings': None,
        'ocr_findings': None,
        'details': result.get('details', {}),
    }
    if result.get('url_result') is not None:
        url_result = result['url_result']
        data['url_findings'] = {
            'score': url_result['score'],
            'risk_index': services.risk_index(url_result['score']),
            'reasons': url_result['reasons'],
            'ml_status': url_result.get('ml_status', ''),
        }
    if result.get('message_result') is not None:
        data['message_findings'] = _message_data(result['message_result'])
    if result.get('image_result') is not None:
        ocr = _message_data(result['image_result'])
        ocr['ocr_text'] = result['image_result'].get('ocr_text')
        ocr['ocr_status'] = result['image_result'].get('ocr_status')
        data['ocr_findings'] = ocr
    return data


def _resolve_message_alias(message: str | None, text: str | None) -> str | None:
    """One message text from the `message`/`text` pair; 400 on conflict."""
    has_message = message is not None and message.strip() != ''
    has_text = text is not None and text.strip() != ''
    if has_message and has_text and message.strip() != text.strip():
        raise E.ConflictingInput("Provide 'message' or 'text', not conflicting values.")
    if has_message:
        return message.strip()
    if has_text:
        return text.strip()
    return None


def _parse_form_bool(raw: str | None) -> bool | None:
    """Strict multipart boolean: 'true'/'false' (any case) or omitted."""
    if raw is None or raw.strip() == '':
        return None
    token = raw.strip().lower()
    if token == 'true':
        return True
    if token == 'false':
        return False
    raise E.ValidationFailed("active_call must be 'true' or 'false'.")


_MOBILE_DESCRIPTION = (
    'One combined verdict for mobile clients over a URL and/or message text. '
    'The backend routes each input to the module that can analyze it and fuses '
    'the evidence deterministically. Screenshots use '
    'POST /api/v1/analyze/screenshot (multipart). '
    'Client guidance: allow ~30s for JSON analyses; screenshots may take '
    '~60s when OCR runs. Scores are uncalibrated risk scores (0-1).'
)


@router.post('/analyze', response_model=MobileAnalyzeResponse, responses=ERROR_RESPONSES,
             summary='Mobile combined analysis (URL and/or message)',
             description=_MOBILE_DESCRIPTION)
async def analyze_mobile(body: MobileAnalyzeRequest):
    """Single mobile verdict for JSON-compatible input (no analysis logic here)."""
    result = await run_in_threadpool(
        services.analyze_mobile, url=body.effective_url,
        message=body.effective_message, image=None, active_call=body.active_call,
    )
    return success_body(_mobile_data(result), _rid())


@router.post('/analyze/screenshot', response_model=MobileAnalyzeResponse,
             responses=ERROR_RESPONSES,
             summary='Mobile combined analysis with a screenshot',
             description=(
                 'Multipart sibling of POST /api/v1/analyze for chat screenshots: '
                 'one `image` file (PNG/JPEG/WebP/BMP, magic bytes verified) plus '
                 'optional `url`, `message` and `active_call` (\'true\'/\'false\') '
                 'form fields. Same service, same fusion, same envelope. '
                 'Allow ~60s client-side: OCR runs server-side with a bounded timeout.'
             ))
async def analyze_mobile_screenshot(
    image: UploadFile | None = File(default=None, description='Chat screenshot image'),
    screenshot: UploadFile | None = File(default=None, description='Alias of image'),
    url: str | None = Form(default=None),
    message: str | None = Form(default=None),
    text: str | None = Form(default=None, description='Alias of message'),
    active_call: str | None = Form(default=None, description="'true' or 'false'"),
):
    """Screenshot-first mobile verdict (no analysis logic here)."""
    upload = image if image is not None else screenshot
    if image is not None and screenshot is not None:
        raise E.ConflictingInput("Provide 'image' or 'screenshot', not both.")
    active = _parse_form_bool(active_call)
    resolved_message = _resolve_message_alias(message, text)
    has_evidence = (
        upload is not None
        or (url is not None and url.strip() != '')
        or resolved_message is not None
    )
    if not has_evidence:
        raise E.MissingInput(
            'Provide at least one of: url, message text, or a screenshot image.'
        )
    image_payload = None
    if upload is not None:
        content = await read_upload_bounded(upload)
        image_payload = {
            'content': content,
            'declared_type': upload.content_type,
            'filename': upload.filename,
        }
    result = await run_in_threadpool(
        services.analyze_mobile,
        url=url.strip() if url is not None and url.strip() != '' else None,
        message=resolved_message, image=image_payload, active_call=active,
    )
    return success_body(_mobile_data(result), _rid())


def _message_data(result: dict) -> dict:
    return {
        'score': result['score'],
        'risk_index': services.risk_index(result['score']),
        'signature': result['signature'],
        'reasons': result['reasons'],
        'ml_status': result.get('ml_status', ''),
        'intent': result.get('intent'),
        'intent_probabilities': result.get('intent_probabilities', {}),
        'rule_evidence': result.get('rule_evidence', []),
        'heuristic_evidence': result.get('heuristic_evidence', []),
        'text_assessed': result.get('text_assessed', False),
    }


@router.post('/analyze/url', response_model=UrlAnalyzeResponse, responses=ERROR_RESPONSES,
             summary='Analyze a URL')
async def analyze_url(body: UrlAnalyzeRequest):
    """Offline URL safety analysis. Never fetches the destination."""
    result = await run_in_threadpool(services.analyze_url, body.url)
    data = {
        'score': result['score'],
        'risk_index': services.risk_index(result['score']),
        'reasons': result['reasons'],
        'ml_status': result['ml_status'],
    }
    return success_body(data, _rid())


@router.post('/analyze/message', response_model=MessageAnalyzeResponse, responses=ERROR_RESPONSES,
             summary='Analyze message text')
async def analyze_message(body: MessageAnalyzeRequest):
    """Message intent analysis over a JSON body — no multipart needed."""
    result = services.require_assessed(
        await run_in_threadpool(services.analyze_text, body.text)
    )
    return success_body(_message_data(result), _rid())


@router.post('/analyze/image', response_model=ImageAnalyzeResponse, responses=ERROR_RESPONSES,
             summary='Analyze a chat screenshot')
async def analyze_image(image: UploadFile = File(description='PNG, JPEG, WebP or BMP screenshot')):
    """Screenshot analysis.

    The declared MIME type and filename must agree with the actual magic bytes;
    the body is read in bounded chunks. OCR runs in a threadpool.
    """
    content = await read_upload_bounded(image)
    result = services.require_image_assessed(
        await run_in_threadpool(
            services.analyze_image_content, content,
            declared_type=image.content_type, filename=image.filename,
        )
    )
    data = _message_data(result)
    data['ocr_text'] = result.get('ocr_text')
    data['ocr_status'] = result.get('ocr_status')
    return success_body(data, _rid())


@router.post('/analyze/combined', response_model=CombinedAnalyzeResponse,
             responses=ERROR_RESPONSES, summary='Combine URL and message evidence')
async def analyze_combined(body: CombinedAnalyzeRequest):
    """Unified risk index over URL and/or message evidence.

    There is deliberately no ``transaction`` field: schema validation refuses
    it with a hint, because Module A is a benchmark, not a fusion input.
    """
    result = await run_in_threadpool(
        services.analyze_combined, url=body.url, text=body.text, active_call=body.active_call,
    )
    data = {
        'tier': result['tier'],
        'risk_level': result['risk_level'],
        'score': result['score'],
        'risk_index': services.risk_index(result['score']),
        'explanation': result['explanation'],
        'analyzed_modules': result['analyzed_modules'],
        'contributing_modules': result['contributing_modules'],
        'unavailable_modules': result['unavailable_modules'],
        'evidence': result['evidence'],
        'warnings': result['warnings'],
        'fusion_version': result['fusion_version'],
        'limitations': result['limitations'],
        'recommended_action': result['recommended_action'],
        'details': result.get('details', {}),
        'modules': result.get('modules', {}),
    }
    return success_body(data, _rid())


@router.post('/module-a/benchmark', response_model=BenchmarkResponse, responses=ERROR_RESPONSES,
             summary="Run the Module A amount-only benchmark")
async def module_a_benchmark(body: BenchmarkRequest):
    """Source-unit benchmark scoring. Requires an explicit ``amount_unit`` —
    there is no default to fall back on, so a client cannot drift into INR."""
    payload = body.to_module_a_payload()
    result = await run_in_threadpool(services.run_benchmark, payload)
    return success_body(result, _rid())


@router.get('/module-a/contract', response_model=BenchmarkContractResponse, responses=ERROR_RESPONSES,
            summary='Inspect the versioned Module A feature contract')
async def module_a_contract():
    """The exact contract an artifact must satisfy to be served."""
    data = {
        'version': FEATURE_CONTRACT['version'],
        'artifact_version': FEATURE_CONTRACT['artifact_version'],
        'model_version': FEATURE_CONTRACT['model_version'],
        'features': list(FEATURE_CONTRACT['features']),
        'feature_order': list(FEATURE_CONTRACT['feature_order']),
        'dataset_id': FEATURE_CONTRACT['dataset_id'],
        'preprocessing_version': FEATURE_CONTRACT['preprocessing_version'],
        'amount_unit': FEATURE_CONTRACT['amount_unit'],
        'expected_units': dict(FEATURE_CONTRACT['expected_units']),
        'scope': FEATURE_CONTRACT['scope'],
    }
    return success_body(data, _rid())
