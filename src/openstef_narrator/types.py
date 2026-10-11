"""Core domain types — ForecastContext, NarrativeReport, NarrativeMeta, Driver."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class Driver:
    """A factor driving the forecast — displayed as a chip in the UI."""

    icon: str
    label: str
    detail: str
    prose: str  # natural language fragment for template insertion


@dataclass(frozen=True, slots=True)
class ForecastPoint:
    """One hour of probabilistic forecast data."""

    hour: int          # offset from forecast start (0-47)
    hour_of_day: int   # 0-23
    p10: float         # 10th percentile load (MW)
    p50: float         # median load (MW)
    p90: float         # 90th percentile load (MW)
    temperature: float  # outdoor temp (°F)


@dataclass(frozen=True, slots=True)
class ForecastContext:
    """Typed input contract for the narrator.

    Bundles everything the narrator needs: forecast points, feeder metadata,
    derived statistics, and scenario classification. Constructed from
    generate_forecast() or from_openstef().
    """

    feeder_id: str
    feeder_name: str
    district: str
    capacity_mw: float
    points: tuple[ForecastPoint, ...]
    peak_mw: float
    peak_hour: int       # hour offset (0-47)
    peak_hour_of_day: int
    peak_pct: float      # peak / capacity
    exceedance_prob: float
    confidence: str      # "High", "Moderate", "Low"
    band_width: float    # relative uncertainty
    scenario: str        # auto-detected or overridden
    drivers: tuple[Driver, ...]
    low_temp: float
    forecast_run_id: str
    secondary_flags: tuple[str, ...] = ()

    @classmethod
    def from_openstef(cls, forecast_df: "pd.DataFrame", feeder_meta: dict) -> ForecastContext:
        """Adapter: convert an OpenSTEF DataFrame + metadata to ForecastContext.

        Pure pandas function — no openstef dependency.
        Expected DataFrame columns: p10, p50, p90, temperature (hourly).
        feeder_meta keys: id, name, district, capacity_mw, band_width, run_id.
        """
        import pandas as pd

        points = tuple(
            ForecastPoint(
                hour=i,
                hour_of_day=int(row.get("hour_of_day", i % 24)),
                p10=float(row["p10"]),
                p50=float(row["p50"]),
                p90=float(row["p90"]),
                temperature=float(row.get("temperature", 50.0)),
            )
            for i, row in forecast_df.iterrows()
        )

        peak_pt = max(points, key=lambda p: p.p50)
        cap = feeder_meta["capacity_mw"]
        peak_pct = peak_pt.p50 / cap
        sigma = (peak_pt.p90 - peak_pt.p50) / 1.28 if peak_pt.p90 > peak_pt.p50 else 0.01

        from openstef_narrator.scenarios import detect_scenario

        return cls(
            feeder_id=feeder_meta["id"],
            feeder_name=feeder_meta["name"],
            district=feeder_meta["district"],
            capacity_mw=cap,
            points=points,
            peak_mw=peak_pt.p50,
            peak_hour=peak_pt.hour,
            peak_hour_of_day=peak_pt.hour_of_day,
            peak_pct=peak_pct,
            exceedance_prob=0.0,  # caller computes
            confidence="Moderate",
            band_width=feeder_meta.get("band_width", 0.1),
            scenario=detect_scenario(peak_pct, feeder_meta.get("band_width", 0.1)),
            drivers=(),
            low_temp=min(p.temperature for p in points),
            forecast_run_id=feeder_meta.get("run_id", "unknown"),
        )


@dataclass(frozen=True, slots=True)
class NarrativeReport:
    """Prose output of the narrator, with «fact» markers."""

    situation: str       # main forecast statement
    risk: str            # confidence + exceedance assessment
    recommendation: str  # operator action
    audit: str           # traceability (full verbosity only, else empty)
    analogue: str = ""   # historical analogue prose (standard/full only)


@dataclass(frozen=True, slots=True)
class NarrativeMeta:
    """Traceability metadata for a narrative report."""

    narrative_id: str
    forecast_run_id: str
    scenario: str
    verbosity: str
    backend: str           # "anthropic", "ollama", "template_fallback"
    generated_at: str
    delivery_targets: tuple[str, ...] = ()
    # 1.3/1.4: audit trail enrichment
    model_version: str = ""            # exact LLM model string, empty if template-only
    backend_requested: str = ""        # what was requested ("anthropic", "template", "auto")
    backend_resolved: str = ""         # what actually produced the output
    validation_passed: bool = True     # did marker validation pass on all sections?
    fallback_sections: tuple[str, ...] = ()  # which sections fell back ("situation", "risk", ...)
    latency_ms: int = 0               # wall-clock time for the full explain() call
    temperature: float = 0.0          # LLM temperature used (0.0 = deterministic)
