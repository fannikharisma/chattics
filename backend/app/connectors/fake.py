"""In-memory connector over the demo star schema, for tests and the local demo.

It implements ``Connector`` exactly: no method exists only here, so the pipeline
cannot tell it apart from the BigQuery connector that arrives in ticket 05.
"""

from datetime import date
from typing import Any

import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError

from app.connectors.base import (
    ChecklistItem,
    ConnectionField,
    ConnectionOption,
    ConnectionTestResult,
    DataSourceStructure,
    ResultSet,
    TableDefinition,
    TableSummary,
)
from app.errors import AppError

_CHECKS: tuple[tuple[str, str], ...] = (
    ("signed_in", "Signed in with Google"),
    ("project_found", "Project found"),
    ("dataset_found", "Dataset found"),
    ("read_only", "Read-only access confirmed"),
)

_FAILURE_DETAILS = {
    "signed_in": (
        "Sign in with Google (gcloud auth application-default login) and try again."
    ),
    "project_found": (
        "The project was not found. Check the project ID and that your account can open it."
    ),
    "dataset_found": (
        "The dataset was not found. Check the dataset name and that it exists in the project."
    ),
    "read_only": (
        "Read-only access could not be confirmed. Check that your account can read this dataset."
    ),
}

_TABLES: dict[str, tuple[list[str], list[list[Any]]]] = {
    "dim_vendor": (
        ["vendor_id", "vendor_name", "country"],
        [
            [1, "Northwind Traders", "US"],
            [2, "Globex GmbH", "DE"],
            [3, "Acme Components", "SG"],
        ],
    ),
    "fact_monthly_forecast": (
        ["vendor_id", "month", "forecast_units"],
        [
            [1, date(2026, 7, 1), 1000],
            [1, date(2026, 8, 1), 1200],
            [1, date(2026, 9, 1), 1100],
            [2, date(2026, 7, 1), 800],
            [2, date(2026, 8, 1), 900],
            [2, date(2026, 9, 1), 850],
            [3, date(2026, 7, 1), 1500],
            [3, date(2026, 8, 1), 1400],
            [3, date(2026, 9, 1), 1600],
        ],
    ),
    "fact_monthly_po": (
        ["vendor_id", "month", "po_units", "promised_date", "delivered_date"],
        [
            [1, date(2026, 7, 1), 950, date(2026, 7, 10), date(2026, 7, 10)],
            [1, date(2026, 8, 1), 1150, date(2026, 8, 10), date(2026, 8, 12)],
            [1, date(2026, 9, 1), 1050, date(2026, 9, 10), date(2026, 9, 10)],
            [2, date(2026, 7, 1), 780, date(2026, 7, 15), date(2026, 7, 14)],
            [2, date(2026, 8, 1), 880, date(2026, 8, 15), date(2026, 8, 15)],
            [2, date(2026, 9, 1), 900, date(2026, 9, 15), date(2026, 9, 18)],
            [3, date(2026, 7, 1), 1480, date(2026, 7, 20), date(2026, 7, 20)],
            [3, date(2026, 8, 1), 1390, date(2026, 8, 20), date(2026, 8, 21)],
            [3, date(2026, 9, 1), 1580, date(2026, 9, 20), date(2026, 9, 20)],
        ],
    ),
}


class FakeConnector:
    """BigQuery-shaped fixture: same contract, no network, deterministic rows.

    ``fail_at`` stops a test connection at one checklist key, so tests can prove
    partial failures without touching a real warehouse.
    """

    def __init__(self, fail_at: str | None = None) -> None:
        self._fail_at = fail_at
    
    def declare_connection_fields(self) -> list[ConnectionField]:
        return [
            ConnectionField(
                key="engine",
                label="Engine",
                kind="select",
                options=[
                    ConnectionOption(
                        value="Google BigQuery", label="Google BigQuery"
                    ),
                    ConnectionOption(
                        value="PostgreSQL",
                        label="PostgreSQL (later)",
                        disabled=True,
                    ),
                    ConnectionOption(
                        value="Snowflake",
                        label="Snowflake (later)",
                        disabled=True,
                    ),
                ],
            ),
            ConnectionField(
                key="method",
                label="Connection method",
                kind="select",
                help_text=(
                    "No password or key is stored. The backend uses the Google "
                    "account signed in on the machine it runs on."
                ),
                options=[
                    ConnectionOption(
                        value="Local Google sign-in",
                        label="Local Google sign-in (test and demo only)",
                    ),
                    ConnectionOption(
                        value="Service-account impersonation",
                        label="Service-account impersonation (coming soon)",
                        disabled=True,
                    ),
                ],
            ),
            ConnectionField(
                key="project_id",
                label="Project ID",
                kind="text",
                placeholder="my-company-analytics",
                help_text="The Google Cloud project that holds the dataset.",
            ),
            ConnectionField(
                key="dataset",
                label="Dataset",
                kind="text",
                placeholder="procurement_dw",
                help_text=(
                    "The dataset that holds your star schema. "
                    "The product gets read-only access."
                ),
            ),
        ]

    def read_structure(self) -> DataSourceStructure:
        return DataSourceStructure(
            tables=[
                TableDefinition(name=name, columns=list(columns))
                for name, (columns, _rows) in _TABLES.items()
            ]
        )

    def dialect(self) -> str:
        return "bigquery"

    def dry_run(self, query_text: str) -> None:
        self._read_order(query_text)

    def run(self, query_text: str, row_cap: int) -> ResultSet:
        statement, tables = self._read_order(query_text)
        if len(tables) != 1:
            raise AppError(
                "query_unsupported",
                "The demo Data Source answers Queries that read one table.",
                400,
            )
        columns, rows = _TABLES[tables[0].name.lower()]
        selected = self._projection(statement, columns)
        indexes = [columns.index(column) for column in selected]
        projected = [[row[index] for index in indexes] for row in rows]
        return ResultSet(columns=selected, rows=projected[:row_cap])

    def test_connection(self) -> ConnectionTestResult:
        checklist: list[ChecklistItem] = []
        for key, label in _CHECKS:
            if key == self._fail_at:
                detail = _FAILURE_DETAILS[key]
                checklist.append(
                    ChecklistItem(key=key, label=label, passed=False, detail=detail)
                )
                return ConnectionTestResult(
                    checklist=checklist, tables=[], error=detail
                )
            checklist.append(ChecklistItem(key=key, label=label, passed=True))
        return ConnectionTestResult(
            checklist=checklist,
            tables=[
                TableSummary(name=name, column_count=len(columns))
                for name, (columns, _rows) in _TABLES.items()
            ],
        )

    def _read_order(self, query_text: str) -> tuple[exp.Expression, list[exp.Table]]:
        try:
            statement = sqlglot.parse_one(query_text, read="bigquery")
        except ParseError as exc:
            raise AppError(
                "query_invalid",
                "The Query could not be understood. Try asking again.",
                400,
            ) from exc
        if not isinstance(statement, exp.Query):
            raise AppError(
                "query_not_read_only",
                "Only Questions that read data are allowed.",
                400,
            )
        cte_names = {cte.alias_or_name.lower() for cte in statement.find_all(exp.CTE)}
        tables = [
            table
            for table in statement.find_all(exp.Table)
            if table.name.lower() not in cte_names
        ]
        for table in tables:
            if table.name.lower() not in _TABLES:
                raise AppError(
                    "table_not_allowed",
                    f"{table.name} is not part of this Data Source.",
                    400,
                )
        return statement, tables

    def _projection(
        self, statement: exp.Expression, columns: list[str]
    ) -> list[str]:
        if not isinstance(statement, exp.Select):
            return list(columns)
        if any(
            isinstance(item, exp.Star)
            or (isinstance(item, exp.Column) and item.is_star)
            for item in statement.expressions
        ):
            return list(columns)
        selected: list[str] = []
        for item in statement.expressions:
            if not isinstance(item, exp.Column) or item.name.lower() not in columns:
                raise AppError(
                    "query_unsupported",
                    "The demo Data Source can only return plain columns for now.",
                    400,
                )
            selected.append(item.name.lower())
        return selected