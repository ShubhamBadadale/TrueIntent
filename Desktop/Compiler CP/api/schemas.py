from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


Target = Literal["aws", "gcp", "azure", "all"]


class CompileRequest(BaseModel):
    source: str = Field(..., min_length=1, max_length=20_000)
    target: Target = "all"


class DiagnosticDto(BaseModel):
    severity: Literal["error", "warning"]
    code: str
    message: str
    line: Optional[int] = None
    column: Optional[int] = None
    phase: str
    hint: Optional[str] = None


class CompileResponse(BaseModel):
    success: bool
    diagnostics: List[DiagnosticDto]
    ast: Optional[Dict[str, Any]]
    ir: Optional[Dict[str, Any]]
    generated: Dict[str, Optional[str]]
    report: Dict[str, Any]


class ExampleDto(BaseModel):
    name: str
    source: str


class ValidateRequest(BaseModel):
    hcl: str = Field(..., min_length=1, max_length=200_000)


class ValidateResponse(BaseModel):
    available: bool
    success: bool
    output: str
