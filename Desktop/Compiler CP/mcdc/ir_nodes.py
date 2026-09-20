from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .diagnostics import SourceLoc


@dataclass
class IRResource:
    ir_id: str
    ir_type: str
    attributes: dict[str, Any]
    depends_on: list[str]
    source_loc: SourceLoc


@dataclass
class IRModule:
    app_name: str
    resources: list[IRResource]
