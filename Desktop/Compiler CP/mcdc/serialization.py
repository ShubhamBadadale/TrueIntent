from __future__ import annotations

from typing import Any

from .ast_nodes import Attribute, AstValue, BoolValue, CloudAppNode, IntValue, ListValue, ObjectValue, ResourceNode, StringValue, VarDecl, VarRef
from .diagnostics import SourceLoc
from .ir_nodes import IRModule


def loc_to_dict(loc: SourceLoc | None) -> dict[str, Any] | None:
    if loc is None:
        return None
    return {"line": loc.line, "column": loc.column, "file": loc.file}


def ast_to_json(app: CloudAppNode | None) -> dict[str, Any] | None:
    if app is None:
        return None
    return {
        "type": "CloudApp",
        "name": app.name,
        "loc": loc_to_dict(app.loc),
        "children": [_var_to_json(v) for v in app.variables] + [_resource_to_json(r) for r in app.resources],
    }


def ir_to_json(module: IRModule | None) -> dict[str, Any] | None:
    if module is None:
        return None
    nodes = [
        {
            "id": res.ir_id,
            "type": res.ir_type,
            "label": f"{res.ir_type}: {res.ir_id}",
            "attributes": res.attributes,
            "loc": loc_to_dict(res.source_loc),
        }
        for res in module.resources
    ]
    edges = [{"from": dep, "to": res.ir_id, "kind": "depends_on"} for res in module.resources for dep in res.depends_on]
    return {"appName": module.app_name, "nodes": nodes, "edges": edges}


def _resource_to_json(res: ResourceNode) -> dict[str, Any]:
    return {
        "type": "Resource",
        "kind": res.kind,
        "name": res.name,
        "dependsOn": res.depends_on,
        "loc": loc_to_dict(res.loc),
        "children": [_attr_to_json(a) for a in res.attributes],
    }


def _var_to_json(var: VarDecl) -> dict[str, Any]:
    return {"type": "VarDecl", "name": var.name, "value": _value_to_json(var.value), "loc": loc_to_dict(var.loc), "children": []}


def _attr_to_json(attr: Attribute) -> dict[str, Any]:
    return {"type": "Attribute", "name": attr.name, "value": _value_to_json(attr.value), "loc": loc_to_dict(attr.loc), "children": []}


def _value_to_json(value: AstValue) -> dict[str, Any]:
    if isinstance(value, StringValue):
        return {"type": "String", "value": value.value, "loc": loc_to_dict(value.loc)}
    if isinstance(value, IntValue):
        return {"type": "Int", "value": value.value, "loc": loc_to_dict(value.loc)}
    if isinstance(value, BoolValue):
        return {"type": "Bool", "value": value.value, "loc": loc_to_dict(value.loc)}
    if isinstance(value, VarRef):
        return {"type": "VarRef", "name": value.name, "loc": loc_to_dict(value.loc)}
    if isinstance(value, ListValue):
        return {"type": "List", "values": [_value_to_json(v) for v in value.values], "loc": loc_to_dict(value.loc)}
    if isinstance(value, ObjectValue):
        return {"type": "Object", "values": {k: _value_to_json(v) for k, v in value.values.items()}, "loc": loc_to_dict(value.loc)}
    raise TypeError(value)
