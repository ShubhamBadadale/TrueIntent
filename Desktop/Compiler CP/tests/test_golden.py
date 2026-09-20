from pathlib import Path

from mcdc.compiler import compile_file


def test_static_web_server_golden_outputs():
    result = compile_file(Path("examples/static_web_server.mcd"), "all")
    for target, output in result.outputs.items():
        expected = Path(f"tests/golden/static_web_server.{target}.tf").read_text()
        assert output.text == expected
