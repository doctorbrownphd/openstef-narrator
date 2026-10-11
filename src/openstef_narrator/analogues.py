"""Historical analogue retrieval — find past events with similar patterns.

Grounds narrative explanations in real operational history. When generating
a report, the engine can find the closest historical match and append prose
like: "This pattern resembles the January 2024 cold snap, when peak ran
12% over forecast and two feeders required load transfer."

The event store is seeded with realistic New England events. A production
system would replace this with a database-backed store.
"""

from __future__ import annotations

from dataclasses import dataclass

from openstef_narrator.types import ForecastContext


@dataclass(frozen=True)
class HistoricalEvent:
    """One past operational event in the event store."""

    event_id: str
    date: str               # "2024-01-16"
    label: str              # "January 2024 cold snap"
    scenario: str           # "peak_forecast", "overload_risk", etc.
    peak_pct: float         # how high peak was (fraction of rating)
    low_temp: float         # degrees F
    feeders_affected: int   # how many feeders were at risk
    outcome: str            # "load transfer on Feeder 12", "DR activated", etc.
    lesson: str             # "Peak ran 12% over forecast"


# ------------------------------------------------------------------
# Seeded event store — realistic NE operational history
# ------------------------------------------------------------------

HISTORICAL_EVENTS: tuple[HistoricalEvent, ...] = (
    HistoricalEvent(
        event_id="evt-2024-jan-cold",
        date="2024-01-16",
        label="January 2024 cold snap",
        scenario="overload_risk",
        peak_pct=1.12,
        low_temp=5.0,
        feeders_affected=2,
        outcome="load transfer on Feeder 12 and Feeder 7",
        lesson="Peak ran 12% over forecast",
    ),
    HistoricalEvent(
        event_id="evt-2023-feb-noreaster",
        date="2023-02-04",
        label="February 2023 nor'easter",
        scenario="peak_forecast",
        peak_pct=0.97,
        low_temp=-2.0,
        feeders_affected=3,
        outcome="pre-staged switching on three feeders in Mill District",
        lesson="Morning ramp exceeded day-ahead forecast by 8%",
    ),
    HistoricalEvent(
        event_id="evt-2023-jul-heat",
        date="2023-07-19",
        label="July 2023 heat dome",
        scenario="peak_forecast",
        peak_pct=0.94,
        low_temp=72.0,
        feeders_affected=4,
        outcome="voltage reduction on Eastgate and Lakeside circuits",
        lesson="Cooling load peaked two hours later than forecast",
    ),
    HistoricalEvent(
        event_id="evt-2023-dec-christmas",
        date="2023-12-24",
        label="Christmas Eve 2023 cold",
        scenario="demand_response",
        peak_pct=0.91,
        low_temp=8.0,
        feeders_affected=1,
        outcome="DR activation shaved 0.6 MW from Feeder 9 evening peak",
        lesson="Enrolled DR was sufficient to avoid switching",
    ),
    HistoricalEvent(
        event_id="evt-2024-mar-storm",
        date="2024-03-12",
        label="March 2024 late-season storm",
        scenario="low_confidence",
        peak_pct=0.88,
        low_temp=18.0,
        feeders_affected=2,
        outcome="forecast re-run at 06:00 narrowed the band by 40%",
        lesson="Initial forecast had 22% band width due to model disagreement",
    ),
    HistoricalEvent(
        event_id="evt-2023-aug-mild",
        date="2023-08-14",
        label="August 2023 mild week",
        scenario="all_clear",
        peak_pct=0.58,
        low_temp=62.0,
        feeders_affected=0,
        outcome="no action required across all feeders",
        lesson="Offshore breeze kept cooling load well below forecast",
    ),
    HistoricalEvent(
        event_id="evt-2025-jan-vortex",
        date="2025-01-08",
        label="January 2025 polar vortex",
        scenario="overload_risk",
        peak_pct=1.06,
        low_temp=-8.0,
        feeders_affected=3,
        outcome="emergency load transfer on three Northborough feeders",
        lesson="Heating load sustained above nameplate for five hours",
    ),
    HistoricalEvent(
        event_id="evt-2023-nov-early-cold",
        date="2023-11-18",
        label="November 2023 early cold snap",
        scenario="peak_forecast",
        peak_pct=0.92,
        low_temp=12.0,
        feeders_affected=1,
        outcome="proactive switching on Feeder 7 ahead of evening peak",
        lesson="Seasonal transition caught day-ahead model off guard",
    ),
    HistoricalEvent(
        event_id="evt-2024-feb-ice",
        date="2024-02-22",
        label="February 2024 ice storm",
        scenario="low_confidence",
        peak_pct=0.85,
        low_temp=28.0,
        feeders_affected=2,
        outcome="held action pending forecast re-run; band narrowed by noon",
        lesson="Icing uncertainty drove 25% prediction band",
    ),
    HistoricalEvent(
        event_id="evt-2024-jun-heatwave",
        date="2024-06-28",
        label="June 2024 early heatwave",
        scenario="demand_response",
        peak_pct=0.89,
        low_temp=68.0,
        feeders_affected=2,
        outcome="DR curtailment held Lakeside and Riverside below rating",
        lesson="AC load ramped faster than seasonal norms predicted",
    ),
)


def _score_event(event: HistoricalEvent, ctx: ForecastContext) -> float:
    """Score a historical event by similarity to the current forecast.

    Lower score = more similar. Components:
      - Scenario match (0 if same, 3.0 penalty if different)
      - Temperature proximity (absolute difference / 20, capped at 1.0)
      - Peak % proximity (absolute difference * 5, capped at 1.0)
    """
    # Scenario match carries the most weight
    scenario_penalty = 0.0 if event.scenario == ctx.scenario else 3.0

    # Temperature proximity — normalise so 20 deg F difference ~ 1.0
    temp_diff = abs(event.low_temp - ctx.low_temp) / 20.0
    temp_score = min(temp_diff, 1.0)

    # Peak % proximity — normalise so 0.20 difference ~ 1.0
    peak_diff = abs(event.peak_pct - ctx.peak_pct) * 5.0
    peak_score = min(peak_diff, 1.0)

    return scenario_penalty + temp_score + peak_score


def find_analogues(
    ctx: ForecastContext,
    top_k: int = 2,
) -> list[HistoricalEvent]:
    """Find the top_k most similar historical events for a forecast context.

    Parameters
    ----------
    ctx : ForecastContext
        Current forecast to match against.
    top_k : int
        Number of analogues to return (default 2).

    Returns
    -------
    list[HistoricalEvent]
        Best matches sorted by similarity (most similar first).
    """
    scored = sorted(HISTORICAL_EVENTS, key=lambda e: _score_event(e, ctx))
    return scored[:top_k]


def format_analogue_prose(event: HistoricalEvent) -> str:
    """Format a single historical event as a narrative sentence.

    All factual claims are wrapped in fact markers so the LLM rewrite
    layer cannot alter them.
    """
    return (
        f"This pattern resembles the \u00ab{event.label}\u00bb, "
        f"when \u00ab{event.lesson}\u00bb and "
        f"\u00ab{event.outcome}\u00bb."
    )
