"""TrueIntent API request/response schemas (Pydantic v2).

Field names and constraints mirror the Iteration 3 dataset schemas in
`data/schema.md` (Module A transaction columns, Module B `url`, Module C
`raw_text` / `scam_type` taxonomy).
"""

from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


# -----------------------------------------------------------------------------
# Module A — Transaction + call state (schema.md section 1)
# -----------------------------------------------------------------------------
class TransactionCheckRequest(BaseModel):
    amount: float = Field(..., gt=0, description="Transaction value (> 0)")
    timestamp: Optional[str] = Field(
        default=None, description="ISO 8601 timestamp, e.g. 2026-09-12T20:54:00Z"
    )
    device_id: str = Field(..., min_length=1, description="Non-empty device identifier")
    is_active_call: bool = Field(default=False, description="Active call during transfer")
    transaction_velocity: int = Field(
        default=1, ge=0, description="Transactions from device in last hour (>= 0)"
    )

    @field_validator("device_id")
    @classmethod
    def _device_id_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("device_id must be a non-empty string.")
        return v

    @field_validator("timestamp")
    @classmethod
    def _timestamp_iso8601(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        candidate = v.strip().replace("Z", "+00:00")
        from datetime import datetime

        try:
            datetime.fromisoformat(candidate)
        except ValueError:
            raise ValueError(
                "timestamp must be ISO 8601, e.g. 2026-09-12T20:54:00Z."
            )
        return v


class TransactionCheckResponse(BaseModel):
    score: float = Field(..., ge=0.0, le=1.0)


# -----------------------------------------------------------------------------
# Module B — URL safety (schema.md section 2)
# -----------------------------------------------------------------------------
class UrlCheckRequest(BaseModel):
    url: str = Field(..., min_length=1, description="URL to evaluate")

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


# -----------------------------------------------------------------------------
# Module D — Combined (any subset of the above)
# -----------------------------------------------------------------------------
class CombinedRequest(BaseModel):
    transaction: Optional[TransactionCheckRequest] = None
    url: Optional[str] = None
    text: Optional[str] = None

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
    score: float = Field(..., ge=0.0, le=1.0)
    explanation: str
    details: dict = Field(default_factory=dict)
    modules: dict = Field(default_factory=dict)
