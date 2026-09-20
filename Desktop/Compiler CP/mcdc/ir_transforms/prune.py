from __future__ import annotations

from mcdc.diagnostics import Diagnostic
from mcdc.ir_nodes import IRModule


def warn_unreferenced(module: IRModule) -> list[Diagnostic]:
    depended = {dep for res in module.resources for dep in res.depends_on}
    warnings: list[Diagnostic] = []
    for res in module.resources:
        if res.ir_type in {"Storage"} and res.ir_id not in depended:
            warnings.append(Diagnostic("warning", "I301", f'resource "{res.ir_id}" is not depended on by another resource', res.source_loc, "ir"))
    return warnings
