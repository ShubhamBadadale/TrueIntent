from __future__ import annotations

from mcdc.ast_nodes import Attribute, BoolValue, CloudAppNode, IntValue, ListValue, ObjectValue, ResourceNode, StringValue, VarDecl, VarRef, AstValue
from mcdc.diagnostics import Diagnostic, SourceLoc, has_errors
from .lexer import Lexer, Token


RESOURCE_KEYWORDS = {"NETWORK", "SUBNET", "COMPUTE", "STORAGE", "FIREWALL"}


def parse_source(source: str, filename: str | None = None) -> tuple[CloudAppNode | None, list[Diagnostic]]:
    tokens, diags = Lexer(source, filename).lex()
    if has_errors(diags):
        return None, diags
    node, parse_diags = Parser(tokens).parse()
    return node, diags + parse_diags


class Parser:
    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.i = 0
        self.diagnostics: list[Diagnostic] = []

    def parse(self) -> tuple[CloudAppNode | None, list[Diagnostic]]:
        app = self._cloud_app()
        self._expect("EOF")
        if has_errors(self.diagnostics):
            return None, self.diagnostics
        return app, self.diagnostics

    def _cloud_app(self) -> CloudAppNode | None:
        loc = self._expect("CLOUD").loc
        self._expect("APP")
        name = self._expect("STRING").value
        self._expect("{")
        resources: list[ResourceNode] = []
        variables: list[VarDecl] = []
        while not self._check("}") and not self._check("EOF"):
            if self._check("VAR"):
                variables.append(self._var_decl())
            elif self._peek().type in RESOURCE_KEYWORDS or self._peek().type == "IDENT":
                resources.append(self._resource_decl())
            else:
                self._error("P001", f"expected resource or variable declaration, found {self._peek().value!r}")
                self._advance()
        self._expect("}")
        return CloudAppNode(name, resources, variables, loc)

    def _var_decl(self) -> VarDecl:
        loc = self._expect("VAR").loc
        name = self._expect("IDENT").value
        self._expect("=")
        value = self._literal()
        self._expect(";")
        return VarDecl(name, value, loc)

    def _resource_decl(self) -> ResourceNode:
        kind_tok = self._advance()
        kind = kind_tok.value
        name = self._expect("STRING").value
        self._expect("{")
        attrs: list[Attribute] = []
        while not self._check("}") and not self._check("EOF"):
            attrs.append(self._attribute())
        self._expect("}")
        depends = self._depends(attrs)
        return ResourceNode(kind, name, attrs, depends, kind_tok.loc)

    def _attribute(self) -> Attribute:
        name_tok = self._expect("IDENT")
        self._expect("=")
        value = self._value()
        if self._check(";"):
            self._advance()
        return Attribute(name_tok.value, value, name_tok.loc)

    def _value(self) -> AstValue:
        if self._check("STRING") or self._check("INT") or self._check("BOOL"):
            return self._literal()
        if self._check("["):
            return self._list()
        if self._check("{"):
            return self._object()
        if self._check("REF_START"):
            loc = self._advance().loc
            name = self._expect("IDENT").value
            self._expect("}")
            return VarRef(name, loc)
        tok = self._peek()
        self._error("P002", f"expected value, found {tok.value!r}")
        self._advance()
        return StringValue("", tok.loc)

    def _literal(self) -> AstValue:
        tok = self._advance()
        if tok.type == "STRING":
            return StringValue(tok.value, tok.loc)
        if tok.type == "INT":
            return IntValue(int(tok.value), tok.loc)
        if tok.type == "BOOL":
            return BoolValue(tok.value == "true", tok.loc)
        self._error("P003", f"expected literal, found {tok.value!r}", tok.loc)
        return StringValue("", tok.loc)

    def _list(self) -> ListValue:
        loc = self._expect("[").loc
        values: list[AstValue] = []
        if not self._check("]"):
            values.append(self._value())
            while self._check(","):
                self._advance()
                values.append(self._value())
        self._expect("]")
        return ListValue(values, loc)

    def _object(self) -> ObjectValue:
        loc = self._expect("{").loc
        values: dict[str, AstValue] = {}
        if not self._check("}"):
            key = self._expect("IDENT").value
            self._expect("=")
            values[key] = self._value()
            while self._check(","):
                self._advance()
                key = self._expect("IDENT").value
                self._expect("=")
                values[key] = self._value()
        self._expect("}")
        return ObjectValue(values, loc)

    def _depends(self, attrs: list[Attribute]) -> list[str]:
        result: list[str] = []
        for attr in attrs:
            if attr.name != "depends_on":
                continue
            if isinstance(attr.value, ListValue):
                for item in attr.value.values:
                    if isinstance(item, StringValue):
                        result.append(item.value)
        return result

    def _expect(self, typ: str) -> Token:
        if self._check(typ):
            return self._advance()
        tok = self._peek()
        self._error("P004", f"expected {typ}, found {tok.value!r}", tok.loc)
        return Token(typ, "", tok.loc)

    def _check(self, typ: str) -> bool:
        return self._peek().type == typ

    def _peek(self) -> Token:
        return self.tokens[self.i]

    def _advance(self) -> Token:
        tok = self.tokens[self.i]
        if self.i < len(self.tokens) - 1:
            self.i += 1
        return tok

    def _error(self, code: str, message: str, loc: SourceLoc | None = None) -> None:
        self.diagnostics.append(Diagnostic("error", code, message, loc or self._peek().loc, "parser"))
