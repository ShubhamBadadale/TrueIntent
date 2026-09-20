from __future__ import annotations

import ipaddress

from mcdc.ir_nodes import IRModule


def normalize_module(module: IRModule) -> IRModule:
    for res in module.resources:
        if "cidr" in res.attributes:
            res.attributes["cidr"] = str(ipaddress.ip_network(res.attributes["cidr"], strict=False))
        if res.ir_type == "Firewall":
            for rule in res.attributes.get("allow", []):
                if "protocol" in rule:
                    rule["protocol"] = str(rule["protocol"]).lower()
    return module
