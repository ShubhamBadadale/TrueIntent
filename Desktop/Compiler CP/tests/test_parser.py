from mcdc.lexer_parser import parse_source


def test_parser_builds_ast():
    app, diagnostics = parse_source('cloud app "A" { network "main" { cidr = "10.0.0.0/16" } }')
    assert diagnostics == []
    assert app is not None
    assert app.resources[0].kind == "network"
