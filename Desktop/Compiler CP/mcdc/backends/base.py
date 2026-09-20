from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from mcdc.ir_nodes import IRModule


@dataclass
class GeneratedOutput:
    text: str
    report: dict[str, object]


class Backend(Protocol):
    target: str

    def generate(self, module: IRModule) -> GeneratedOutput:
        ...


def hcl_string(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    return '"' + str(value).replace('"', '\\"') + '"'


def name_from_ir(ir_id: str) -> str:
    return ir_id.split(".", 1)[1]
