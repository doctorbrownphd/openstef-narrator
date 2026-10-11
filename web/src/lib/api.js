const START_HOUR = 14;

function clockLabel(absHour) {
  const day = Math.floor(absHour / 24), hod = absHour % 24;
  const d = day === 0 ? 'today' : day === 1 ? 'tomorrow' : `in ${day} days`;
  return { day: d, time: `${String(hod).padStart(2, '0')}:00`, label: `${d} ${String(hod).padStart(2, '0')}:00` };
}

export function transformForecast(data) {
  const points = data.points.map(p => ({
    h: p.hour,
    abs: START_HOUR + p.hour,
    hod: p.hour_of_day,
    p10: p.p10,
    p50: p.p50,
    p90: p.p90,
    temp: p.temperature,
  }));
  const peakPt = points.reduce((a, p) => p.p50 > a.p50 ? p : a);
  return {
    feederId: data.feeder_id,
    feeder: { id: data.feeder_id, name: data.feeder_name, district: data.district, cap: data.capacity_mw, scenario: data.scenario },
    cap: data.capacity_mw,
    points,
    peak: { ...peakPt, pct: data.peak_pct, clock: clockLabel(START_HOUR + data.peak_hour) },
    exceedance: data.exceedance_prob,
    confidence: data.confidence,
    scenario: data.scenario,
    bandPct: data.band_width,
    lowTemp: data.low_temp,
    runId: data.forecast_run_id,
    drivers: data.drivers,
  };
}

export async function fetchFeeders() {
  const res = await fetch('/api/feeders');
  const data = await res.json();
  return data.feeders;
}

export async function fetchForecast(feederId, seed = 42) {
  const res = await fetch(`/api/forecast?feeder_id=${feederId}&seed=${seed}`);
  const data = await res.json();
  return transformForecast(data);
}

export async function fetchNarrate(feederId, verbosity = 'standard', seed = 42) {
  const res = await fetch('/api/narrate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ feeder_id: feederId, verbosity, seed }),
  });
  return res.json();
}

export async function fetchScenarios() {
  const res = await fetch('/api/scenarios');
  const data = await res.json();
  return data.scenarios;
}

export async function fetchAudit() {
  const res = await fetch('/api/audit');
  const data = await res.json();
  return data.entries;
}
