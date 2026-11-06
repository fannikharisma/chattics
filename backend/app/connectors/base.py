"""The connector contract every database engine implements (ADR 0003).

A connector is a stateless adapter around one warehouse. It knows that engine's
structure and dialect, and it never touches the app database or a Tenant:
Tenant scoping belongs to ``repo.py``, which loads the Tenant's Data Source
before a connector is built.

A connector also owns the conversation with the person connecting it: it declares
the form fields, and reports a small checklist so a failed test names the step
that failed in plain English.
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
    help_text: str | None = None
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
class TableSummary:
    """One table found by a connection test: name and column count only."""

    name: str
    column_count: int


@dataclass(frozen=True)
class ChecklistItem:
    """One row in the Test connection checklist."""

    key: str
    label: str
    passed: bool
    detail: str | None = None


@dataclass(frozen=True)
class ConnectionTestResult:
    """Outcome of Test connection. Partial when a check fails.

    ``checklist`` stops at the first failure, ``tables`` is empty unless every
    check passed, and ``error`` is the plain message for that first failure.
    """

    checklist: list[ChecklistItem]
    tables: list[TableSummary]
    error: str | None = None


@dataclass(frozen=True)
class ResultSet:
    columns: list[str]
    rows: list[list[Any]]


class Connector(Protocol):
    def declare_connection_fields(self) -> list[ConnectionField]: ...

    def read_structure(self) -> DataSourceStructure: ...

    def dialect(self) -> str: ...

    def dry_run(self, query_text: str) -> None: ...

    def run(self, query_text: str, row_cap: int) -> ResultSet: ...

    def test_connection(self) -> ConnectionTestResult: ...

@dataclass(frozen=True)
class ConnectionOption:
    """One choice in a select. Disabled choices are visible but not pickable."""

    value: str
    label: str
    disabled: bool = False


@dataclass(frozen=True)
class ConnectionField:
    """One input the Data Source form must draw."""

    key: str
    label: str
    kind: Literal["text", "select"]
    required: bool = True
    help_text: str | None = None
    placeholder: str | None = None
    options: list[ConnectionOption] | None = None