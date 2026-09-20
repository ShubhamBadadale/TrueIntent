from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

from .backends.aws import AwsBackend
from .backends.azure import AzureBackend
from .backends.base import GeneratedOutput
from .backends.gcp import GcpBackend
from .capability_matrix import check_capabilities
from .diagnostics import Diagnostic, has_errors
from .ir_lowering import IRLowerer
from .ir_nodes import IRModule
from .ir_transforms.normalize import normalize_module
from .ir_transforms.prune import warn_unreferenced
from .ir_transforms.resolve_vars import resolve_constants
from .lexer_parser import parse_source
from .semantic_analyzer import SemanticAnalyzer


BACKENDS = {"aws": AwsBackend, "gcp": GcpBackend, "azure": AzureBackend}


@dataclass
class CompileResult:
    module: IRModule | None
    outputs: dict[str, GeneratedOutput]
    diagnostics: list[Diagnostic]
    timings: dict[str, float]


def build_ir(path: Path) -> tuple[IRModule | None, list[Diagnostic], dict[str, float]]:
    timings: dict[str, float] = {}
    source = path.read_text()
    t = time.perf_counter()
    app, diagnostics = parse_source(source, str(path))
    timings["lex_parse"] = time.perf_counter() - t
    if app is None:
        return None, diagnostics, timings
    t = time.perf_counter()
    table, semantic_diags = SemanticAnalyzer().analyze(app)
    timings["semantic"] = time.perf_counter() - t
    diagnostics.extend(semantic_diags)
    if has_errors(diagnostics):
        return None, diagnostics, timings
    t = time.perf_counter()
    module, lower_diags = IRLowerer().lower(app, table)
    module = normalize_module(resolve_constants(module))
    diagnostics.extend(lower_diags)
    diagnostics.extend(warn_unreferenced(module))
    timings["ir"] = time.perf_counter() - t
    return module, diagnostics, timings


def compile_file(path: Path, target: str) -> CompileResult:
    module, diagnostics, timings = build_ir(path)
    outputs: dict[str, GeneratedOutput] = {}
    if module is None or has_errors(diagnostics):
        return CompileResult(module, outputs, diagnostics, timings)
    targets = list(BACKENDS) if target == "all" else [target]
    for tgt in targets:
        t = time.perf_counter()
        diagnostics.extend(check_capabilities(module, tgt))
        if has_errors(diagnostics):
            continue
        outputs[tgt] = BACKENDS[tgt]().generate(module)
        timings[f"codegen_{tgt}"] = time.perf_counter() - t
    return CompileResult(module, outputs, diagnostics, timings)
