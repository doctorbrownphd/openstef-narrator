# OpenSTEF Narrator

An LLM-powered explainability layer that translates OpenSTEF forecast output into plain-language narrative reports for utility operators, regulators, and executives.

## Language

### Forecast domain

**Forecast**:
A 48-hour probabilistic load prediction for a single feeder, with p10/p50/p90 bands at hourly resolution. Produced by OpenSTEF.
_Avoid_: prediction, estimate

**Feeder**:
A distribution circuit serving a geographic area, with a known transformer rating (MW) and district name. The unit of forecasting.
_Avoid_: circuit, line, branch

**Exceedance probability**:
The probability that actual load exceeds the transformer's rated capacity during the forecast window. Computed from the p90 band and rating.
_Avoid_: overload chance, risk percentage

**Forecast context**:
A typed dataclass bundling everything the narrator needs: forecast points (p10/p50/p90 per hour), temperature series, feeder metadata (name, district, rating), and optional DR enrollment. The narrator's input contract.
_Avoid_: forecast data, input, payload

### Narrative domain

**Narrative report**:
The prose output of the narrator: situation, risk assessment, and recommendation sections. Contains `«fact»` markers around all injected numeric values.
_Avoid_: summary, explanation, alert

**Narrative metadata**:
Traceability fields attached to a report: narrative_id, forecast_run_id, backend used, verbosity, timestamp. Logged to the audit trail.
_Avoid_: report header, trace info

**Fact marker**:
The `«»` delimiters wrapping every injected numeric value in a narrative. Serves as UI highlighting, LLM hallucination boundary, and audit traceability. Part of the data contract.
_Avoid_: highlight, tag, placeholder

**Scenario**:
One of five operational situations that determines the narrative's tone, structure, and recommendation: peak forecast, overload risk, demand response, low confidence, all-clear. Auto-detected from forecast data, overridable by caller.
_Avoid_: template, case, mode

**Verbosity**:
The level of detail in the narrative: terse (2-3 sentences, dashboards), standard (full situation report), full (regulatory-grade with audit block).
_Avoid_: detail level, length

### Engine

**Template engine**:
The deterministic prose generator that produces a draft narrative with all `«facts»` injected. Always available, zero latency, no LLM dependency. The safety net when the LLM is unavailable.
_Avoid_: fallback, default engine

**Rewrite**:
The LLM operation that takes a template draft and produces natural prose while preserving all `«fact»` markers. The LLM shapes language, never numbers.
_Avoid_: generate, transform, polish

**Backend**:
An LLM provider implementing the `rewrite()` interface. Local (Ollama/Mistral) or cloud (OpenAI/Anthropic). Swappable without changing the narrator's API.
_Avoid_: model, provider, adapter

**Formatter**:
An output adapter that converts a narrative report into a delivery format: markdown, email, OperatorFabric card, SMS. Pluggable.
_Avoid_: renderer, serializer
