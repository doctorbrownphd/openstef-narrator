import { useState, useEffect, useMemo } from 'react';
import { Icon, Badge, Stat, Card, CodeBlock } from '../components/ui.jsx';
import { FactText } from '../components/FactText.jsx';
import { ForecastChart, CapacityGauge } from '../components/Charts.jsx';
import { fetchFeeders, fetchForecast, fetchNarrate } from '../lib/api.js';

const SCEN_TONE = { peak_forecast:'warn', overload_risk:'bad', demand_response:'accent', low_confidence:'neutral', all_clear:'ok' };
const SCEN_LABEL = { peak_forecast:'Peak forecast', overload_risk:'Overload risk', demand_response:'Demand response', low_confidence:'Low confidence', all_clear:'All clear' };

function FeederPicker({ feeders, value, onChange, forecasts }) {
  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: 8 }}>
      {feeders.map(f => {
        const on = f.id === value;
        const fc = forecasts[f.id];
        const peakPct = fc ? fc.peak.pct : f.peak_pct;
        return (
          <button key={f.id} onClick={() => onChange(f.id)} style={{
            textAlign: 'left', cursor: 'pointer', fontFamily: 'var(--font-ui)',
            display: 'flex', flexDirection: 'column', gap: 7, width: '100%',
            background: on ? 'var(--accent-weak)' : 'var(--surface)', border: `1px solid ${on ? 'var(--accent)' : 'var(--line)'}`,
            borderRadius: 'var(--radius)', padding: '10px 12px', transition: 'all .14s',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8 }}>
              <span style={{ fontSize: 13, fontWeight: 600 }}>{f.name}</span>
              <Badge tone={SCEN_TONE[f.scenario]}>{(SCEN_LABEL[f.scenario] || '').split(' ')[0]}</Badge>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8 }}>
              <span className="mono" style={{ fontSize: 10.5, color: 'var(--ink-3)' }}>{f.district}</span>
              <span className="mono tnum" style={{ fontSize: 12, fontWeight: 600, color: peakPct >= 1 ? 'var(--bad)' : peakPct >= 0.9 ? 'var(--f-driver)' : peakPct >= 0.75 ? 'var(--warn)' : 'var(--ok)' }}>{Math.round(peakPct * 100)}%</span>
            </div>
          </button>
        );
      })}
    </div>
  );
}

function ReportCard({ fc, narration, highlight }) {
  const [delivered, setDelivered] = useState('OperatorFabric');
  if (!narration) return <Card pad={18}><div style={{ color: 'var(--ink-3)', fontSize: 13 }}>Generating narrative...</div></Card>;

  const report = narration.report;
  const drivers = fc.drivers || [];

  const Block = ({ icon, label, children, accent }) => (
    <div style={{ padding: '15px 0', borderTop: '1px solid var(--line)' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 9 }}>
        <Icon name={icon} size={14} style={{ color: accent ? 'var(--accent)' : 'var(--ink-3)' }} />
        <span className="mono" style={{ fontSize: 10.5, letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--ink-2)', fontWeight: 600 }}>{label}</span>
      </div>
      {children}
    </div>
  );

  return (
    <Card pad={0} style={{ overflow: 'hidden' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '13px 18px', borderBottom: '1px solid var(--line)', background: 'var(--surface-2)', flexWrap: 'wrap', gap: 8 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 9 }}>
          <Icon name="sparkles" size={16} style={{ color: 'var(--accent)' }} />
          <div style={{ fontSize: 13.5, fontWeight: 600 }}>Narrative report</div>
          <Badge tone={SCEN_TONE[fc.scenario]}>{SCEN_LABEL[fc.scenario]}</Badge>
        </div>
        <span className="mono" style={{ fontSize: 10, color: 'var(--ink-3)' }}>{narration.meta.narrative_id} &middot; {narration.meta.verbosity}</span>
      </div>

      <div style={{ padding: '4px 18px 16px' }}>
        <div style={{ paddingTop: 15 }}>
          <FactText text={report.situation} highlight={highlight}
            style={{ fontSize: 15.5, lineHeight: 1.62, color: 'var(--ink)', display: 'block', textWrap: 'pretty' }} />
        </div>

        <Block icon="trend" label="Drivers">
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            {drivers.map((d, i) => (
              <span key={i} style={{ display: 'inline-flex', alignItems: 'center', gap: 7, padding: '6px 10px', background: 'var(--surface-2)',
                border: '1px solid var(--line)', borderRadius: 99 }}>
                <Icon name={d.icon} size={14} style={{ color: 'var(--f-driver)' }} />
                <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--ink)' }}>{d.label}</span>
                <span className="mono" style={{ fontSize: 10, color: 'var(--ink-3)' }}>{d.detail}</span>
              </span>
            ))}
          </div>
        </Block>

        <Block icon="gauge" label="Risk & confidence">
          <FactText text={report.risk} highlight={highlight} style={{ fontSize: 13.5, lineHeight: 1.6, color: 'var(--ink-2)', display: 'block', textWrap: 'pretty' }} />
        </Block>

        <Block icon="send" label="Recommendation" accent>
          <div style={{ padding: '12px 14px', background: 'var(--accent-weak)', border: '1px solid var(--accent)', borderRadius: 'var(--radius)' }}>
            <FactText text={report.recommendation} highlight={highlight} style={{ fontSize: 13.5, lineHeight: 1.55, color: 'var(--ink)', display: 'block', fontWeight: 500, textWrap: 'pretty' }} />
          </div>
        </Block>

        {report.audit && (
          <div style={{ marginTop: 14, paddingTop: 13, borderTop: '1px dashed var(--line-strong)' }}>
            <FactText text={report.audit} highlight={highlight} style={{ fontSize: 11, lineHeight: 1.55, color: 'var(--ink-3)', display: 'block' }} />
          </div>
        )}
      </div>

      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12, padding: '11px 18px', borderTop: '1px solid var(--line)', background: 'var(--surface-2)', flexWrap: 'wrap' }}>
        <span style={{ fontSize: 11, color: 'var(--ink-3)', display: 'flex', alignItems: 'center', gap: 6 }}>
          <Icon name="shield" size={13} />Numbers injected from forecast — never model-generated</span>
        <div style={{ display: 'flex', gap: 6 }}>
          {[['OperatorFabric', 'grid'], ['email', 'mail'], ['sms', 'sms']].map(([k, ic]) => (
            <button key={k} onClick={() => setDelivered(k)} title={`Deliver to ${k}`} style={{
              display: 'inline-flex', alignItems: 'center', gap: 6, padding: '6px 10px',
              fontSize: 11.5, fontFamily: 'var(--font-ui)', cursor: 'pointer', borderRadius: 'var(--radius-sm)',
              border: `1px solid ${delivered === k ? 'var(--accent)' : 'var(--line)'}`, background: delivered === k ? 'var(--accent-weak)' : 'var(--surface)',
              color: delivered === k ? 'var(--accent)' : 'var(--ink-2)', fontWeight: 500,
            }}>
              <Icon name={ic} size={13} />{k}</button>
          ))}
        </div>
      </div>
    </Card>
  );
}

function snippet(fc, verbosity) {
  return `<span style="color:var(--ink-3)"># pip install openstef-narrator</span>
<span style="color:var(--f-driver)">from</span> openstef_narrator <span style="color:var(--f-driver)">import</span> explain

report = explain(
    forecast_run=<span style="color:var(--f-load)">"${fc.runId}"</span>,
    verbosity=<span style="color:var(--f-load)">"${verbosity}"</span>,
    backend=<span style="color:var(--f-load)">"local"</span>,
)
<span style="color:var(--ink-3)"># report.situation / .risk / .recommendation
# every numeric fact traces back to ${fc.runId}</span>`;
}

export function ForecastScreen({ layout = 'console', verbosity = 'standard', highlightFacts = true }) {
  const [feederId, setFeederId] = useState('feeder7');
  const [feeders, setFeeders] = useState([]);
  const [fc, setFc] = useState(null);
  const [narration, setNarration] = useState(null);
  const [forecasts, setForecasts] = useState({});

  useEffect(() => {
    fetchFeeders().then(f => {
      setFeeders(f);
      // pre-fetch forecasts for picker badges
      f.forEach(feeder => fetchForecast(feeder.id).then(fc => setForecasts(prev => ({ ...prev, [feeder.id]: fc }))));
    });
  }, []);

  useEffect(() => {
    fetchForecast(feederId).then(setFc);
    setNarration(null);
  }, [feederId]);

  useEffect(() => {
    if (!fc) return;
    fetchNarrate(feederId, verbosity).then(setNarration);
  }, [fc, verbosity]);

  if (!fc || feeders.length === 0) return <div style={{ color: 'var(--ink-3)', padding: 40 }}>Loading forecast...</div>;

  const chartCard = (
    <Card pad={0} style={{ overflow: 'hidden' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 16px', borderBottom: '1px solid var(--line)', flexWrap: 'wrap', gap: 10 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <Icon name="trend" size={18} style={{ color: 'var(--accent)' }} />
          <div>
            <div style={{ fontSize: 13.5, fontWeight: 600 }}>{fc.feeder.name} &middot; 48-hour load forecast</div>
            <div className="mono" style={{ fontSize: 10.5, color: 'var(--ink-3)' }}>{fc.feeder.district} &middot; {fc.runId} &middot; hourly p50 + p10&ndash;p90 band</div>
          </div>
        </div>
        <div style={{ display: 'flex', gap: 13, flexWrap: 'wrap' }}>
          {[['var(--f-load)', 'p50 load', true], ['var(--f-band)', 'p10\u2013p90', false], ['var(--f-cap)', 'rating', true], ['var(--f-temp)', 'temp', true]].map(([c, l, line], i) => (
            <span key={i} style={{ display: 'inline-flex', alignItems: 'center', gap: 5, fontSize: 11, color: 'var(--ink-2)' }}>
              <span style={{ width: 14, height: !line ? 9 : 2, borderRadius: !line ? 2 : 0, background: c, display: 'inline-block' }} />{l}</span>
          ))}
        </div>
      </div>
      <div style={{ padding: '14px 12px 6px' }}>
        <ForecastChart fc={fc} height={layout === 'stacked' ? 340 : 300} />
      </div>
    </Card>
  );

  const stats = (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(120px,1fr))', gap: 12 }}>
      <Card pad={14}><Stat label="Forecast peak" value={`${Math.round(fc.peak.pct * 100)}%`} sub={`${fc.peak.p50.toFixed(1)} of ${fc.cap.toFixed(1)} MW`} color={fc.peak.pct >= 1 ? 'var(--bad)' : fc.peak.pct >= 0.9 ? 'var(--f-driver)' : 'var(--accent)'} /></Card>
      <Card pad={14}><Stat label="Peak window" value={fc.peak.clock.time} sub={fc.peak.clock.day} /></Card>
      <Card pad={14}><Stat label="Exceedance" value={`${Math.round(fc.exceedance * 100)}%`} unit="prob" sub="P(load > rating)" color={fc.exceedance >= 0.3 ? 'var(--bad)' : fc.exceedance >= 0.1 ? 'var(--warn)' : 'var(--ok)'} /></Card>
      <Card pad={14}><Stat label="Confidence" value={fc.confidence} sub={`\u00B1${Math.round(fc.bandPct * 100)}% band`} /></Card>
    </div>
  );

  const gaugeCard = (
    <Card pad={16}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
        <div style={{ fontSize: 12.5, fontWeight: 600 }}>Peak vs transformer rating</div>
        <Badge tone={fc.peak.pct >= 1 ? 'bad' : fc.peak.pct >= 0.9 ? 'warn' : 'ok'}>{fc.peak.pct >= 1 ? 'over rating' : fc.peak.pct >= 0.9 ? 'near rating' : 'headroom'}</Badge>
      </div>
      <CapacityGauge pct={fc.peak.pct} />
    </Card>
  );

  const report = <ReportCard fc={fc} narration={narration} highlight={highlightFacts} />;
  const code = <CodeBlock code={snippet(fc, verbosity)} />;

  const configCard = (
    <Card pad={18} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 9 }}>
        <Icon name="trend" size={17} style={{ color: 'var(--accent)' }} />
        <div style={{ fontSize: 13.5, fontWeight: 600 }}>Forecast feeder</div>
        <Badge tone="accent">OpenSTEF</Badge>
      </div>
      <FeederPicker feeders={feeders} value={feederId} onChange={setFeederId} forecasts={forecasts} />
      {code}
    </Card>
  );

  const results = (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      {chartCard}{stats}
      <div style={{ display: 'grid', gridTemplateColumns: layout === 'split' ? '1fr' : '1.5fr 1fr', gap: 14, alignItems: 'start' }}>
        {report}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>{gaugeCard}{layout === 'split' ? code : null}</div>
      </div>
    </div>
  );

  if (layout === 'stacked') {
    return <div className="os-fade" style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      {chartCard}{stats}
      <div style={{ display: 'grid', gridTemplateColumns: '1.5fr 1fr', gap: 16, alignItems: 'start' }}>{report}<div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>{gaugeCard}{code}</div></div>
    </div>;
  }
  if (layout === 'split') {
    return <div className="os-fade" style={{ display: 'grid', gridTemplateColumns: '1fr 360px', gap: 18, alignItems: 'start' }}>
      {results}<div style={{ position: 'sticky', top: 16 }}>{configCard}</div></div>;
  }
  return <div className="os-fade" style={{ display: 'grid', gridTemplateColumns: '330px 1fr', gap: 18, alignItems: 'start' }}>
    <div style={{ position: 'sticky', top: 16 }}>{configCard}</div>{results}</div>;
}
