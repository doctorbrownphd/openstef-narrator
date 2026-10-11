"""Scenario definitions and auto-detection rules."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Scenario:
    """One of five operational scenario types that shapes the narrative tone."""

    id: str
    label: str
    tone: str          # "advisory", "urgent", "cautionary", "routine"
    trigger: str       # human-readable trigger condition
    description: str
    template_only: bool = False  # if True, LLM rewrite is bypassed by policy


SCENARIOS: tuple[Scenario, ...] = (
    Scenario(
        "peak_forecast", "Peak forecast", "advisory",
        "p50 peak > 85% of rating",
        "Standard high-load heads-up: when, how high, what is driving it, "
        "and whether to act.",
    ),
    Scenario(
        "overload_risk", "Transformer overload risk", "urgent",
        "p90 peak ≥ 100% of rating",
        "Upper-band crosses nameplate — escalates to a switching or DR recommendation.",
        template_only=True,  # 1.5: zero external dependency under time pressure
    ),
    Scenario(
        "demand_response", "Demand-response recommendation", "advisory",
        "85–95% peak + DR enrolled",
        "Peak is shavable with enrolled curtailment rather than switching.",
    ),
    Scenario(
        "low_confidence", "Low-confidence alert", "cautionary",
        "band width > 15% at peak",
        "Wide prediction interval — flags uncertainty and recommends re-running.",
    ),
    Scenario(
        "all_clear", "All-clear", "routine",
        "p90 peak < 75% of rating",
        "Ample headroom; confirms no action and closes the loop for the shift log.",
    ),
)

_SCENARIO_INDEX = {s.id: s for s in SCENARIOS}


def get_scenario(id: str) -> Scenario:
    """Look up a scenario by ID. Raises ValueError if not found."""
    try:
        return _SCENARIO_INDEX[id]
    except KeyError:
        valid = ", ".join(_SCENARIO_INDEX)
        raise ValueError(f"Unknown scenario '{id}'. Valid: {valid}") from None


def detect_scenario(peak_pct: float, band_width: float) -> str:
    """Auto-detect the appropriate scenario from forecast data.

    Precedence order and rationale
    ==============================
    Reality can overlap — a feeder may be simultaneously near overload AND
    low-confidence, or in the DR window with a wide band.  The rules below
    are evaluated top-to-bottom; the FIRST match wins.

    1. **low_confidence** (band_width > 0.15): Uncertainty dominates.  When
       the prediction band is wide, the point estimate is unreliable, so any
       overload/DR signal built on that point estimate is suspect.  We surface
       the uncertainty first and tell the operator to re-run.

    2. **overload_risk** (peak_pct >= 1.0): Assuming the band is tight enough
       to trust, exceeding nameplate is the highest-severity operational
       signal — it demands immediate switching or DR activation.

    3. **all_clear** (peak_pct < 0.75): With ample headroom the feeder needs
       no action.  Checked before DR / peak so we don't suggest intervention
       on a comfortable feeder.

    4. **demand_response** (0.85 <= peak_pct < 0.95): The "sweet spot" where
       enrolled curtailment alone can shave the peak, avoiding switching.

    5. **peak_forecast** (else): Catch-all for elevated load that doesn't
       meet a more specific threshold.
    """
    # Check band width first — uncertainty dominates when it's high
    if band_width > 0.15:
        return "low_confidence"
    if peak_pct >= 1.0:
        return "overload_risk"
    if peak_pct < 0.75:
        return "all_clear"
    if 0.85 <= peak_pct < 0.95:
        return "demand_response"
    return "peak_forecast"


def detect_scenario_with_flags(
    peak_pct: float,
    band_width: float,
) -> tuple[str, tuple[str, ...]]:
    """Return the primary scenario PLUS any secondary flags.

    Secondary flags capture overlapping conditions that didn't win the
    precedence race but may be operationally relevant as metadata.

    Returns
    -------
    primary : str
        The winning scenario id (same result as ``detect_scenario``).
    secondary_flags : tuple[str, ...]
        Zero or more scenario ids that *also* match their threshold but
        lost the precedence tiebreak.
    """
    primary = detect_scenario(peak_pct, band_width)
    flags: list[str] = []

    # Check every threshold independently, skipping the one that already won
    if band_width > 0.15 and primary != "low_confidence":
        flags.append("low_confidence")
    if peak_pct >= 1.0 and primary != "overload_risk":
        flags.append("overload_risk")
    if peak_pct < 0.75 and primary != "all_clear":
        flags.append("all_clear")
    if 0.85 <= peak_pct < 0.95 and primary != "demand_response":
        flags.append("demand_response")
    # peak_forecast is the catch-all; it's only interesting as a flag when
    # the primary is something else AND the feeder is genuinely elevated
    if peak_pct >= 0.85 and primary != "peak_forecast":
        flags.append("peak_forecast")

    return primary, tuple(flags)
