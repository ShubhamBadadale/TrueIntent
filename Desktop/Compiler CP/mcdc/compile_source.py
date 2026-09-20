from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Literal

from .backends.base import GeneratedOutput
from .capability_matrix import check_capabilities
from .compiler import BACKENDS
from .diagnostics import Diagnostic, has_errors
from .ir_lowering import IRLowerer
from .ir_nodes import IRModule
from .ir_transforms.normalize import normalize_module
from .ir_transforms.prune import warn_unreferenced
from .ir_transforms.resolve_vars import resolve_constants
from .lexer_parser import parse_source
from .semantic_analyzer import SemanticAnalyzer
from .serialization import ast_to_json, ir_to_json


Target = Literal["aws", "gcp", "azure", "all"]


@dataclass
class SourceCompileResult:
    success: bool
    diagnostics: list[Diagnostic]
    ast: dict[str, object] | None
    ir: dict[str, object] | None
    generated: dict[str, str | None]
    report: dict[str, object]
    module: IRModule | None = None


def compile_source(source: str, target: Target = "all", filename: str | None = "<editor>") -> SourceCompileResult:
    diagnostics: list[Diagnostic] = []
    timings: dict[str, float] = {}
    generated: dict[str, str | None] = {"aws": None, "gcp": None, "azure": None}
    outputs: dict[str, GeneratedOutput] = {}
    app = None
    module = None

    t = time.perf_counter()
    app, parse_diags = parse_source(source, filename)
    timings["lex_parse"] = _ms(t)
    diagnostics.extend(parse_diags)
    if app is None or has_errors(diagnostics):
        return _result(False, diagnostics, ast_to_json(app), None, generated, timings, outputs, module)

    t = time.perf_counter()
    table, semantic_diags = SemanticAnalyzer().analyze(app)
    timings["semantic"] = _ms(t)
    diagnostics.extend(semantic_diags)
    if has_errors(diagnostics):
        return _result(False, diagnostics, ast_to_json(app), None, generated, timings, outputs, module)

    t = time.perf_counter()
    module, lower_diags = IRLowerer().lower(app, table)
    module = normalize_module(resolve_constants(module))
    diagnostics.extend(lower_diags)
    diagnostics.extend(warn_unreferenced(module))
    timings["ir"] = _ms(t)

    targets = list(BACKENDS) if target == "all" else [target]
    for tgt in targets:
        t = time.perf_counter()
        capability_diags = check_capabilities(module, tgt)
        diagnostics.extend(capability_diags)
        if not any(d.severity == "error" for d in capability_diags):
            output = BACKENDS[tgt]().generate(module)
            outputs[tgt] = output
            generated[tgt] = output.text
        timings[f"codegen_{tgt}"] = _ms(t)

    return _result(not has_errors(diagnostics), diagnostics, ast_to_json(app), ir_to_json(module), generated, timings, outputs, module)


def _result(
    success: bool,
    diagnostics: list[Diagnostic],
    ast: dict[str, object] | None,
    ir: dict[str, object] | None,
    generated: dict[str, str | None],
    timings: dict[str, float],
    outputs: dict[str, GeneratedOutput],
    module: IRModule | None,
) -> SourceCompileResult:
    counts: dict[str, int] = {}
    if module:
        for res in module.resources:
            counts[res.ir_type] = counts.get(res.ir_type, 0) + 1
    return SourceCompileResult(
        success=success,
        diagnostics=diagnostics,
        ast=ast,
        ir=ir,
        generated=generated,
        report={
            "phase_timings_ms": timings,
            "resource_counts": counts,
            "backend_reports": {target: output.report for target, output in outputs.items()},
        },
        module=module,
    )


def _ms(start: float) -> float:
    return round((time.perf_counter() - start) * 1000, 3)
