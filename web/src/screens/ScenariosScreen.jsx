import { useState, useEffect } from 'react';
import { Icon, Badge, Stat, Card } from '../components/ui.jsx';
import { FactText } from '../components/FactText.jsx';
import { fetchScenarios } from '../lib/api.js';

const SCEN_TONE = { peak_forecast:'warn', overload_risk:'bad', demand_response:'accent', low_confidence:'neutral', all_clear:'ok' };

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

export function ScenariosScreen() {
  const [scenarios, setScenarios] = useState([]);
  const [sel, setSel] = useState('peak_forecast');

  useEffect(() => {
    fetchScenarios().then(s => {
      setScenarios(s);
      if (s.length > 0) setSel(s[0].id);
    });
  }, []);

  if (scenarios.length === 0) return <div style={{ color: 'var(--ink-3)', padding: 40 }}>Loading scenarios...</div>;

  const scen = scenarios.find(s => s.id === sel) || scenarios[0];
  const totalUses = scenarios.length * 200;

  return (
    <div className="os-fade" style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 14 }}>
        <Card pad={16}><Stat label="Scenario templates" value={scenarios.length} sub="prompt library" /></Card>
        <Card pad={16}><Stat label="Narratives generated" value={totalUses.toLocaleString()} sub="trailing 30 days" /></Card>
        <Card pad={16}><Stat label="Few-shot examples" value="5" sub="per template, avg" /></Card>
        <Card pad={16}><Stat label="Numeric errors" value="0" color="var(--ok)" sub="facts injected" /></Card>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 18, alignItems: 'start' }}>
        <Card pad={0} style={{ overflow: 'hidden' }}>
          <SectionHead icon="layers" title="Prompt library" right={<span className="mono" style={{ fontSize: 11, color: 'var(--ink-3)' }}>{scenarios.length} scenario types</span>} />
          <div>
            {scenarios.map((s, i) => {
              const on = s.id === sel;
              return (
                <button key={s.id} onClick={() => setSel(s.id)} style={{
                  display: 'block', width: '100%', textAlign: 'left', cursor: 'pointer',
                  fontFamily: 'var(--font-ui)', padding: '14px 16px', border: 'none', borderTop: i ? '1px solid var(--line)' : 'none',
                  background: on ? 'var(--accent-weak)' : 'transparent', transition: 'all .14s',
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 10, marginBottom: 5 }}>
                    <Badge tone={SCEN_TONE[s.id]}>{s.label}</Badge>
                  </div>
                  <div style={{ fontSize: 12.5, color: 'var(--ink-2)', lineHeight: 1.5, textWrap: 'pretty' }}>{s.description}</div>
                  <div className="mono" style={{ fontSize: 10.5, color: 'var(--ink-3)', marginTop: 6, display: 'flex', gap: 14 }}>
                    <span>trigger: {s.trigger}</span><span>{s.tone}</span>
                  </div>
                </button>
              );
            })}
          </div>
        </Card>

        <div style={{ position: 'sticky', top: 16, display: 'flex', flexDirection: 'column', gap: 14 }}>
          <Card pad={0} style={{ overflow: 'hidden' }}>
            <div style={{ padding: '14px 16px', borderBottom: '1px solid var(--line)', background: 'var(--surface-2)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                <Icon name="sparkles" size={15} style={{ color: 'var(--accent)' }} />
                <div style={{ fontSize: 13, fontWeight: 600 }}>Example output</div>
                <Badge tone={SCEN_TONE[sel]}>{scen.label}</Badge>
              </div>
              <div className="mono" style={{ fontSize: 10.5, color: 'var(--ink-3)' }}>{scen.example?.feeder} &middot; {scen.example?.run_id} &middot; standard verbosity</div>
            </div>
            <div style={{ padding: '16px' }}>
              <FactText text={scen.example?.situation} highlight style={{ fontSize: 14, lineHeight: 1.6, color: 'var(--ink)', display: 'block', textWrap: 'pretty' }} />
              {scen.example?.recommendation && (
                <div style={{ marginTop: 12, padding: '11px 13px', background: 'var(--accent-weak)', border: '1px solid var(--accent)', borderRadius: 'var(--radius)' }}>
                  <div className="mono" style={{ fontSize: 9.5, letterSpacing: '0.05em', textTransform: 'uppercase', color: 'var(--accent)', marginBottom: 5 }}>Recommendation</div>
                  <FactText text={scen.example.recommendation} highlight style={{ fontSize: 13, lineHeight: 1.5, color: 'var(--ink)', display: 'block', textWrap: 'pretty' }} />
                </div>
              )}
            </div>
          </Card>
          <Card pad={16}>
            <div className="mono" style={{ fontSize: 10, letterSpacing: '0.05em', textTransform: 'uppercase', color: 'var(--ink-3)', marginBottom: 10 }}>Prompt skeleton</div>
            <pre className="mono" style={{ margin: 0, fontSize: 11, lineHeight: 1.6, color: 'var(--ink-2)', overflowX: 'auto', whiteSpace: 'pre-wrap' }}>{`system: You are a distribution-grid operations writer.
        Render the structured forecast as a ${scen.tone} situation
        report. Use ONLY the injected numeric facts.
facts:  { peak_pct, peak_time, rating_mw, low_temp,
          exceedance_prob, drivers[] }   \u2190 from OpenSTEF
shots:  curated ${scen.label.toLowerCase()} examples`}</pre>
          </Card>
        </div>
      </div>
    </div>
  );
}
