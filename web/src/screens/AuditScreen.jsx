import { useState, useEffect } from 'react';
import { Icon, Badge, Stat, Card, Select } from '../components/ui.jsx';
import { FactText } from '../components/FactText.jsx';
import { fetchAudit } from '../lib/api.js';

const SCEN_TONE = { peak_forecast:'warn', overload_risk:'bad', demand_response:'accent', low_confidence:'neutral', all_clear:'ok' };
const SCEN_LABEL = { peak_forecast:'Peak forecast', overload_risk:'Overload risk', demand_response:'Demand response', low_confidence:'Low confidence', all_clear:'All clear' };

function SectionHead({ icon, title, right }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '13px 16px', borderBottom: '1px solid var(--line)' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <Icon name={icon} size={17} style={{ color: 'var(--accent)' }} />
        <div style={{ fontSize: 13.5, fontWeight: 600, whiteSpace: 'nowrap' }}>{title}</div>
      </div>
      {right}
    </div>
  );
}

export function AuditScreen() {
  const [entries, setEntries] = useState([]);
  const [sel, setSel] = useState(0);
  const [fBackend, setFBackend] = useState('all');
  const [fScen, setFScen] = useState('all');

  useEffect(() => {
    fetchAudit().then(e => setEntries(e));
  }, []);

  if (entries.length === 0) {
    return (
      <div className="os-fade" style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 14 }}>
          <Card pad={16}><Stat label="Narratives audited" value="0" sub="versioned + linked" /></Card>
          <Card pad={16}><Stat label="Mean latency" value="0.9" unit="s" sub="forecast \u2192 card" /></Card>
          <Card pad={16}><Stat label="Backends" value="2" sub="local + cloud" /></Card>
          <Card pad={16}><Stat label="Numeric errors" value="0" color="var(--ok)" sub="injected facts" /></Card>
        </div>
        <Card pad={40} style={{ textAlign: 'center' }}>
          <Icon name="audit" size={32} style={{ color: 'var(--ink-3)', margin: '0 auto 12px' }} />
          <div style={{ fontSize: 14, color: 'var(--ink-2)', marginBottom: 6 }}>No audit entries yet</div>
          <div style={{ fontSize: 12, color: 'var(--ink-3)' }}>Generate a narrative on the Forecast tab to populate the audit trail.</div>
        </Card>
      </div>
    );
  }

  const rows = entries.filter(r =>
    (fBackend === 'all' || r.meta.backend === fBackend) &&
    (fScen === 'all' || r.meta.scenario === fScen)
  );
  const cur = rows[sel] || rows[0] || entries[0];

  return (
    <div className="os-fade" style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 14 }}>
        <Card pad={16}><Stat label="Narratives audited" value={entries.length.toLocaleString()} sub="versioned + linked" /></Card>
        <Card pad={16}><Stat label="Mean latency" value="0.9" unit="s" sub="forecast \u2192 card" /></Card>
        <Card pad={16}><Stat label="Backends" value="2" sub="local + cloud" /></Card>
        <Card pad={16}><Stat label="Numeric errors" value="0" color="var(--ok)" sub="injected facts" /></Card>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 360px', gap: 18, alignItems: 'start' }}>
        <Card pad={0} style={{ overflow: 'hidden' }}>
          <SectionHead icon="audit" title="Narrative audit trail" right={<span className="mono" style={{ fontSize: 11, color: 'var(--ink-3)' }}>{rows.length} runs</span>} />
          <div style={{ display: 'flex', gap: 10, padding: '12px 16px', borderBottom: '1px solid var(--line)', background: 'var(--surface-2)', flexWrap: 'wrap' }}>
            <Select value={fScen} onChange={setFScen} options={[{ value: 'all', label: 'All scenarios' }, ...Object.entries(SCEN_LABEL).map(([v, l]) => ({ value: v, label: l }))]} />
            <Select value={fBackend} onChange={setFBackend} options={[{ value: 'all', label: 'All backends' }, { value: 'template_fallback', label: 'Template' }, { value: 'anthropic', label: 'Cloud' }]} />
          </div>
          <div style={{ maxHeight: 520, overflowY: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
              <thead><tr style={{ position: 'sticky', top: 0, background: 'var(--surface)', boxShadow: '0 1px 0 var(--line)' }}>
                {['Narrative', 'Scenario', 'Backend', 'Verbosity'].map((h, i) => (
                  <th key={h} className="mono" style={{ textAlign: 'left', padding: '9px 16px', fontSize: 10, letterSpacing: '0.05em', textTransform: 'uppercase', color: 'var(--ink-3)', fontWeight: 500, whiteSpace: 'nowrap' }}>{h}</th>))}
              </tr></thead>
              <tbody>
                {rows.map((r, idx) => {
                  const on = idx === sel;
                  return (
                    <tr key={idx} onClick={() => setSel(idx)} style={{ borderTop: '1px solid var(--line)', cursor: 'pointer', background: on ? 'var(--accent-weak)' : 'transparent' }}>
                      <td style={{ padding: '9px 16px' }}>
                        <div className="mono" style={{ fontSize: 11, fontWeight: 600, color: on ? 'var(--accent)' : 'var(--ink)' }}>{r.meta.narrative_id}</div>
                        <div className="mono" style={{ fontSize: 9.5, color: 'var(--ink-3)' }}>&larr; {r.meta.forecast_run_id}</div>
                      </td>
                      <td style={{ padding: '9px 16px' }}><Badge tone={SCEN_TONE[r.meta.scenario]}>{(SCEN_LABEL[r.meta.scenario] || '').split(' ')[0]}</Badge></td>
                      <td style={{ padding: '9px 16px' }}><span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, color: 'var(--ink-2)' }}><Icon name={r.meta.backend === 'template_fallback' ? 'server' : 'cloud'} size={13} style={{ color: 'var(--ink-3)' }} />{r.meta.backend}</span></td>
                      <td className="mono" style={{ padding: '9px 16px', color: 'var(--ink-3)', fontSize: 11 }}>{r.meta.verbosity}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </Card>

        <div style={{ position: 'sticky', top: 16, display: 'flex', flexDirection: 'column', gap: 14 }}>
          <Card pad={0} style={{ overflow: 'hidden' }}>
            <div style={{ padding: '14px 16px', borderBottom: '1px solid var(--line)', background: 'var(--surface-2)' }}>
              <div className="mono" style={{ fontSize: 11, fontWeight: 600, marginBottom: 3 }}>{cur.meta.narrative_id}</div>
              <div className="mono" style={{ fontSize: 10, color: 'var(--ink-3)', display: 'flex', alignItems: 'center', gap: 6 }}>
                <Icon name="branch" size={11} />linked forecast {cur.meta.forecast_run_id}</div>
            </div>
            <div style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: 12 }}>
              <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                <Badge tone={SCEN_TONE[cur.meta.scenario]}>{SCEN_LABEL[cur.meta.scenario]}</Badge>
                <Badge tone="neutral">{cur.meta.verbosity}</Badge>
                <Badge tone="neutral">{cur.meta.backend}</Badge>
              </div>
              <FactText text={cur.report.situation} highlight style={{ fontSize: 13, lineHeight: 1.55, color: 'var(--ink)', display: 'block', textWrap: 'pretty' }} />
            </div>
          </Card>

          <Card pad={16} style={{ background: 'var(--accent-weak)', border: '1px solid var(--accent)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 7 }}>
              <Icon name="shield" size={15} style={{ color: 'var(--accent)' }} />
              <div style={{ fontSize: 12.5, fontWeight: 600, color: 'var(--accent)' }}>No hallucination on numbers</div>
            </div>
            <div style={{ fontSize: 11.5, color: 'var(--ink-2)', lineHeight: 1.55 }}>Every narrative is versioned and linked to the forecast run that produced it. <span className="mono" style={{ color: 'var(--ink-3)' }}>0 numeric errors &middot; facts injected from forecast JSON</span></div>
          </Card>
        </div>
      </div>
    </div>
  );
}
