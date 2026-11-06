from app.ai import AIAnswer, FakeAI
from app.connectors.base import ResultSet
from app.connectors.fake import FakeConnector


def test_fake_connector_declares_bigquery_like_fields(
    fake_connector: FakeConnector,
) -> None:
    fields = fake_connector.declare_connection_fields()
    by_key = {field.key: field for field in fields}

    assert {"engine", "method", "project_id", "dataset"} <= set(by_key)
    for field in by_key.values():
        assert field.label.strip()
        assert field.required is True

    assert by_key["engine"].kind == "select"
    assert by_key["engine"].options == ["Google BigQuery"]
    assert by_key["method"].kind == "select"
    assert by_key["method"].options == ["Local Google sign-in"]
    assert by_key["project_id"].kind == "text"
    assert by_key["dataset"].kind == "text"

    assert fake_connector.dialect() == "bigquery"


def test_fake_connector_returns_fixture_rows(fake_connector: FakeConnector) -> None:
    result = fake_connector.run("select * from dim_vendor", row_cap=10_000)

    assert isinstance(result, ResultSet)
    assert result.columns == ["vendor_id", "vendor_name", "country"]
    assert len(result.rows) >= 3

    purchase_orders = fake_connector.run("select * from fact_monthly_po", row_cap=10_000)

    capped = fake_connector.run("select * from fact_monthly_po", row_cap=2)
    assert len(capped.rows) == 2

    promised = purchase_orders.columns.index("promised_date")
    delivered = purchase_orders.columns.index("delivered_date")
    assert any(row[delivered] > row[promised] for row in purchase_orders.rows)


def test_fake_ai_returns_canned_answer(fake_ai: FakeAI) -> None:
    answer = fake_ai.answer("which vendors delivered late?", {})

    assert isinstance(answer, AIAnswer)
    assert answer.query_text.strip()
    assert answer.assumption is not None and answer.assumption.strip()

def test_fake_connector_test_connection_passes_four_checks_and_lists_tables(
    fake_connector: FakeConnector,
) -> None:
    result = fake_connector.test_connection()

    assert [item.key for item in result.checklist] == [
        "signed_in",
        "project_found",
        "dataset_found",
        "read_only",
    ]
    assert all(item.passed for item in result.checklist)
    assert all(item.detail is None for item in result.checklist)
    assert result.error is None

    assert {table.name: table.column_count for table in result.tables} == {
        "dim_vendor": 3,
        "fact_monthly_forecast": 3,
        "fact_monthly_po": 5,
    }


def test_fake_connector_stops_at_the_first_failed_check() -> None:
    result = FakeConnector(fail_at="dataset_found").test_connection()

    assert [item.key for item in result.checklist] == [
        "signed_in",
        "project_found",
        "dataset_found",
    ]
    assert [item.passed for item in result.checklist] == [True, True, False]
    assert result.checklist[-1].detail is not None
    assert result.error == result.checklist[-1].detail
    assert "dataset" in result.error.lower()
    assert result.tables == []