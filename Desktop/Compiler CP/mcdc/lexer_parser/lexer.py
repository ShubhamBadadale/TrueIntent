from __future__ import annotations

from dataclasses import dataclass

from mcdc.diagnostics import Diagnostic, SourceLoc


KEYWORDS = {"cloud", "app", "network", "subnet", "compute", "storage", "firewall", "var", "true", "false"}
SYMBOLS = {"{", "}", "[", "]", "=", ",", ";"}


@dataclass(frozen=True)
class Token:
    type: str
    value: str
    loc: SourceLoc


class Lexer:
    def __init__(self, source: str, filename: str | None = None):
        self.source = source
        self.filename = filename
        self.i = 0
        self.line = 1
        self.col = 1
        self.diagnostics: list[Diagnostic] = []

    def lex(self) -> tuple[list[Token], list[Diagnostic]]:
        tokens: list[Token] = []
        while not self._eof():
            ch = self._peek()
            if ch in " \t\r\n":
                self._advance_ws()
            elif ch == "/" and self._peek(1) == "/":
                self._line_comment()
            elif ch == "/" and self._peek(1) == "*":
                self._block_comment()
            elif ch == '"':
                tokens.append(self._string())
            elif ch.isdigit():
                tokens.append(self._int())
            elif ch.isalpha() or ch == "_":
                tokens.append(self._ident())
            elif ch == "$" and self._peek(1) == "{":
                loc = self._loc()
                self._advance()
                self._advance()
                tokens.append(Token("REF_START", "${", loc))
            elif ch in SYMBOLS:
                loc = self._loc()
                self._advance()
                tokens.append(Token(ch, ch, loc))
            else:
                self.diagnostics.append(Diagnostic("error", "L001", f"unexpected character {ch!r}", self._loc(), "lexer"))
                self._advance()
        tokens.append(Token("EOF", "", self._loc()))
        return tokens, self.diagnostics

    def _loc(self) -> SourceLoc:
        return SourceLoc(self.line, self.col, self.filename)

    def _eof(self) -> bool:
        return self.i >= len(self.source)

    def _peek(self, n: int = 0) -> str:
        j = self.i + n
        return "" if j >= len(self.source) else self.source[j]

    def _advance(self) -> str:
        ch = self.source[self.i]
        self.i += 1
        if ch == "\n":
            self.line += 1
            self.col = 1
        else:
            self.col += 1
        return ch

    def _advance_ws(self) -> None:
        while not self._eof() and self._peek() in " \t\r\n":
            self._advance()

    def _line_comment(self) -> None:
        while not self._eof() and self._peek() != "\n":
            self._advance()

    def _block_comment(self) -> None:
        start = self._loc()
        self._advance()
        self._advance()
        while not self._eof():
            if self._peek() == "*" and self._peek(1) == "/":
                self._advance()
                self._advance()
                return
            self._advance()
        self.diagnostics.append(Diagnostic("error", "L002", "unterminated block comment", start, "lexer"))

    def _string(self) -> Token:
        loc = self._loc()
        self._advance()
        out = []
        while not self._eof() and self._peek() != '"':
            if self._peek() == "\\":
                self._advance()
                if self._eof():
                    break
                escapes = {"n": "\n", "t": "\t", '"': '"', "\\": "\\"}
                out.append(escapes.get(self._peek(), self._peek()))
                self._advance()
            else:
                out.append(self._advance())
        if self._eof():
            self.diagnostics.append(Diagnostic("error", "L003", "unterminated string literal", loc, "lexer"))
        else:
            self._advance()
        return Token("STRING", "".join(out), loc)

    def _int(self) -> Token:
        loc = self._loc()
        out = []
        while not self._eof() and self._peek().isdigit():
            out.append(self._advance())
        return Token("INT", "".join(out), loc)

    def _ident(self) -> Token:
        loc = self._loc()
        out = []
        while not self._eof() and (self._peek().isalnum() or self._peek() in "_-"):
            out.append(self._advance())
        value = "".join(out)
        typ = value.upper() if value in KEYWORDS else "IDENT"
        if value in {"true", "false"}:
            typ = "BOOL"
        return Token(typ, value, loc)
