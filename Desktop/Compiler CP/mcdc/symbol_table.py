from __future__ import annotations

from dataclasses import dataclass

from .ast_nodes import ResourceNode, VarDecl
from .diagnostics import Diagnostic


@dataclass
class SymbolTable:
    resources: dict[str, ResourceNode]
    variables: dict[str, VarDecl]

    @classmethod
    def build(cls, resources: list[ResourceNode], variables: list[VarDecl]) -> tuple["SymbolTable", list[Diagnostic]]:
        diagnostics: list[Diagnostic] = []
        res: dict[str, ResourceNode] = {}
        vars_: dict[str, VarDecl] = {}
        for node in resources:
            if node.name in res:
                diagnostics.append(Diagnostic("error", "E101", f'duplicate resource name "{node.name}"', node.loc, "semantic"))
            else:
                res[node.name] = node
        for var in variables:
            if var.name in vars_:
                diagnostics.append(Diagnostic("error", "E102", f'duplicate variable name "{var.name}"', var.loc, "semantic"))
            else:
                vars_[var.name] = var
        return cls(res, vars_), diagnostics
