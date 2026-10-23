"""The connector contract every database engine implements (ADR 0003).

A connector is a stateless adapter around one warehouse. It knows that engine's
structure and dialect, and it never touches the app database or a Tenant:
Tenant scoping belongs to ``repo.py``, which loads the Tenant's Data Source
before a connector is built.
"""

from dataclasses import dataclass
from typing import Any, Literal, Protocol


@dataclass(frozen=True)
class ConnectionField:
    """One input the Data Source form must draw."""

    key: str
    label: str
    kind: Literal["text", "select"]
    required: bool = True
    options: list[str] | None = None


@dataclass(frozen=True)
class TableDefinition:
    name: str
    columns: list[str]


@dataclass(frozen=True)
class DataSourceStructure:
    """Tables and columns, in an engine-agnostic shape."""

    tables: list[TableDefinition]


@dataclass(frozen=True)
class ResultSet:
    columns: list[str]
    rows: list[list[Any]]


class Connector(Protocol):
    def declare_connection_fields(self) -> list[ConnectionField]: ...

    def read_structure(self) -> DataSourceStructure: ...

    def dialect(self) -> str: ...

    def dry_run(self, query_text: str) -> None: ...

    def run(self, query_text: str) -> ResultSet: ...