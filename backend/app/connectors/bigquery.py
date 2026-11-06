"""Google BigQuery connector (ADR 0003, ADR 0006).

v1 is test and demo only: every call runs with the machine's own Google
identity through Application Default Credentials. There is no credentials
argument and no key stored anywhere, so no secret can leak through the app
database. Service-account impersonation arrives later.

Run ``gcloud auth application-default login`` before using this connector. When
it is missing, the first checklist item says exactly that.
"""

import logging
import re

from google.api_core.exceptions import GoogleAPIError
from google.auth.exceptions import GoogleAuthError
from google.cloud import bigquery

from app.connectors.base import (
    ChecklistItem,
    ConnectionField,
    ConnectionTestResult,
    DataSourceStructure,
    ResultSet,
    TableDefinition,
    TableSummary,
)
from app.errors import AppError

logger = logging.getLogger(__name__)

_PROJECT_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9.:-]*$")
_DATASET_ID = re.compile(r"^[A-Za-z0-9_]+$")

_CHECKS: tuple[tuple[str, str], ...] = (
    ("signed_in", "Signed in with Google"),
    ("project_found", "Project found"),
    ("dataset_found", "Dataset found"),
    ("read_only", "Read-only access confirmed"),
)
_LABELS = dict(_CHECKS)

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

_STRUCTURE_QUERY = """
select t.table_name, c.column_name
from `{dataset_path}.INFORMATION_SCHEMA.TABLES` as t
join `{dataset_path}.INFORMATION_SCHEMA.COLUMNS` as c using (table_name)
order by t.table_name, c.ordinal_position
""".strip()

_API_ERRORS = (GoogleAPIError, GoogleAuthError)


class BigQueryConnector:
    """One Tenant's BigQuery project and dataset, reached with local ADC."""

    def __init__(self, project_id: str, dataset: str) -> None:
        if not _PROJECT_ID.fullmatch(project_id):
            raise AppError(
                "invalid_connection",
                "The project ID is not valid. Check the ID and try again.",
                400,
            )
        if not _DATASET_ID.fullmatch(dataset):
            raise AppError(
                "invalid_connection",
                "The dataset name is not valid. Check the name and try again.",
                400,
            )
        self._project_id = project_id
        self._dataset = dataset
        self._client_instance: bigquery.Client | None = None

    @property
    def _dataset_path(self) -> str:
        return f"{self._project_id}.{self._dataset}"

    def _client(self) -> bigquery.Client:
        # No credentials argument: ADC is the only sign-in (ADR 0006).
        if self._client_instance is None:
            self._client_instance = bigquery.Client(project=self._project_id)
        return self._client_instance

    def declare_connection_fields(self) -> list[ConnectionField]:
        return [
            ConnectionField(
                key="engine",
                label="Engine",
                kind="select",
                options=["Google BigQuery"],
            ),
            ConnectionField(
                key="method",
                label="Connection method",
                kind="select",
                options=["Local Google sign-in"],
            ),
            ConnectionField(
                key="project_id",
                label="Project ID",
                kind="text",
                help_text="The Google Cloud project that holds the dataset.",
            ),
            ConnectionField(
                key="dataset",
                label="Dataset",
                kind="text",
                help_text="The BigQuery dataset with the tables to explore.",
            ),
        ]

    def read_structure(self) -> DataSourceStructure:
        try:
            return self._read_structure()
        except _API_ERRORS as exc:
            logger.warning(
                "bigquery structure read failed (%s)", type(exc).__name__
            )
            raise AppError(
                "structure_unavailable",
                "The Data Source's tables could not be read. Check the connection and try again.",
                500,
            ) from exc

    def dialect(self) -> str:
        return "bigquery"

    def dry_run(self, query_text: str) -> None:
        job_config = bigquery.QueryJobConfig(dry_run=True, use_query_cache=False)
        try:
            self._client().query(query_text, job_config=job_config)
        except _API_ERRORS as exc:
            logger.warning("bigquery dry run failed (%s)", type(exc).__name__)
            raise AppError(
                "query_invalid",
                "The Query could not be checked. Try asking again.",
                400,
            ) from exc

    def run(self, query_text: str, row_cap: int) -> ResultSet:
        try:
            job = self._client().query(query_text)
            rows = job.result(max_results=row_cap)
            columns = [field.name for field in job.schema or []]
            return ResultSet(
                columns=columns,
                rows=[list(row.values()) for row in rows],
            )
        except _API_ERRORS as exc:
            logger.warning("bigquery query failed (%s)", type(exc).__name__)
            raise AppError(
                "query_failed",
                "The Query could not run. Try asking again in a moment.",
                500,
            ) from exc

    def test_connection(self) -> ConnectionTestResult:
        checklist: list[ChecklistItem] = []

        try:
            client = self._client()
        except (GoogleAuthError, OSError):
            return self._failed(checklist, "signed_in")
        checklist.append(self._passed("signed_in"))

        try:
            client.query("select 1").result()
        except _API_ERRORS:
            return self._failed(checklist, "project_found")
        checklist.append(self._passed("project_found"))

        try:
            client.get_dataset(self._dataset_path)
        except _API_ERRORS:
            return self._failed(checklist, "dataset_found")
        checklist.append(self._passed("dataset_found"))

        try:
            structure = self._read_structure()
        except _API_ERRORS:
            return self._failed(checklist, "read_only")
        checklist.append(self._passed("read_only"))

        return ConnectionTestResult(
            checklist=checklist,
            tables=[
                TableSummary(name=table.name, column_count=len(table.columns))
                for table in structure.tables
            ],
        )

    def _read_structure(self) -> DataSourceStructure:
        query = _STRUCTURE_QUERY.format(dataset_path=self._dataset_path)
        rows = self._client().query(query).result()
        tables: dict[str, list[str]] = {}
        for table_name, column_name in rows:
            tables.setdefault(table_name, []).append(column_name)
        return DataSourceStructure(
            tables=[
                TableDefinition(name=name, columns=columns)
                for name, columns in tables.items()
            ]
        )

    @staticmethod
    def _passed(key: str) -> ChecklistItem:
        return ChecklistItem(key=key, label=_LABELS[key], passed=True)

    @staticmethod
    def _failed(
        checklist: list[ChecklistItem], key: str
    ) -> ConnectionTestResult:
        detail = _FAILURE_DETAILS[key]
        checklist.append(
            ChecklistItem(key=key, label=_LABELS[key], passed=False, detail=detail)
        )
        return ConnectionTestResult(checklist=checklist, tables=[], error=detail)