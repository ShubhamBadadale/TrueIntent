from mcdc.lexer_parser import parse_source
from mcdc.semantic_analyzer import SemanticAnalyzer


def analyze(src: str):
    app, parse_diags = parse_source(src)
    assert parse_diags == []
    assert app is not None
    _, diags = SemanticAnalyzer().analyze(app)
    return diags


def test_duplicate_and_undefined_dependency_errors():
    diags = analyze('cloud app "A" { network "main" { cidr = "10.0.0.0/16" } network "main" { cidr = "10.1.0.0/16" } compute "web" { image = "u" cpu = 1 memory = 1 depends_on = ["missing"] } }')
    codes = {d.code for d in diags}
    assert {"E101", "E203"} <= codes


def test_type_required_cycle_and_legal_combo_errors():
    diags = analyze('cloud app "A" { subnet "s" { cidr = "bad" depends_on = ["c"] } compute "c" { image = "u" cpu = "two" memory = 1 depends_on = ["s"] } firewall "f" { allow = [{ port = 70000, protocol = "icmp", source = "bad" }] } }')
    codes = {d.code for d in diags}
    assert {"E302", "E304", "E306", "E307", "E309", "E401", "E205"} <= codes


def test_undefined_variable_error():
    diags = analyze('cloud app "A" { compute "web" { image = ${img} cpu = 1 memory = 1 } }')
    assert "E202" in {d.code for d in diags}
