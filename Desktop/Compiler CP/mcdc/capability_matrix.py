from __future__ import annotations

from dataclasses import dataclass

from .diagnostics import Diagnostic
from .ir_nodes import IRModule


@dataclass(frozen=True)
class ResourceMapping:
    terraform_types: tuple[str, ...]


CAPABILITY_MATRIX: dict[str, dict[str, ResourceMapping]] = {
    "Compute": {
        "aws": ResourceMapping(("aws_instance",)),
        "gcp": ResourceMapping(("google_compute_instance",)),
        "azure": ResourceMapping(("azurerm_linux_virtual_machine",)),
    },
    "Network": {
        "aws": ResourceMapping(("aws_vpc",)),
        "gcp": ResourceMapping(("google_compute_network",)),
        "azure": ResourceMapping(("azurerm_virtual_network",)),
    },
    "Subnet": {
        "aws": ResourceMapping(("aws_subnet",)),
        "gcp": ResourceMapping(("google_compute_subnetwork",)),
        "azure": ResourceMapping(("azurerm_subnet",)),
    },
    "Storage": {
        "aws": ResourceMapping(("aws_s3_bucket",)),
        "gcp": ResourceMapping(("google_storage_bucket",)),
        "azure": ResourceMapping(("azurerm_storage_account", "azurerm_storage_container")),
    },
    "Firewall": {
        "aws": ResourceMapping(("aws_security_group",)),
        "gcp": ResourceMapping(("google_compute_firewall",)),
        "azure": ResourceMapping(("azurerm_network_security_group",)),
    },
    "GpuCluster": {"aws": ResourceMapping(("aws_eks_node_group",))},
}


def check_capabilities(module: IRModule, target: str) -> list[Diagnostic]:
    diags: list[Diagnostic] = []
    for res in module.resources:
        supported = CAPABILITY_MATRIX.get(res.ir_type, {})
        if target not in supported:
            targets = ", ".join(sorted(supported)) or "none"
            diags.append(Diagnostic("error", "C001", f'resource type "{res.ir_type}" has no mapping for target "{target}"', res.source_loc, "capability", f"supported targets for {res.ir_type}: {targets}"))
    return diags
