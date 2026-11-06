"""The Tenant's Data Source card: test first, then save.

The server owns the test-before-save rule. A passing test stores a fingerprint
of the canonical fields; saving recomputes it and refuses on any mismatch, so
the client cannot fake a test by sending a fingerprint of its own.
"""

import hashlib
import json
from dataclasses import asdict
from datetime import datetime
from typing import Any, Literal, cast

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import get_tenant_context, require_tenant_admin
from app.connectors import (
    SUPPORTED_ENGINE,
    SUPPORTED_METHOD,
    ConnectorFactory,
    get_connector_factory,
)
from app.connectors.base import Connector, DataSourceStructure
from app.db import get_session
from app.errors import AppError
from app.repo import (
    DataSourceRecord,
    TenantRecord,
    UserRecord,
    connect_data_source,
    get_data_source,
    record_data_source_test,
)
from pydantic import BaseModel, Field

from app.connectors import (
    SUPPORTED_ENGINE,
    SUPPORTED_METHOD,
    ConnectorFactory,
    declared_connection_fields,
    get_connector_factory,
)

router = APIRouter(prefix="/api/data-source", tags=["data-source"])

DataSourceStatus = Literal["not_connected", "connected"]

_CONNECTION_COLUMNS = ("engine", "method")
_TEST_REQUIRED = "Test the connection again before saving."


class TableSummaryResponse(BaseModel):
    name: str
    column_count: int


class ChecklistItemResponse(BaseModel):
    key: str
    label: str
    passed: bool
    detail: str | None = None


class ConnectionTestResponse(BaseModel):
    checklist: list[ChecklistItemResponse]
    tables: list[TableSummaryResponse]
    error: str | None
    status: Literal["not_connected"] = "not_connected"


class DataSourceResponse(BaseModel):
    engine: str
    method: str
    fields: dict[str, str]
    status: DataSourceStatus
    tested_at: datetime | None
    tables: list[TableSummaryResponse]


def _require_supported_connection(fields: dict[str, str]) -> None:
    if fields.get("engine", "").strip() != SUPPORTED_ENGINE:
        raise AppError("unknown_engine", "This engine is not available yet.", 400)
    if fields.get("method", "").strip() != SUPPORTED_METHOD:
        raise AppError(
            "unsupported_method",
            "This connection method is not available yet. Use local Google sign-in.",
            400,
        )


def _canonical_fields(
    fields: dict[str, str], connector: Connector
) -> dict[str, str]:
    """Keep exactly the declared fields; drop anything else, including fakes."""
    return {
        field.key: fields.get(field.key, "").strip()
        for field in connector.declare_connection_fields()
    }


def _fingerprint(fields: dict[str, str]) -> str:
    canonical = json.dumps(
        fields, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _stored_fields(fields: dict[str, str]) -> dict[str, str]:
    return {
        key: value
        for key, value in fields.items()
        if key not in _CONNECTION_COLUMNS
    }


def _structure_json(structure: DataSourceStructure) -> dict[str, Any]:
    return {"tables": [asdict(table) for table in structure.tables]}


def _table_summaries(structure: dict[str, Any]) -> list[TableSummaryResponse]:
    tables = structure.get("tables", []) if structure else []
    return [
        TableSummaryResponse(
            name=str(table["name"]),
            column_count=len(table.get("columns", [])),
        )
        for table in tables
    ]


def _data_source_response(record: DataSourceRecord) -> DataSourceResponse:
    return DataSourceResponse(
        engine=record.engine,
        method=record.method,
        fields=record.fields,
        status=cast(DataSourceStatus, record.status),
        tested_at=record.tested_at,
        tables=_table_summaries(record.last_structure),
    )

class ConnectionOptionResponse(BaseModel):
    value: str
    label: str
    disabled: bool = False


class ConnectionFieldResponse(BaseModel):
    key: str
    label: str
    kind: Literal["text", "select"]
    required: bool
    help_text: str | None = None
    placeholder: str | None = None
    options: list[ConnectionOptionResponse] = Field(default_factory=list)


class ConnectionFieldsResponse(BaseModel):
    fields: list[ConnectionFieldResponse]

@router.get("/fields", response_model=ConnectionFieldsResponse)
def read_connection_fields(
    _identity: UserRecord = Depends(require_tenant_admin),
) -> ConnectionFieldsResponse:
    """The form is drawn from the connector, never from a frontend list."""
    return ConnectionFieldsResponse(
        fields=[
            ConnectionFieldResponse(
                key=field.key,
                label=field.label,
                kind=field.kind,
                required=field.required,
                help_text=field.help_text,
                placeholder=field.placeholder,
                options=[
                    ConnectionOptionResponse(
                        value=option.value,
                        label=option.label,
                        disabled=option.disabled,
                    )
                    for option in field.options or []
                ],
            )
            for field in declared_connection_fields()
        ]
    )

@router.get("", response_model=DataSourceResponse | None)
def read_data_source(
    _identity: UserRecord = Depends(require_tenant_admin),
    tenant: TenantRecord = Depends(get_tenant_context),
    session: Session = Depends(get_session),
) -> DataSourceResponse | None:
    record = get_data_source(session, tenant.id)
    return _data_source_response(record) if record is not None else None


@router.post("/test", response_model=ConnectionTestResponse)
def test_data_source(
    fields: dict[str, str],
    _identity: UserRecord = Depends(require_tenant_admin),
    tenant: TenantRecord = Depends(get_tenant_context),
    session: Session = Depends(get_session),
    connector_factory: ConnectorFactory = Depends(get_connector_factory),
) -> ConnectionTestResponse:
    _require_supported_connection(fields)
    connector = connector_factory(fields)
    normalised = _canonical_fields(fields, connector)
    result = connector.test_connection()

    response = ConnectionTestResponse(
        checklist=[
            ChecklistItemResponse(**asdict(item)) for item in result.checklist
        ],
        tables=[
            TableSummaryResponse(
                name=table.name, column_count=table.column_count
            )
            for table in result.tables
        ],
        error=result.error,
    )
    if result.error is not None:
        return response

    structure = connector.read_structure()
    try:
        record_data_source_test(
            session,
            tenant.id,
            engine=normalised["engine"],
            method=normalised["method"],
            fields=_stored_fields(normalised),
            fingerprint=_fingerprint(normalised),
            structure=_structure_json(structure),
        )
        session.commit()
    except Exception:
        session.rollback()
        raise
    return response


@router.put("", response_model=DataSourceResponse)
def save_data_source(
    fields: dict[str, str],
    _identity: UserRecord = Depends(require_tenant_admin),
    tenant: TenantRecord = Depends(get_tenant_context),
    session: Session = Depends(get_session),
    connector_factory: ConnectorFactory = Depends(get_connector_factory),
) -> DataSourceResponse:
    _require_supported_connection(fields)
    connector = connector_factory(fields)
    normalised = _canonical_fields(fields, connector)

    try:
        saved = connect_data_source(
            session,
            tenant.id,
            fields=_stored_fields(normalised),
            fingerprint=_fingerprint(normalised),
        )
        if not saved:
            raise AppError("test_required", _TEST_REQUIRED, 409)
        session.commit()
    except Exception:
        session.rollback()
        raise

    record = get_data_source(session, tenant.id)
    if record is None:
        raise AppError(
            "data_source_missing",
            "The Data Source could not be saved. Please try again.",
            500,
        )
    return _data_source_response(record)