"""TrueIntent API request/response schemas (Pydantic v2).

Field names and constraints mirror the Iteration 3 dataset schemas in
`data/schema.md` (Module A transaction columns, Module B `url`, Module C
`raw_text` / `scam_type` taxonomy).
"""

from typing import Literal, Optional
from datetime import datetime, timezone

from pydantic import BaseModel, Field, field_validator, model_validator


# -----------------------------------------------------------------------------
# Module A — Transaction + call state (schema.md section 1)
# -----------------------------------------------------------------------------
class CallTelemetry(BaseModel):
    """Unattested phone report for the course demo; not proof of a call."""
    device_id: str = Field(min_length=1)
    is_active_call: bool
    timestamp: datetime

    @model_validator(mode="after")
    def validate_report(self):
        if not self.device_id.strip() or self.timestamp.tzinfo is None:
            raise ValueError("Telemetry needs a device ID and timezone-aware timestamp")
        age = (datetime.now(timezone.utc) - self.timestamp).total_seconds()
        if not -30 <= age <= 120:
            raise ValueError("Telemetry must be no older than 120 seconds or over 30 seconds ahead")
        return self


class TransactionCheckRequest(BaseModel):
    """Amount-only IEEE-CIS benchmark request.

    `amount_unit` must be the explicit source unit; anything else (including
    the `INR` default) is refused downstream with 422. Every field other than
    `amount`/`amount_unit` is accepted legacy metadata: validated for shape and
    echoed back for caller compatibility, never used as a model feature and
    never reported as transaction-fusion evidence.
    """

    amount: float = Field(..., ge=0, allow_inf_nan=False, description="Nonnegative benchmark amount")
    amount_unit: Literal['INR', 'ieee_cis_source'] = Field(
        default='INR', description='INR is unsupported; source-unit benchmark use must be explicit'
    )
    timestamp: Optional[str] = Field(
        default=None, description="Legacy ISO 8601 metadata; not used as a clock feature"
    )
    device_id: Optional[str] = Field(default=None, min_length=1, description="Legacy metadata; not a model feature")
    is_active_call: bool = Field(default=False, description="Legacy reported call state; not a model feature")
    call_telemetry: Optional[CallTelemetry] = None
    transaction_velocity: int = Field(
        default=1, ge=0, description="Legacy metadata; excluded from the amount-only model"
    )

    @field_validator('amount', mode='before')
    @classmethod
    def _amount_not_boolean(cls, value):
        if isinstance(value, bool):
            raise ValueError('amount must be numeric, not boolean')
        return value

    @model_validator(mode="after")
    def matching_device(self):
        if self.call_telemetry and self.call_telemetry.device_id != self.device_id:
            raise ValueError("Telemetry device_id must match transaction device_id")
        return self

    def to_module_a_payload(self):
        payload = self.model_dump(exclude_none=True, exclude={"call_telemetry"})
        if self.call_telemetry is not None:
            payload["is_active_call"] = self.call_telemetry.is_active_call
        return payload

    @field_validator("device_id")
    @classmethod
    def _device_id_not_blank(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.strip():
            raise ValueError("device_id must be a non-empty string.")
        return v

    @field_validator("timestamp")
    @classmethod
    def _timestamp_iso8601(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        candidate = v.strip().replace("Z", "+00:00")
        try:
            datetime.fromisoformat(candidate)
        except ValueError:
            raise ValueError(
                "timestamp must be ISO 8601, e.g. 2026-09-12T20:54:00Z."
            )
        return v


class TransactionCheckResponse(BaseModel):
    score: float = Field(..., ge=0.0, le=1.0)
    analysis_scope: Literal['ieee_cis_amount_only_benchmark'] = 'ieee_cis_amount_only_benchmark'
    explanation: str


# -----------------------------------------------------------------------------
# Module B — URL safety (schema.md section 2)
# -----------------------------------------------------------------------------
class UrlCheckRequest(BaseModel):
    url: str = Field(..., min_length=1, max_length=8192, description="URL to evaluate")

    @field_validator("url")
    @classmethod
    def _url_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("url must be a non-empty string.")
        return v.strip()


class UrlCheckResponse(BaseModel):
    score: float = Field(..., ge=0.0, le=1.0)
    reasons: list[str] = Field(default_factory=list)
    ml_status: str = ""


# -----------------------------------------------------------------------------
# Module C — Message / screenshot (schema.md section 3)
# -----------------------------------------------------------------------------
Signature = Literal["fear_authority", "greed_opportunity", "none"]


class MessageCheckResponse(BaseModel):
    score: float = Field(..., ge=0.0, le=1.0)
    signature: Signature = "none"
    reasons: list[str] = Field(default_factory=list)
    ml_status: str = ""
    ocr_text: Optional[str] = None
    ocr_status: Optional[str] = None
    intent: Optional[str] = None
    intent_probabilities: dict[str, float] = Field(default_factory=dict)
    rule_evidence: list[dict] = Field(default_factory=list)
    heuristic_evidence: list[dict] = Field(default_factory=list)
    text_assessed: bool = False


# -----------------------------------------------------------------------------
# Module D — Combined (any subset of the above)
# -----------------------------------------------------------------------------
class CombinedRequest(BaseModel):
    """URL and/or message evidence, optionally with a user-reported call state.

    `transaction` is retained only so a transaction-bearing request is refused
    with an explicit 422 explaining that Module A is benchmark-only; it can
    never contribute to fusion.
    """

    active_call: Optional[bool] = Field(default=None, strict=True, description='User-reported status; omitted means unknown')
    transaction: Optional[TransactionCheckRequest] = None
    url: Optional[str] = Field(default=None, max_length=8192)
    text: Optional[str] = Field(default=None, max_length=20000)

    @model_validator(mode="after")
    def _at_least_one_input(self):
        has_txn = self.transaction is not None
        has_url = self.url is not None and self.url.strip() != ""
        has_text = self.text is not None and self.text.strip() != ""
        if not (has_txn or has_url or has_text):
            raise ValueError(
                "Provide at least one of: transaction, url, or non-empty text."
            )
        return self


class CombinedResponse(BaseModel):
    tier: Literal["Low", "Medium", "High", "Critical"]
    risk_level: Literal["Low", "Medium", "High", "Critical"] = "Low"
    score: float = Field(..., ge=0.0, le=1.0)
    explanation: str
    analyzed_modules: list[str] = Field(default_factory=list)
    contributing_modules: list[str] = Field(default_factory=list)
    unavailable_modules: list[str] = Field(default_factory=list)
    evidence: list[dict] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    fusion_version: str = ""
    limitations: list[str] = Field(default_factory=list)
    recommended_action: str = ""
    details: dict = Field(default_factory=dict)
    modules: dict = Field(default_factory=dict)
