"""The AI seam: one method, structured output, no free text.

``FakeAI`` is the only implementation until ticket 07 adds the LiteLLM
answerer. Tests must never call a model: they override ``get_ai`` through
FastAPI's dependency overrides and swap in a fake configured per scenario.
"""

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class AIAnswer:
    """What the AI is allowed to return: a Query, an Assumption, a note, a chart."""

    query_text: str
    assumption: str | None = None
    kpi_note: str | None = None
    chart_suggestion: dict[str, Any] | None = None


class Answerer(Protocol):
    def answer(self, question: str, briefing: dict[str, Any]) -> AIAnswer: ...


_LATE_DELIVERIES_QUERY = """
select vendor_id, month, po_units, promised_date, delivered_date
from fact_monthly_po
where delivered_date > promised_date
""".strip()


class FakeAI:
    """Canned answers selected by keyword, over the fixture's tables."""

    def answer(self, question: str, briefing: dict[str, Any]) -> AIAnswer:
        words = question.lower()

        if "late" in words:
            return AIAnswer(
                query_text=_LATE_DELIVERIES_QUERY,
                assumption=(
                    "I treated a delivery as late when it arrived after the "
                    "promised date, across every month in the Data Source."
                ),
                chart_suggestion={
                    "type": "bar",
                    "x": "vendor_id",
                    "y": "po_units",
                },
            )

        return AIAnswer(
            query_text="select * from dim_vendor",
            assumption="I assumed you want the full list of vendors.",
        )


def get_ai() -> Answerer:
    """FastAPI dependency. Override this in tests; nothing else may supply an AI."""
    return FakeAI()