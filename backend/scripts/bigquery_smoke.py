"""Print a live BigQuery dataset's tables and column counts.

Run manually from backend/, after ``gcloud auth application-default login``:

    uv run python -m scripts.bigquery_smoke <project-id> <dataset>

Uses the machine's own Google identity (ADR 0006). Stores no secret and is
never imported by the app or the test suite.
"""

import sys

from app.connectors.bigquery import BigQueryConnector
from app.errors import AppError


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        raise SystemExit(
            "Usage: python -m scripts.bigquery_smoke <project-id> <dataset>"
        )

    try:
        connector = BigQueryConnector(project_id=argv[1], dataset=argv[2])
    except AppError as exc:
        print(exc.message)
        return 1

    result = connector.test_connection()
    for item in result.checklist:
        mark = "PASS" if item.passed else "FAIL"
        print(f"[{mark}] {item.label}")
        if item.detail:
            print(f"       {item.detail}")

    if result.error:
        return 1

    for table in result.tables:
        print(f"{table.name}: {table.column_count} columns")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))