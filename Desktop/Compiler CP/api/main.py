from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from mcdc.compile_source import compile_source
from mcdc.diagnostics import Diagnostic

from .schemas import CompileRequest, CompileResponse, DiagnosticDto, ExampleDto, ValidateRequest, ValidateResponse


ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"
FEATURED_EXAMPLES = ["static_web_server", "negative_unsupported_resource"]

app = FastAPI(title="Multi-Cloud Deployment Compiler API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/compile", response_model=CompileResponse)
def compile_endpoint(request: CompileRequest) -> CompileResponse:
    return _compile_response(request.source, request.target)


@app.get("/api/examples", response_model=list[ExampleDto])
def examples_endpoint() -> list[ExampleDto]:
    examples: list[ExampleDto] = []
    for name in FEATURED_EXAMPLES:
        path = EXAMPLES / f"{name}.mcd"
        if path.exists():
            examples.append(ExampleDto(name=path.stem, source=path.read_text()))
    return examples


@app.post("/api/validate-terraform", response_model=ValidateResponse)
def validate_terraform(request: ValidateRequest) -> ValidateResponse:
    tool = shutil.which("terraform") or shutil.which("tofu")
    if tool is None:
        return ValidateResponse(available=False, success=False, output="Terraform/OpenTofu is not installed on this server.")
    with tempfile.TemporaryDirectory() as tmp:
        workdir = Path(tmp)
        (workdir / "main.tf").write_text(request.hcl)
        init = subprocess.run([tool, "init", "-backend=false", "-input=false"], cwd=workdir, text=True, capture_output=True, check=False)
        if init.returncode != 0:
            return ValidateResponse(available=True, success=False, output=init.stdout + init.stderr)
        validate = subprocess.run([tool, "validate"], cwd=workdir, text=True, capture_output=True, check=False)
        return ValidateResponse(available=True, success=validate.returncode == 0, output=validate.stdout + validate.stderr)


@app.websocket("/api/compile/stream")
async def compile_stream(websocket: WebSocket) -> None:
    await websocket.accept()
    payload: dict[str, Any] = json.loads(await websocket.receive_text())
    source = str(payload.get("source", ""))
    target = payload.get("target", "all")
    await websocket.send_json({"phase": "request", "status": "ok", "duration_ms": 0})
    result = _compile_response(source, target)
    for phase, duration in result.report.get("phase_timings_ms", {}).items():
        await websocket.send_json({"phase": phase, "status": "ok", "duration_ms": duration})
    await websocket.send_json({"phase": "complete", "status": "ok" if result.success else "error", "result": result.model_dump()})
    await websocket.close()


def _compile_response(source: str, target: str) -> CompileResponse:
    result = compile_source(source, target)  # type: ignore[arg-type]
    return CompileResponse(
        success=result.success,
        diagnostics=[_diag(d) for d in result.diagnostics],
        ast=result.ast,
        ir=result.ir,
        generated=result.generated,
        report=result.report,
    )


def _diag(diag: Diagnostic) -> DiagnosticDto:
    return DiagnosticDto(
        severity=diag.severity,
        code=diag.code,
        message=diag.message,
        line=diag.loc.line if diag.loc else None,
        column=diag.loc.column if diag.loc else None,
        phase=diag.phase,
        hint=diag.hint,
    )
