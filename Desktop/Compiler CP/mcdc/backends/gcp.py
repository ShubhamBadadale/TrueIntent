from __future__ import annotations

from mcdc.ir_nodes import IRModule, IRResource
from mcdc.ir_transforms.dependency_graph import ordered_resources
from .base import GeneratedOutput, hcl_string, name_from_ir


class GcpBackend:
    target = "gcp"

    def generate(self, module: IRModule) -> GeneratedOutput:
        resources, diags = ordered_resources(module)
        self.by_id = {r.ir_id: r for r in resources}
        parts = ['terraform {\n  required_providers {\n    google = {\n      source = "hashicorp/google"\n    }\n  }\n}\n', 'provider "google" {\n  project = "example-project"\n  region = "us-central1"\n}\n']
        for res in resources:
            parts.append(self._resource(res))
        return GeneratedOutput("\n".join(parts), {"target": self.target, "resources": [r.ir_id for r in resources], "diagnostics": [d.to_dict() for d in diags]})

    def _resource(self, res: IRResource) -> str:
        name = name_from_ir(res.ir_id)
        if res.ir_type == "Network":
            return f'resource "google_compute_network" "{name}" {{\n  name = {hcl_string(name)}\n  auto_create_subnetworks = false\n}}\n'
        if res.ir_type == "Subnet":
            network = self._first(res.depends_on, "network")
            return f'resource "google_compute_subnetwork" "{name}" {{\n  name = {hcl_string(name)}\n  ip_cidr_range = {hcl_string(res.attributes["cidr"])}\n  region = "us-central1"\n  network = google_compute_network.{network}.id\n}}\n'
        if res.ir_type == "Compute":
            subnet = self._first(res.depends_on, "subnet")
            return f'resource "google_compute_instance" "{name}" {{\n  name = {hcl_string(name)}\n  machine_type = "e2-micro"\n  zone = "us-central1-a"\n  boot_disk {{ initialize_params {{ image = {hcl_string(res.attributes["image"])} }} }}\n  network_interface {{ subnetwork = google_compute_subnetwork.{subnet}.id }}\n}}\n'
        if res.ir_type == "Storage":
            return f'resource "google_storage_bucket" "{name}" {{\n  name = "{name}-${{random_id.suffix.hex}}"\n  location = "US"\n}}\n\nresource "random_id" "suffix" {{\n  byte_length = 4\n}}\n'
        if res.ir_type == "Firewall":
            network = self._first(res.depends_on, "network")
            allows = "\n".join(f'  allow {{\n    protocol = {hcl_string(r["protocol"])}\n    ports = [{hcl_string(r["port"])}]\n  }}' for r in res.attributes.get("allow", []))
            sources = ", ".join(hcl_string(r["source"]) for r in res.attributes.get("allow", []))
            return f'resource "google_compute_firewall" "{name}" {{\n  name = {hcl_string(name)}\n  network = google_compute_network.{network}.name\n{allows}\n  source_ranges = [{sources}]\n}}\n'
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
