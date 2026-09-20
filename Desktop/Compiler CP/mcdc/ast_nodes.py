from __future__ import annotations

from dataclasses import dataclass
from typing import Union

from .diagnostics import SourceLoc


@dataclass(frozen=True)
class StringValue:
    value: str
    loc: SourceLoc


@dataclass(frozen=True)
class IntValue:
    value: int
    loc: SourceLoc


@dataclass(frozen=True)
class BoolValue:
    value: bool
    loc: SourceLoc


@dataclass(frozen=True)
class ListValue:
    values: list["AstValue"]
    loc: SourceLoc


@dataclass(frozen=True)
class ObjectValue:
    values: dict[str, "AstValue"]
    loc: SourceLoc


@dataclass(frozen=True)
class VarRef:
    name: str
    loc: SourceLoc


AstValue = Union[StringValue, IntValue, BoolValue, ListValue, ObjectValue, VarRef]


@dataclass
class Attribute:
    name: str
    value: AstValue
    loc: SourceLoc


@dataclass
class ResourceNode:
    kind: str
    name: str
    attributes: list[Attribute]
    depends_on: list[str]
    loc: SourceLoc


@dataclass
class VarDecl:
    name: str
    value: AstValue
    loc: SourceLoc


@dataclass
class CloudAppNode:
    name: str
    resources: list[ResourceNode]
    variables: list[VarDecl]
    loc: SourceLoc
