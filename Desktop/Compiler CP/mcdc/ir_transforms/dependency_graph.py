from __future__ import annotations

from collections import deque

from mcdc.diagnostics import Diagnostic
from mcdc.ir_nodes import IRModule


def build_graph(module: IRModule) -> dict[str, list[str]]:
    return {r.ir_id: list(r.depends_on) for r in module.resources}


def topological_order(module: IRModule) -> tuple[list[str], list[Diagnostic]]:
    graph = build_graph(module)
    indegree = {node: 0 for node in graph}
    outgoing = {node: [] for node in graph}
    for node, deps in graph.items():
        for dep in deps:
            if dep in indegree:
                indegree[node] += 1
                outgoing[dep].append(node)
    q = deque([n for n, deg in indegree.items() if deg == 0])
    order: list[str] = []
    while q:
        n = q.popleft()
        order.append(n)
        for child in outgoing[n]:
            indegree[child] -= 1
            if indegree[child] == 0:
                q.append(child)
    if len(order) != len(graph):
        return order, [Diagnostic("error", "I201", "dependency cycle detected during IR topological sort", None, "ir")]
    return order, []


def ordered_resources(module: IRModule):
    order, diags = topological_order(module)
    by_id = {r.ir_id: r for r in module.resources}
    return [by_id[i] for i in order if i in by_id], diags
