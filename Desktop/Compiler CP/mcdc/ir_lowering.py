from __future__ import annotations

from typing import Any

from .ast_nodes import AstValue, BoolValue, CloudAppNode, IntValue, ListValue, ObjectValue, StringValue, VarRef
from .diagnostics import Diagnostic
from .ir_nodes import IRModule, IRResource
from .symbol_table import SymbolTable


TYPE_MAP = {"network": "Network", "subnet": "Subnet", "compute": "Compute", "storage": "Storage", "firewall": "Firewall", "gpu_cluster": "GpuCluster"}


class IRLowerer:
    def lower(self, app: CloudAppNode, table: SymbolTable) -> tuple[IRModule, list[Diagnostic]]:
        resources: list[IRResource] = []
        name_to_ir = {r.name: f"{r.kind}.{self._safe(r.name)}" for r in app.resources}
        for res in app.resources:
            attrs = {attr.name: self._value(attr.value, table) for attr in res.attributes if attr.name != "depends_on"}
            resources.append(IRResource(name_to_ir[res.name], TYPE_MAP.get(res.kind, self._camel(res.kind)), attrs, [name_to_ir[d] for d in res.depends_on if d in name_to_ir], res.loc))
        return IRModule(app.name, resources), []

    def _value(self, value: AstValue, table: SymbolTable) -> Any:
        if isinstance(value, StringValue):
            return value.value
        if isinstance(value, IntValue):
            return value.value
        if isinstance(value, BoolValue):
            return value.value
        if isinstance(value, VarRef):
            return self._value(table.variables[value.name].value, table)
        if isinstance(value, ListValue):
            return [self._value(v, table) for v in value.values]
        if isinstance(value, ObjectValue):
            return {k: self._value(v, table) for k, v in value.values.items()}
        raise TypeError(value)

    def _safe(self, name: str) -> str:
        return "".join(ch if ch.isalnum() or ch == "_" else "_" for ch in name)

    def _camel(self, name: str) -> str:
        return "".join(part[:1].upper() + part[1:] for part in name.replace("-", "_").split("_") if part)
