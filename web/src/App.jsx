import { useState, useEffect } from 'react';
import { Icon, Logo, Btn } from './components/ui.jsx';
import { useTweaks, TweaksPanel, TweakSection, TweakRadio, TweakToggle } from './components/TweaksPanel.jsx';
import { ForecastScreen } from './screens/ForecastScreen.jsx';
import { ScenariosScreen } from './screens/ScenariosScreen.jsx';
import { AuditScreen } from './screens/AuditScreen.jsx';

const NAV = [
  { id: 'forecast', label: 'Forecast', icon: 'trend' },
  { id: 'scenarios', label: 'Scenarios', icon: 'layers' },
  { id: 'audit', label: 'Audit', icon: 'audit' },
];

const TWEAK_DEFAULTS = {
  style: 'filament',
  layout: 'console',
  verbosity: 'standard',
  highlightFacts: true,
  dark: false,
  density: 'regular',
};

function TopBar({ tab, setTab, dark, setDark }) {
  return (
    <div style={{ position: 'sticky', top: 0, zIndex: 50, background: 'color-mix(in srgb, var(--paper) 88%, transparent)',
         backdropFilter: 'blur(10px)', borderBottom: '1px solid var(--line)' }}>
      <div style={{ maxWidth: 1340, margin: '0 auto', padding: '0 24px', height: 58,
           display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 26 }}>
          <Logo />
          <nav style={{ display: 'flex', gap: 2 }}>
            {NAV.map(n => (
              <button key={n.id} onClick={() => setTab(n.id)} style={{
                display: 'inline-flex', alignItems: 'center', gap: 7,
                padding: '7px 13px', fontSize: 13, fontWeight: tab === n.id ? 600 : 500, cursor: 'pointer',
                fontFamily: 'var(--font-ui)', border: 'none', borderRadius: 'var(--radius-sm)',
                color: tab === n.id ? 'var(--ink)' : 'var(--ink-2)',
                background: tab === n.id ? 'var(--surface-2)' : 'transparent', transition: 'all .14s',
              }}>
                <Icon name={n.icon} size={15} style={{ color: tab === n.id ? 'var(--accent)' : 'var(--ink-3)' }} />{n.label}
              </button>
            ))}
          </nav>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <span className="mono" style={{ fontSize: 11, color: 'var(--ink-3)', display: 'flex', alignItems: 'center', gap: 6 }}>
            <span style={{ width: 7, height: 7, borderRadius: 99, background: 'var(--ok)' }} />LF Energy &middot; OpenSTEF
          </span>
          <button onClick={() => setDark(!dark)} title="Toggle theme" style={{
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            width: 34, height: 34, cursor: 'pointer', border: '1px solid var(--line)', borderRadius: 'var(--radius-sm)',
            background: 'var(--surface)', color: 'var(--ink-2)',
          }}>
            <Icon name={dark ? 'sun' : 'moon'} size={16} />
          </button>
        </div>
      </div>
    </div>
  );
}

function PageHead({ tab }) {
  const meta = {
    forecast: { t: 'Forecast narrator', d: 'OpenSTEF predicts the load; the Narrator says what it means. Pick a feeder to see its 48-hour forecast translated into a plain-language situation report \u2014 what will happen, what is driving it, and whether to act.' },
    scenarios: { t: 'Prompt library', d: 'Five scenario templates cover the operating cases that matter: peak forecast, transformer-overload risk, demand-response opportunity, low-confidence alert, and all-clear. Each renders the same structured forecast into operator-grade prose.' },
    audit: { t: 'Audit trail', d: 'Every narrative is versioned and linked to the forecast run that produced it, with the backend and delivery targets recorded. Numeric facts are injected from the forecast \u2014 so each report is fully traceable.' },
  }[tab];
  return (
    <div style={{ marginBottom: 22, maxWidth: 800 }}>
      <div className="mono" style={{ fontSize: 11, letterSpacing: '0.06em', color: 'var(--accent)', textTransform: 'uppercase', marginBottom: 9 }}>
        OpenSTEF Narrator &middot; forecast explainability layer</div>
      <h1 style={{ fontSize: 27, fontWeight: 600, letterSpacing: '-0.025em', marginBottom: 9 }}>{meta.t}</h1>
      <p style={{ fontSize: 14, color: 'var(--ink-2)', lineHeight: 1.6, margin: 0, textWrap: 'pretty' }}>{meta.d}</p>
    </div>
  );
}

export default function App() {
  const [t, setTweak] = useTweaks(TWEAK_DEFAULTS);
  const [tab, setTab] = useState('forecast');

  useEffect(() => {
    const r = document.documentElement;
    r.setAttribute('data-style', t.style);
    r.setAttribute('data-theme', t.dark ? 'dark' : 'light');
    r.style.setProperty('font-size', t.density === 'compact' ? '13px' : t.density === 'comfy' ? '15px' : '14px');
  }, [t.style, t.dark, t.density]);

  return (
    <div style={{ minHeight: '100vh' }}>
      <TopBar tab={tab} setTab={setTab} dark={t.dark} setDark={v => setTweak('dark', v)} />
      <main style={{ maxWidth: 1340, margin: '0 auto', padding: '26px 24px 80px' }}>
        <PageHead tab={tab} />
        {tab === 'forecast' && <ForecastScreen layout={t.layout} verbosity={t.verbosity} highlightFacts={t.highlightFacts} />}
        {tab === 'scenarios' && <ScenariosScreen />}
        {tab === 'audit' && <AuditScreen />}
      </main>

      <TweaksPanel>
        <TweakSection label="Visual style" />
        <TweakRadio label="Theme" value={t.style} options={['spruce', 'graphite', 'filament']}
                    onChange={v => setTweak('style', v)} />
        <TweakToggle label="Dark mode" value={t.dark} onChange={v => setTweak('dark', v)} />
        <TweakSection label="Narrative" />
        <TweakRadio label="Verbosity" value={t.verbosity} options={['terse', 'standard', 'full']}
                    onChange={v => setTweak('verbosity', v)} />
        <TweakToggle label="Highlight injected facts" value={t.highlightFacts} onChange={v => setTweak('highlightFacts', v)} />
        <TweakSection label="Forecast layout" />
        <TweakRadio label="Arrangement" value={t.layout} options={['console', 'split', 'stacked']}
                    onChange={v => setTweak('layout', v)} />
        <TweakSection label="Density" />
        <TweakRadio label="Scale" value={t.density} options={['compact', 'regular', 'comfy']}
                    onChange={v => setTweak('density', v)} />
      </TweaksPanel>
    </div>
  );
}
