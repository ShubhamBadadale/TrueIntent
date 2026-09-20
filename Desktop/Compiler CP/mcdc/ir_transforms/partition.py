from __future__ import annotations

from mcdc.ir_nodes import IRModule, IRResource


PORTABLE = {"Compute", "Network", "Subnet", "Storage", "Firewall"}


def partition_portable(module: IRModule) -> tuple[list[IRResource], list[IRResource]]:
    return ([r for r in module.resources if r.ir_type in PORTABLE], [r for r in module.resources if r.ir_type not in PORTABLE])
