"""``/api/v1`` request and response models.

Request models mirror the legacy validation exactly (same bounds, same boolean
rejection, same telemetry rules) but speak JSON end to end: the message
endpoint takes a JSON body instead of multipart form fields, which is what a
mobile client wants.

Response ``data`` payloads reuse the legacy shapes and add ``risk_index`` —
the 0–100 rendering of ``score`` that every results view already shows. The
benchmark never carries a risk index: it is explicitly not a risk tier.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from backend.app.envelope import ErrorEnvelope, ResponseMeta

Signature = Literal['fear_authority', 'greed_opportunity', 'none']
Tier = Literal['Low', 'Medium', 'High', 'Critical']


def _not_blank(value: str, field: str) -> str:
    if not value.strip():
        raise ValueError(f'{field} must be a non-empty string.')
    return value.strip()


# -----------------------------------------------------------------------------
# Shared result fragments
# -----------------------------------------------------------------------------
class UrlAnalysisData(BaseModel):
    model_config = ConfigDict(extra='forbid')

    score: float = Field(ge=0.0, le=1.0)
    risk_index: int = Field(ge=0, le=100, description='score rescaled to 0-100; uncalibrated')
    reasons: list[str] = Field(default_factory=list)
    ml_status: str = ''


class MessageAnalysisData(BaseModel):
    model_config = ConfigDict(extra='forbid')

    score: float = Field(ge=0.0, le=1.0)
    risk_index: int = Field(ge=0, le=100, description='score rescaled to 0-100; uncalibrated')
    signature: Signature = 'none'
    reasons: list[str] = Field(default_factory=list)
    ml_status: str = ''
    intent: Optional[str] = None
    intent_probabilities: dict[str, float] = Field(default_factory=dict)
    rule_evidence: list[dict] = Field(default_factory=list)
    heuristic_evidence: list[dict] = Field(
        default_factory=list,
        description='Offline heuristic evidence only; never an ML verdict',
    )
    text_assessed: bool = False


class ImageAnalysisData(MessageAnalysisData):
    ocr_text: Optional[str] = None
    ocr_status: Optional[str] = None


class CombinedAnalysisData(BaseModel):
    model_config = ConfigDict(extra='forbid')

    tier: Tier
    risk_level: Tier = 'Low'
    score: float = Field(ge=0.0, le=1.0)
    risk_index: int = Field(ge=0, le=100, description='score rescaled to 0-100; uncalibrated')
    explanation: str
    analyzed_modules: list[str] = Field(default_factory=list)
    contributing_modules: list[str] = Field(default_factory=list)
    unavailable_modules: list[str] = Field(default_factory=list)
    evidence: list[dict] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    fusion_version: str = ''
    limitations: list[str] = Field(default_factory=list)
    recommended_action: str = ''
    details: dict = Field(default_factory=dict)
    modules: dict = Field(default_factory=dict)


class BenchmarkData(BaseModel):
    model_config = ConfigDict(extra='forbid')

    score: float = Field(ge=0.0, le=1.0)
    analysis_scope: Literal['ieee_cis_amount_only_benchmark'] = 'ieee_cis_amount_only_benchmark'
    explanation: str


class BenchmarkContractData(BaseModel):
    """The versioned Module A contract, so a client can discover it."""

    model_config = ConfigDict(extra='forbid')

    version: int
    artifact_version: int
    model_version: str
    features: list[str]
    feature_order: list[str]
    dataset_id: str
    preprocessing_version: int
    amount_unit: str
    expected_units: dict[str, str]
    scope: str


# -----------------------------------------------------------------------------
# Requests
# -----------------------------------------------------------------------------
class UrlAnalyzeRequest(BaseModel):
    """Length limits live in the service layer so an overlong URL gets the
    specific ``invalid_url`` error (with the limit) rather than a generic
    schema rejection."""

    model_config = ConfigDict(extra='forbid')

    url: str = Field(min_length=1)

    @field_validator('url')
    @classmethod
    def _url_not_blank(cls, v: str) -> str:
        return _not_blank(v, 'url')


class MessageAnalyzeRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')

    text: str = Field(min_length=1)

    @field_validator('text')
    @classmethod
    def _text_not_blank(cls, v: str) -> str:
        return _not_blank(v, 'text')


class CombinedAnalyzeRequest(BaseModel):
    """URL and/or message evidence with an optional user-reported call state.

    A ``transaction`` field is not accepted at all: it is refused by schema
    validation with a hint, rather than by a downstream branch.
    """

    model_config = ConfigDict(extra='forbid')

    url: Optional[str] = Field(default=None)
    text: Optional[str] = Field(default=None)
    active_call: Optional[bool] = Field(
        default=None, strict=True,
        description='User-reported status; omitted means unknown',
    )

    @model_validator(mode='after')
    def _at_least_one_input(self):
        has_url = self.url is not None and self.url.strip() != ''
        has_text = self.text is not None and self.text.strip() != ''
        if not (has_url or has_text):
            raise ValueError('Provide url and/or non-empty text.')
        return self


class MobileAnalyzeRequest(BaseModel):
    """The mobile entry point: one or more of URL, message text, screenshot.

    Screenshots travel as multipart files on ``POST /api/v1/analyze/screenshot``
    (same service, same fusion); this JSON body covers URL and message text.
    ``text`` is accepted as an alias of ``message`` so payloads copied from
    ``/analyze/combined`` keep working — but the two must not disagree.
    """

    model_config = ConfigDict(
        extra='forbid',
        json_schema_extra={
            'examples': [
                {'url': 'https://example.com/login',
                 'message': 'Your account will be suspended, verify now.'},
                {'message': 'Hey, are we still meeting for lunch tomorrow?'},
                {'url': 'https://www.google.com/'},
            ],
        },
    )

    url: Optional[str] = Field(default=None, description='Suspicious link to check')
    message: Optional[str] = Field(default=None, description='Chat/SMS text to check')
    text: Optional[str] = Field(
        default=None, description='Alias of message; must not disagree with it',
    )
    active_call: Optional[bool] = Field(
        default=None, strict=True,
        description='User-reported status; omitted means unknown',
    )

    @model_validator(mode='after')
    def _at_least_one_input(self):
        has_url = self.url is not None and self.url.strip() != ''
        has_message = ((self.message is not None and self.message.strip() != '')
                       or (self.text is not None and self.text.strip() != ''))
        if not (has_url or has_message):
            raise ValueError('Provide url and/or non-empty message text.')
        if (self.message is not None and self.message.strip() != ''
                and self.text is not None and self.text.strip() != ''
                and self.message.strip() != self.text.strip()):
            raise ValueError("Provide 'message' or 'text', not conflicting values.")
        return self

    @property
    def effective_message(self) -> Optional[str]:
        """The single message text the service analyzes (alias resolved)."""
        if self.message is not None and self.message.strip() != '':
            return self.message.strip()
        if self.text is not None and self.text.strip() != '':
            return self.text.strip()
        return None

    @property
    def effective_url(self) -> Optional[str]:
        if self.url is not None and self.url.strip() != '':
            return self.url.strip()
        return None


class CallTelemetryV1(BaseModel):
    """Unattested phone report; not proof of a call. Same rules as legacy."""

    model_config = ConfigDict(extra='forbid')

    device_id: str = Field(min_length=1)
    is_active_call: bool
    timestamp: datetime

    @model_validator(mode='after')
    def validate_report(self):
        if not self.device_id.strip() or self.timestamp.tzinfo is None:
            raise ValueError('Telemetry needs a device ID and timezone-aware timestamp')
        age = (datetime.now(timezone.utc) - self.timestamp).total_seconds()
        if not -30 <= age <= 120:
            raise ValueError('Telemetry must be no older than 120 seconds or over 30 seconds ahead')
        return self


class BenchmarkRequest(BaseModel):
    """Amount-only IEEE-CIS benchmark. Unlike the legacy route, `amount_unit`
    has no default here: a new client must state its units explicitly."""

    model_config = ConfigDict(extra='forbid')

    amount: float = Field(ge=0, allow_inf_nan=False, description='Nonnegative benchmark amount')
    amount_unit: Literal['INR', 'ieee_cis_source'] = Field(
        description='Only ieee_cis_source is supported; INR is refused with 422'
    )
    timestamp: Optional[str] = Field(
        default=None, description='Legacy ISO 8601 metadata; not used as a clock feature'
    )
    device_id: Optional[str] = Field(default=None, min_length=1)
    is_active_call: bool = Field(default=False)
    call_telemetry: Optional[CallTelemetryV1] = None
    transaction_velocity: int = Field(default=1, ge=0)

    @field_validator('amount', mode='before')
    @classmethod
    def _amount_not_boolean(cls, value):
        if isinstance(value, bool):
            raise ValueError('amount must be numeric, not boolean')
        return value

    @field_validator('device_id')
    @classmethod
    def _device_id_not_blank(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.strip():
            raise ValueError('device_id must be a non-empty string.')
        return v

    @field_validator('timestamp')
    @classmethod
    def _timestamp_iso8601(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        candidate = v.strip().replace('Z', '+00:00')
        try:
            datetime.fromisoformat(candidate)
        except ValueError:
            raise ValueError('timestamp must be ISO 8601, e.g. 2026-09-12T20:54:00Z.')
        return v

    @model_validator(mode='after')
    def matching_device(self):
        if self.call_telemetry and self.call_telemetry.device_id != self.device_id:
            raise ValueError('Telemetry device_id must match transaction device_id')
        return self

    def to_module_a_payload(self) -> dict:
        payload = self.model_dump(exclude_none=True, exclude={'call_telemetry'})
        if self.call_telemetry is not None:
            payload['is_active_call'] = self.call_telemetry.is_active_call
        return payload


# -----------------------------------------------------------------------------
# Envelopes
# -----------------------------------------------------------------------------
class UrlAnalyzeResponse(BaseModel):
    model_config = ConfigDict(extra='forbid')

    success: Literal[True] = True
    data: UrlAnalysisData
    meta: ResponseMeta


class MessageAnalyzeResponse(BaseModel):
    model_config = ConfigDict(extra='forbid')

    success: Literal[True] = True
    data: MessageAnalysisData
    meta: ResponseMeta


class ImageAnalyzeResponse(BaseModel):
    model_config = ConfigDict(extra='forbid')

    success: Literal[True] = True
    data: ImageAnalysisData
    meta: ResponseMeta


class CombinedAnalyzeResponse(BaseModel):
    model_config = ConfigDict(extra='forbid')

    success: Literal[True] = True
    data: CombinedAnalysisData
    meta: ResponseMeta


class MobileAnalyzeData(BaseModel):
    """One mobile verdict over URL and/or message and/or screenshot evidence."""

    model_config = ConfigDict(extra='forbid')

    tier: Tier
    risk_level: Tier = 'Low'
    score: float = Field(ge=0.0, le=1.0, description='Overall risk score; uncalibrated')
    risk_index: int = Field(ge=0, le=100, description='score rescaled to 0-100; uncalibrated')
    summary: str = Field(description='One-line verdict for small screens')
    explanation: str
    analyzed_modules: list[str] = Field(default_factory=list)
    contributing_modules: list[str] = Field(default_factory=list)
    unavailable_modules: list[str] = Field(default_factory=list)
    evidence: list[dict] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    fusion_version: str = ''
    limitations: list[str] = Field(default_factory=list)
    recommended_action: str = ''
    safety_actions: list[str] = Field(
        default_factory=list, description='Checklist version of the recommended action',
    )
    url_findings: Optional[UrlAnalysisData] = Field(
        default=None, description='Present when a URL was submitted',
    )
    message_findings: Optional[MessageAnalysisData] = Field(
        default=None, description='Present when message text was submitted',
    )
    ocr_findings: Optional[ImageAnalysisData] = Field(
        default=None, description='Present when a screenshot was submitted',
    )
    details: dict = Field(default_factory=dict)


class BenchmarkResponse(BaseModel):
    model_config = ConfigDict(extra='forbid')

    success: Literal[True] = True
    data: BenchmarkData
    meta: ResponseMeta


class MobileAnalyzeResponse(BaseModel):
    model_config = ConfigDict(extra='forbid')

    success: Literal[True] = True
    data: MobileAnalyzeData
    meta: ResponseMeta


class BenchmarkContractResponse(BaseModel):
    model_config = ConfigDict(extra='forbid')

    success: Literal[True] = True
    data: BenchmarkContractData
    meta: ResponseMeta


__all__ = [
    'BenchmarkContractData', 'BenchmarkContractResponse', 'BenchmarkData',
    'BenchmarkRequest', 'BenchmarkResponse', 'CallTelemetryV1',
    'CombinedAnalysisData', 'CombinedAnalyzeRequest', 'CombinedAnalyzeResponse',
    'ErrorEnvelope', 'ImageAnalysisData', 'ImageAnalyzeResponse',
    'MessageAnalysisData', 'MessageAnalyzeRequest', 'MessageAnalyzeResponse',
    'MobileAnalyzeData', 'MobileAnalyzeRequest', 'MobileAnalyzeResponse',
    'ResponseMeta', 'Signature', 'Tier', 'UrlAnalysisData', 'UrlAnalyzeRequest',
    'UrlAnalyzeResponse',
]
