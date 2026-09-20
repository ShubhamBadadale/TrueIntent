from __future__ import annotations

from mcdc.ir_nodes import IRModule, IRResource
from mcdc.ir_transforms.dependency_graph import ordered_resources
from .base import GeneratedOutput, hcl_string, name_from_ir


class AwsBackend:
    target = "aws"

    def generate(self, module: IRModule) -> GeneratedOutput:
        resources, diags = ordered_resources(module)
        self.by_id = {r.ir_id: r for r in resources}
        parts = ['terraform {\n  required_providers {\n    aws = {\n      source = "hashicorp/aws"\n    }\n  }\n}\n', 'provider "aws" {\n  region = "us-east-1"\n}\n']
        for res in resources:
            parts.append(self._resource(res))
        return GeneratedOutput("\n".join(parts), {"target": self.target, "resources": [r.ir_id for r in resources], "diagnostics": [d.to_dict() for d in diags]})

    def _resource(self, res: IRResource) -> str:
        name = name_from_ir(res.ir_id)
        if res.ir_type == "Network":
            return f'resource "aws_vpc" "{name}" {{\n  cidr_block = {hcl_string(res.attributes["cidr"])}\n  tags = {{ Name = {hcl_string(name)} }}\n}}\n'
        if res.ir_type == "Subnet":
            vpc = self._first(res.depends_on, "network")
            return f'resource "aws_subnet" "{name}" {{\n  vpc_id = aws_vpc.{vpc}.id\n  cidr_block = {hcl_string(res.attributes["cidr"])}\n  tags = {{ Name = {hcl_string(name)} }}\n}}\n'
        if res.ir_type == "Compute":
            subnet = self._first(res.depends_on, "subnet")
            return f'resource "aws_instance" "{name}" {{\n  ami = {hcl_string(res.attributes["image"])}\n  instance_type = "t3.micro"\n  subnet_id = aws_subnet.{subnet}.id\n  tags = {{ Name = {hcl_string(name)} }}\n}}\n'
        if res.ir_type == "Storage":
            return f'resource "aws_s3_bucket" "{name}" {{\n  bucket = "{name}-${{random_id.suffix.hex}}"\n}}\n\nresource "random_id" "suffix" {{\n  byte_length = 4\n}}\n'
        if res.ir_type == "Firewall":
            vpc = self._first(res.depends_on, "network")
            ingress = "\n".join(f'  ingress {{\n    from_port = {r["port"]}\n    to_port = {r["port"]}\n    protocol = {hcl_string(r["protocol"])}\n    cidr_blocks = [{hcl_string(r["source"])}]\n  }}' for r in res.attributes.get("allow", []))
            return f'resource "aws_security_group" "{name}" {{\n  name = {hcl_string(name)}\n  vpc_id = aws_vpc.{vpc}.id\n{ingress}\n  egress {{\n    from_port = 0\n    to_port = 0\n    protocol = "-1"\n    cidr_blocks = ["0.0.0.0/0"]\n  }}\n}}\n'
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
