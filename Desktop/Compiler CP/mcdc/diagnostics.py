from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal


@dataclass(frozen=True)
class SourceLoc:
    line: int
    column: int
    file: str | None = None

    def display(self) -> str:
        path = self.file or "<source>"
        return f"{path}:{self.line}:{self.column}"


@dataclass(frozen=True)
class Diagnostic:
    severity: Literal["error", "warning"]
    code: str
    message: str
    loc: SourceLoc | None = None
    phase: str = "general"
    hint: str | None = None

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        return data

    def format(self) -> str:
        head = f"{self.severity}[{self.code}]: {self.message}"
        if self.loc:
            head += f"\n  --> {self.loc.display()}"
        if self.hint:
            head += f"\nhint: {self.hint}"
        return head


def has_errors(diagnostics: list[Diagnostic]) -> bool:
    return any(d.severity == "error" for d in diagnostics)
