from mcdc.lexer_parser import Lexer


def test_lexer_tracks_tokens_and_comments():
    tokens, diagnostics = Lexer('cloud app "A" { // hi\n var x = 1; }').lex()
    assert diagnostics == []
    assert [t.type for t in tokens[:5]] == ["CLOUD", "APP", "STRING", "{", "VAR"]
