from pathlib import Path

from mcdc.compiler import compile_file


def test_unsupported_resource_reports_capability_error():
    result = compile_file(Path("examples/negative_unsupported_resource.mcd"), "azure")
    assert "C001" in {d.code for d in result.diagnostics}
    assert result.outputs == {}
