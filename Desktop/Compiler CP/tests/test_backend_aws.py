from pathlib import Path

from mcdc.compiler import compile_file


def test_aws_backend_generates_references():
    result = compile_file(Path("examples/static_web_server.mcd"), "aws")
    text = result.outputs["aws"].text
    assert 'resource "aws_vpc" "main"' in text
    assert "vpc_id = aws_vpc.main.id" in text
    assert "subnet_id = aws_subnet.public.id" in text
