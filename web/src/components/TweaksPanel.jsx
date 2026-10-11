import { useState, useCallback } from 'react';

export function useTweaks(defaults) {
  const [values, setValues] = useState(defaults);
  const setTweak = useCallback((key, val) => {
    setValues(prev => ({ ...prev, [key]: val }));
  }, []);
  return [values, setTweak];
}

export function TweaksPanel({ children }) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <button onClick={() => setOpen(!open)} title="Tweaks" style={{
        position: 'fixed', bottom: 16, right: 16, zIndex: 999, width: 36, height: 36,
        borderRadius: 99, border: '1px solid var(--line)', background: 'var(--surface)',
        boxShadow: 'var(--shadow-md)', cursor: 'pointer', display: 'flex', alignItems: 'center',
        justifyContent: 'center', fontSize: 16, color: 'var(--ink-2)',
      }}>
        {open ? '\u2715' : '\u2699'}
      </button>
      {open && (
        <div style={{
          position: 'fixed', bottom: 60, right: 16, zIndex: 998, width: 260,
          maxHeight: 'calc(100vh - 80px)', overflowY: 'auto',
          background: 'var(--surface)', border: '1px solid var(--line)',
          borderRadius: 'var(--radius-lg)', boxShadow: 'var(--shadow-lg)',
          padding: '14px 16px', display: 'flex', flexDirection: 'column', gap: 10,
          fontFamily: 'var(--font-ui)', fontSize: 12,
        }}>
          <div style={{ fontWeight: 600, fontSize: 12, marginBottom: 4 }}>Tweaks</div>
          {children}
        </div>
      )}
    </>
  );
}

export function TweakSection({ label }) {
  return <div style={{ fontSize: 10, fontWeight: 600, letterSpacing: '0.06em', textTransform: 'uppercase',
    color: 'var(--ink-3)', paddingTop: 8 }}>{label}</div>;
}

export function TweakRadio({ label, value, options, onChange }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
      <div style={{ fontSize: 11, color: 'var(--ink-2)', fontWeight: 500 }}>{label}</div>
      <div style={{ display: 'flex', background: 'var(--surface-2)', border: '1px solid var(--line)',
        borderRadius: 'var(--radius-sm)', padding: 2, gap: 1 }}>
        {options.map(o => {
          const on = o === value;
          return (
            <button key={o} onClick={() => onChange(o)} style={{
              flex: 1, padding: '4px 6px', fontSize: 11, border: 'none', cursor: 'pointer',
              borderRadius: 'calc(var(--radius-sm) - 2px)', fontFamily: 'var(--font-ui)', fontWeight: on ? 600 : 400,
              background: on ? 'var(--surface)' : 'transparent', color: on ? 'var(--ink)' : 'var(--ink-3)',
              boxShadow: on ? 'var(--shadow-sm)' : 'none', transition: 'all .14s',
            }}>{o}</button>
          );
        })}
      </div>
    </div>
  );
}

export function TweakToggle({ label, value, onChange }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
      <span style={{ fontSize: 11, color: 'var(--ink-2)', fontWeight: 500 }}>{label}</span>
      <button onClick={() => onChange(!value)} style={{
        width: 32, height: 18, borderRadius: 99, border: 'none', cursor: 'pointer', position: 'relative',
        background: value ? 'var(--accent)' : 'var(--line-strong)', transition: 'background .15s',
      }}>
        <span style={{
          position: 'absolute', top: 2, left: value ? 16 : 2, width: 14, height: 14, borderRadius: 99,
          background: '#fff', transition: 'left .15s', boxShadow: '0 1px 2px rgba(0,0,0,.3)',
        }} />
      </button>
    </div>
  );
}
