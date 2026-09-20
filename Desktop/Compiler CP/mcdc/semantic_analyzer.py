from __future__ import annotations

import ipaddress

from .ast_nodes import Attribute, AstValue, CloudAppNode, IntValue, ListValue, ObjectValue, ResourceNode, StringValue, VarRef
from .diagnostics import Diagnostic
from .symbol_table import SymbolTable


REQUIRED = {
    "network": {"cidr"},
    "subnet": {"cidr", "depends_on"},
    "compute": {"image", "cpu", "memory"},
    "storage": {"size"},
    "firewall": {"allow"},
}


class SemanticAnalyzer:
    def analyze(self, app: CloudAppNode) -> tuple[SymbolTable, list[Diagnostic]]:
        table, diagnostics = SymbolTable.build(app.resources, app.variables)
        diagnostics.extend(self._validate_resources(app.resources, table))
        diagnostics.extend(self._validate_var_refs(app, table))
        diagnostics.extend(self._validate_cycles(app.resources))
        return table, diagnostics

    def _validate_resources(self, resources: list[ResourceNode], table: SymbolTable) -> list[Diagnostic]:
        diags: list[Diagnostic] = []
        for res in resources:
            attrs = {a.name: a for a in res.attributes}
            if res.kind not in REQUIRED:
                continue
            for req in sorted(REQUIRED[res.kind] - set(attrs)):
                diags.append(Diagnostic("error", "E301", f'{res.kind} "{res.name}" missing required attribute "{req}"', res.loc, "semantic"))
            for dep in res.depends_on:
                if dep not in table.resources:
                    diags.append(Diagnostic("error", "E203", f'undefined reference to resource "{dep}" in {res.kind} "{res.name}".depends_on', res.loc, "semantic"))
                elif dep == res.name:
                    diags.append(Diagnostic("error", "E204", f'{res.kind} "{res.name}" cannot depend on itself', res.loc, "semantic"))
            diags.extend(self._validate_types(res, attrs, table))
        return diags

    def _validate_types(self, res: ResourceNode, attrs: dict[str, Attribute], table: SymbolTable) -> list[Diagnostic]:
        diags: list[Diagnostic] = []
        for name in ("cidr",):
            if name in attrs and isinstance(attrs[name].value, StringValue):
                try:
                    ipaddress.ip_network(attrs[name].value.value, strict=False)
                except ValueError:
                    diags.append(Diagnostic("error", "E302", f'invalid CIDR "{attrs[name].value.value}"', attrs[name].loc, "semantic"))
            elif name in attrs:
                diags.append(Diagnostic("error", "E303", f'attribute "{name}" must be a string CIDR', attrs[name].loc, "semantic"))
        for name in ("cpu", "memory", "size"):
            if name in attrs and not isinstance(attrs[name].value, (IntValue, VarRef)):
                diags.append(Diagnostic("error", "E304", f'attribute "{name}" must be an integer', attrs[name].loc, "semantic"))
        if "allow" in attrs and isinstance(attrs["allow"].value, ListValue):
            for rule in attrs["allow"].value.values:
                if not isinstance(rule, ObjectValue):
                    diags.append(Diagnostic("error", "E305", "firewall allow entries must be objects", attrs["allow"].loc, "semantic"))
                    continue
                vals = rule.values
                port = vals.get("port")
                protocol = vals.get("protocol")
                source = vals.get("source")
                if not isinstance(port, IntValue) or not 0 <= port.value <= 65535:
                    diags.append(Diagnostic("error", "E306", "firewall port must be an integer from 0 to 65535", rule.loc, "semantic"))
                if not isinstance(protocol, StringValue) or protocol.value.lower() not in {"tcp", "udp"}:
                    diags.append(Diagnostic("error", "E307", 'firewall protocol must be "tcp" or "udp"', rule.loc, "semantic"))
                if not isinstance(source, StringValue):
                    diags.append(Diagnostic("error", "E308", "firewall source must be a CIDR string", rule.loc, "semantic"))
                else:
                    try:
                        ipaddress.ip_network(source.value, strict=False)
                    except ValueError:
                        diags.append(Diagnostic("error", "E309", f'invalid firewall source CIDR "{source.value}"', rule.loc, "semantic"))
        if res.kind == "subnet":
            network_deps = [table.resources[d].kind for d in res.depends_on if d in table.resources]
            if "network" not in network_deps:
                diags.append(Diagnostic("error", "E401", f'subnet "{res.name}" must depend_on an existing network', res.loc, "semantic"))
        return diags

    def _validate_var_refs(self, app: CloudAppNode, table: SymbolTable) -> list[Diagnostic]:
        diags: list[Diagnostic] = []
        def walk(value: AstValue) -> None:
            if isinstance(value, VarRef) and value.name not in table.variables:
                diags.append(Diagnostic("error", "E202", f'undefined variable "{value.name}"', value.loc, "semantic"))
            elif isinstance(value, ListValue):
                for item in value.values:
                    walk(item)
            elif isinstance(value, ObjectValue):
                for item in value.values.values():
                    walk(item)
        for res in app.resources:
            for attr in res.attributes:
                walk(attr.value)
        return diags

    def _validate_cycles(self, resources: list[ResourceNode]) -> list[Diagnostic]:
        graph = {r.name: list(r.depends_on) for r in resources}
        visiting: set[str] = set()
        visited: set[str] = set()
        diags: list[Diagnostic] = []
        locs = {r.name: r.loc for r in resources}

        def dfs(name: str, trail: list[str]) -> None:
            if name in visiting:
                cycle = " -> ".join(trail + [name])
                diags.append(Diagnostic("error", "E205", f"dependency cycle detected: {cycle}", locs.get(name), "semantic"))
                return
            if name in visited:
                return
            visiting.add(name)
            for dep in graph.get(name, []):
                if dep in graph:
                    dfs(dep, trail + [name])
            visiting.remove(name)
            visited.add(name)

        for name in graph:
            dfs(name, [])
        return diags
