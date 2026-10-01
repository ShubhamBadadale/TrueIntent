"""Error taxonomy shared by every layer.

Two audiences, two renderings:

* ``/api/v1/*`` returns the envelope from :mod:`backend.app.envelope`.
* The legacy ``/check-*`` routes return FastAPI's ``{"detail": ...}`` body,
  which the React portal and the existing suite both depend on.

Both renderings come from the same :class:`AppError`, so an error can never
report one code on the new routes and a different message on the old ones.

Messages written here are safe to return to a client: they never contain a
filesystem path, an environment value, a model path or a stack trace.
"""
from __future__ import annotations

from typing import Any


class ErrorCode:
    """Stable, machine-readable error identifiers.

    These are part of the public v1 contract: clients may branch on them, so
    they are append-only.
    """

    VALIDATION_ERROR = 'validation_error'
    INVALID_URL = 'invalid_url'
    MISSING_INPUT = 'missing_input'
    CONFLICTING_INPUT = 'conflicting_input'
    UNSUPPORTED_MEDIA_TYPE = 'unsupported_media_type'
    PAYLOAD_TOO_LARGE = 'payload_too_large'
    UNREADABLE_IMAGE = 'unreadable_image'
    OCR_UNAVAILABLE = 'ocr_unavailable'
    MESSAGE_NOT_ASSESSED = 'message_not_assessed'
    MODEL_UNAVAILABLE = 'model_unavailable'
    ARTIFACT_INCOMPATIBLE = 'artifact_incompatible'
    TRANSACTION_FUSION_DISABLED = 'transaction_fusion_disabled'
    AMOUNT_UNIT_REJECTED = 'amount_unit_rejected'
    NOT_FOUND = 'not_found'
    METHOD_NOT_ALLOWED = 'method_not_allowed'
    INTERNAL_ERROR = 'internal_error'


class AppError(Exception):
    """Base class for every deliberate, client-visible failure."""

    status_code: int = 500
    code: str = ErrorCode.INTERNAL_ERROR
    module: str | None = None
    #: Set when the message was assembled from an upstream exception. Such
    #: messages are never echoed to a client; ``public_message`` is used instead.
    derived_from_exception: bool = False

    def __init__(
        self,
        message: str,
        *,
        code: str | None = None,
        module: str | None = None,
        status_code: int | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        if code is not None:
            self.code = code
        if module is not None:
            self.module = module
        if status_code is not None:
            self.status_code = status_code
        self.details: dict[str, Any] = details or {}

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.message

    def to_dict(self) -> dict[str, Any]:
        return {
            'code': self.code,
            'message': self.message,
            'module': self.module,
            'details': self.details,
        }


# ---------------------------------------------------------------------------
# 4xx — the caller can fix these
# ---------------------------------------------------------------------------
class ValidationFailed(AppError):
    status_code = 422
    code = ErrorCode.VALIDATION_ERROR


class InvalidUrl(ValidationFailed):
    code = ErrorCode.INVALID_URL
    module = 'module_b'


class MissingInput(AppError):
    status_code = 400
    code = ErrorCode.MISSING_INPUT


class ConflictingInput(AppError):
    status_code = 400
    code = ErrorCode.CONFLICTING_INPUT


class UnsupportedMediaType(AppError):
    status_code = 415
    code = ErrorCode.UNSUPPORTED_MEDIA_TYPE


class PayloadTooLarge(AppError):
    status_code = 413
    code = ErrorCode.PAYLOAD_TOO_LARGE


class UnreadableImage(AppError):
    status_code = 400
    code = ErrorCode.UNREADABLE_IMAGE
    module = 'module_c'


# ---------------------------------------------------------------------------
# 400 — well-formed request the fusion layer cannot use
# ---------------------------------------------------------------------------
class FusionInputError(AppError):
    """Raised when no usable evidence reaches Module D (e.g. whitespace-only
    inputs that pass schema shape checks). Never a verdict."""

    status_code = 400
    code = ErrorCode.VALIDATION_ERROR
    module = 'module_d'


# ---------------------------------------------------------------------------
# 422 — well-formed request, refused by design
# ---------------------------------------------------------------------------
class TransactionFusionDisabled(ValidationFailed):
    code = ErrorCode.TRANSACTION_FUSION_DISABLED
    module = 'module_d'


class AmountUnitRejected(ValidationFailed):
    code = ErrorCode.AMOUNT_UNIT_REJECTED
    module = 'module_a'


# ---------------------------------------------------------------------------
# 503 — the caller is correct, this deployment cannot answer yet
# ---------------------------------------------------------------------------
class OcrUnavailable(AppError):
    status_code = 503
    code = ErrorCode.OCR_UNAVAILABLE
    module = 'module_c'


class MessageNotAssessed(AppError):
    """The text was never actually scored. Never presented as a low score."""

    status_code = 503
    code = ErrorCode.MESSAGE_NOT_ASSESSED
    module = 'module_c'


class ModelUnavailable(AppError):
    status_code = 503
    code = ErrorCode.MODEL_UNAVAILABLE


class ArtifactIncompatible(ModelUnavailable):
    code = ErrorCode.ARTIFACT_INCOMPATIBLE


class InternalError(AppError):
    status_code = 500
    code = ErrorCode.INTERNAL_ERROR
    #: Clients never see an internal message; it exists for server-side logs.
    derived_from_exception = True


#: HTTP status -> default code, used when translating framework exceptions.
STATUS_CODE_MAP: dict[int, str] = {
    400: ErrorCode.VALIDATION_ERROR,
    401: ErrorCode.VALIDATION_ERROR,
    403: ErrorCode.VALIDATION_ERROR,
    404: ErrorCode.NOT_FOUND,
    405: ErrorCode.METHOD_NOT_ALLOWED,
    413: ErrorCode.PAYLOAD_TOO_LARGE,
    415: ErrorCode.UNSUPPORTED_MEDIA_TYPE,
    422: ErrorCode.VALIDATION_ERROR,
    429: ErrorCode.VALIDATION_ERROR,
}