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
    result = fake_connector.run("select * from dim_vendor")

    assert isinstance(result, ResultSet)
    assert result.columns == ["vendor_id", "vendor_name", "country"]
    assert len(result.rows) >= 3

    purchase_orders = fake_connector.run("select * from fact_monthly_po")
    promised = purchase_orders.columns.index("promised_date")
    delivered = purchase_orders.columns.index("delivered_date")
    assert any(row[delivered] > row[promised] for row in purchase_orders.rows)


def test_fake_ai_returns_canned_answer(fake_ai: FakeAI) -> None:
    answer = fake_ai.answer("which vendors delivered late?", {})

    assert isinstance(answer, AIAnswer)
    assert answer.query_text.strip()
    assert answer.assumption is not None and answer.assumption.strip()