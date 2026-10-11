# OpenSTEF Narrator

Plain-language reports for probabilistic feeder load forecasts. The narrator takes a 48-hour forecast with p10, p50, and p90 bands and writes the situation report an operator, a regulator, or an executive would want: what load is expected, how likely the feeder is to exceed its rating, how confident the forecast is, and what to do about it.

It is built to sit on top of [OpenSTEF](https://lfenergy.org/projects/openstef/), the LF Energy short-term forecasting project. It is a standalone package, not a fork, and it is not affiliated with OpenSTEF or LF Energy.

## How it keeps the numbers honest

An LLM writing about grid conditions can invent a number or a cause. The narrator is designed so that it can't.

1. A deterministic template engine writes a draft and wraps every injected fact in `«»` markers: peak load, rating, exceedance probability, timing, and the load drivers.
2. An LLM optionally rewrites the prose between the markers. It can reorder and rephrase facts, but it can't add or change them.
3. A validator rejects any rewrite that drops a marker, alters one, or introduces a number that isn't inside a marker. On rejection, or when no LLM is configured, the template draft ships unchanged.
4. The highest-severity scenario, overload risk, is template-only by policy, so the most urgent reports never depend on an outside API.

Every report goes to a SQLite audit trail with the forecast run ID, a hash of the report text, the backend requested and the one actually used (template or LLM, with the model version), the validation result, and any sections that fell back to the template. A reviewer can trace what an operator saw and how it was produced.

## What it does

- **Scenario detection:** classifies each forecast as peak forecast, overload risk, demand response, low confidence, or all clear, and sets tone, structure, and recommendation to match.
- **Verbosity levels:** terse for dashboards, standard for situation reports, and full for regulatory use with an audit block.
- **Load drivers:** decomposes the forecast into load components and reports them as marked facts.
- **Uncertainty hedging:** wording follows forecast confidence, and scenario flags call out conditions such as a wide band.
- **System rollup:** a single summary across all feeders.
- **Historical analogues and counterfactuals:** past events that resemble the current forecast, drawn from a seeded event store, and "what if it runs 5 °F colder" style alternatives.
- **Operator feedback:** operators rate narratives, and the ratings are stored with the audit record.
- **Delivery:** formatters for Markdown, email, SMS, and [OperatorFabric](https://opfab.github.io/) cards.
- **Weather:** pulls National Weather Service forecasts for each feeder's district.

## Data

The five feeders and their forecasts are synthetic. Feeder names, districts, ratings, loads, and the historical events are invented for the demo. Weather locations point at real New England towns only so the National Weather Service lookup returns real temperatures. `ForecastContext.from_openstef()` accepts an OpenSTEF forecast DataFrame, but it hasn't yet been tested against live OpenSTEF output.

An optional bridge to [OpenSynth New England](https://github.com/doctorbrownphd/opensynth-newengland) builds feeder forecasts from synthetic smart meter profiles.

## Running it

Requires Python 3.10 or later and Node.js for the web app.

```bash
pip install -e ".[api,llm,weather]"
make build                      # build the React front end
python -m openstef_narrator.api # serves the API and the app on port 8001
```

To use the LLM rewrite, set `ANTHROPIC_API_KEY`. Without it, the narrator uses the template engine alone.

To run the tests:

```bash
pip install -e ".[api,dev,weather]"
python -m pytest tests -q
```

## Design decisions

The `docs/adr/` folder records why the narrator is a standalone repo, why it pairs a template engine with an LLM rewrite, and why the `«»` markers are the data contract.

## License

Apache-2.0. See [LICENSE](LICENSE).
