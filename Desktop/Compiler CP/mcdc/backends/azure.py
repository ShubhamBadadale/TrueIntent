from __future__ import annotations

from mcdc.ir_nodes import IRModule, IRResource
from mcdc.ir_transforms.dependency_graph import ordered_resources
from .base import GeneratedOutput, hcl_string, name_from_ir


class AzureBackend:
    target = "azure"

    def generate(self, module: IRModule) -> GeneratedOutput:
        resources, diags = ordered_resources(module)
        self.by_id = {r.ir_id: r for r in resources}
        parts = ['terraform {\n  required_providers {\n    azurerm = {\n      source = "hashicorp/azurerm"\n    }\n  }\n}\n', 'provider "azurerm" {\n  features {}\n}\n', 'resource "azurerm_resource_group" "main" {\n  name = "mcdc-rg"\n  location = "East US"\n}\n']
        for res in resources:
            parts.append(self._resource(res))
        return GeneratedOutput("\n".join(parts), {"target": self.target, "resources": [r.ir_id for r in resources], "diagnostics": [d.to_dict() for d in diags]})

    def _resource(self, res: IRResource) -> str:
        name = name_from_ir(res.ir_id)
        if res.ir_type == "Network":
            return f'resource "azurerm_virtual_network" "{name}" {{\n  name = {hcl_string(name)}\n  address_space = [{hcl_string(res.attributes["cidr"])}]\n  location = azurerm_resource_group.main.location\n  resource_group_name = azurerm_resource_group.main.name\n}}\n'
        if res.ir_type == "Subnet":
            network = self._first(res.depends_on, "network")
            return f'resource "azurerm_subnet" "{name}" {{\n  name = {hcl_string(name)}\n  resource_group_name = azurerm_resource_group.main.name\n  virtual_network_name = azurerm_virtual_network.{network}.name\n  address_prefixes = [{hcl_string(res.attributes["cidr"])}]\n}}\n'
        if res.ir_type == "Compute":
            subnet = self._first(res.depends_on, "subnet")
            return f'resource "azurerm_network_interface" "{name}" {{\n  name = "{name}-nic"\n  location = azurerm_resource_group.main.location\n  resource_group_name = azurerm_resource_group.main.name\n  ip_configuration {{\n    name = "internal"\n    subnet_id = azurerm_subnet.{subnet}.id\n    private_ip_address_allocation = "Dynamic"\n  }}\n}}\n\nresource "azurerm_linux_virtual_machine" "{name}" {{\n  name = {hcl_string(name)}\n  resource_group_name = azurerm_resource_group.main.name\n  location = azurerm_resource_group.main.location\n  size = "Standard_B1s"\n  admin_username = "adminuser"\n  network_interface_ids = [azurerm_network_interface.{name}.id]\n  admin_ssh_key {{ username = "adminuser" public_key = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQDexample" }}\n  os_disk {{ caching = "ReadWrite" storage_account_type = "Standard_LRS" }}\n  source_image_reference {{ publisher = "Canonical" offer = "0001-com-ubuntu-server-jammy" sku = "22_04-lts" version = "latest" }}\n}}\n'
        if res.ir_type == "Storage":
            return f'resource "azurerm_storage_account" "{name}" {{\n  name = "{name}${{random_id.suffix.hex}}"\n  resource_group_name = azurerm_resource_group.main.name\n  location = azurerm_resource_group.main.location\n  account_tier = "Standard"\n  account_replication_type = "LRS"\n}}\n\nresource "azurerm_storage_container" "{name}" {{\n  name = "data"\n  storage_account_name = azurerm_storage_account.{name}.name\n  container_access_type = "private"\n}}\n\nresource "random_id" "suffix" {{\n  byte_length = 4\n}}\n'
        if res.ir_type == "Firewall":
            rules = "\n".join(f'resource "azurerm_network_security_rule" "{name}_{r["port"]}" {{\n  name = "{name}-{r["port"]}"\n  priority = {100 + i}\n  direction = "Inbound"\n  access = "Allow"\n  protocol = "{str(r["protocol"]).title()}"\n  source_port_range = "*"\n  destination_port_range = "{r["port"]}"\n  source_address_prefix = {hcl_string(r["source"])}\n  destination_address_prefix = "*"\n  resource_group_name = azurerm_resource_group.main.name\n  network_security_group_name = azurerm_network_security_group.{name}.name\n}}\n' for i, r in enumerate(res.attributes.get("allow", [])))
            return f'resource "azurerm_network_security_group" "{name}" {{\n  name = {hcl_string(name)}\n  location = azurerm_resource_group.main.location\n  resource_group_name = azurerm_resource_group.main.name\n}}\n\n{rules}'
        return ""

    def _first(self, deps: list[str], prefix: str) -> str:
        seen: set[str] = set()
        return self._find(deps, prefix, seen) or "main"

    def _find(self, deps: list[str], prefix: str, seen: set[str]) -> str | None:
        for dep in deps:
            if dep.startswith(prefix + "."):
                return name_from_ir(dep)
            if dep not in seen and dep in self.by_id:
                seen.add(dep)
                found = self._find(self.by_id[dep].depends_on, prefix, seen)
                if found:
                    return found
        return None
