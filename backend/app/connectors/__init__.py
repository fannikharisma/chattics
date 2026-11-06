"""Turn submitted Data Source fields into the right connector."""

from collections.abc import Callable

from app.connectors.base import Connector
from app.connectors.bigquery import (
    BigQueryConnector,
    declared_connection_fields,
)
from app.errors import AppError



ConnectorFactory = Callable[[dict[str, str]], Connector]

SUPPORTED_ENGINE = "Google BigQuery"
SUPPORTED_METHOD = "Local Google sign-in"


def build_connector(fields: dict[str, str]) -> Connector:
    """Build the adapter for a set of declared fields. No network call yet."""
    engine = fields.get("engine", "").strip()
    if engine != SUPPORTED_ENGINE:
        raise AppError("unknown_engine", "This engine is not available yet.", 400)

    method = fields.get("method", "").strip()
    if method != SUPPORTED_METHOD:
        raise AppError(
            "unsupported_method",
            "This connection method is not available yet. Use local Google sign-in.",
            400,
        )

    return BigQueryConnector(
        project_id=fields.get("project_id", "").strip(),
        dataset=fields.get("dataset", "").strip(),
    )


def get_connector_factory() -> ConnectorFactory:
    """FastAPI dependency. Tests override this with the fake connector."""
    return build_connector