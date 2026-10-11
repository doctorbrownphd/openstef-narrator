import { useState } from 'react';

/* ---------- Icons (stroke, 24 viewBox) ---------- */
export function Icon({ name, size = 16, sw = 1.7, style }) {
  const p = { fill:'none', stroke:'currentColor', strokeWidth:sw, strokeLinecap:'round', strokeLinejoin:'round' };
  const paths = {
    bolt: <path {...p} d="M13 3 4 14h7l-1 7 9-11h-7z" />,
    grid: <g {...p}><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></g>,
    shield: <g {...p}><path d="M12 3l7 3v6c0 4.5-3 7.5-7 9-4-1.5-7-4.5-7-9V6z"/><path d="M9 12l2 2 4-4"/></g>,
    sun: <g {...p}><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M2 12h2M20 12h2M5 5l1.5 1.5M17.5 17.5L19 19M19 5l-1.5 1.5M6.5 17.5L5 19"/></g>,
    moon: <path {...p} d="M20 14.5A8 8 0 1 1 9.5 4a6.5 6.5 0 0 0 10.5 10.5z" />,
    copy: <g {...p}><rect x="9" y="9" width="11" height="11" rx="2"/><path d="M5 15V5a2 2 0 0 1 2-2h8"/></g>,
    download: <g {...p}><path d="M12 3v12M7 11l5 5 5-5"/><path d="M4 19h16"/></g>,
    refresh: <g {...p}><path d="M4 12a8 8 0 0 1 14-5.3L21 9"/><path d="M21 4v5h-5"/><path d="M20 12a8 8 0 0 1-14 5.3L3 15"/><path d="M3 20v-5h5"/></g>,
    play: <path {...p} d="M7 4v16l13-8z" />,
    chevron: <path {...p} d="M9 6l6 6-6 6" />,
    chevdown: <path {...p} d="M6 9l6 6 6-6" />,
    car: <g {...p}><path d="M5 16l1.5-5A2 2 0 0 1 8.4 9.5h7.2a2 2 0 0 1 1.9 1.5L19 16"/><path d="M3 16h18v3h-2v1h-2v-1H7v1H5v-1H3z"/></g>,
    solar: <g {...p}><circle cx="12" cy="12" r="3.5"/><path d="M12 3v2M12 19v2M3 12h2M19 12h2M5.6 5.6l1.4 1.4M17 17l1.4 1.4M18.4 5.6 17 7M7 17l-1.4 1.4"/></g>,
    home: <path {...p} d="M4 11l8-7 8 7M6 10v9h12v-9" />,
    flame: <path {...p} d="M12 3c1 3-2 4-2 7a2 2 0 0 0 4 0c0-1 1 0 1 2a3.5 3.5 0 0 1-7 0c0-4 4-5 4-9z" />,
    battery: <g {...p}><rect x="3" y="8" width="16" height="9" rx="2"/><path d="M21 11v3"/><path d="M9 10l-1.5 3.5h2L8 16"/></g>,
    book: <g {...p}><path d="M5 4h11a2 2 0 0 1 2 2v14H7a2 2 0 0 1-2-2z"/><path d="M5 18a2 2 0 0 1 2-2h11"/></g>,
    layers: <g {...p}><path d="M12 3l9 5-9 5-9-5z"/><path d="M3 13l9 5 9-5"/></g>,
    check: <path {...p} d="M5 12l4 4 10-10" />,
    x: <path {...p} d="M6 6l12 12M18 6L6 18" />,
    chip: <g {...p}><rect x="6" y="6" width="12" height="12" rx="2"/><path d="M9 1.5v3M15 1.5v3M9 19.5v3M15 19.5v3M1.5 9h3M1.5 15h3M19.5 9h3M19.5 15h3"/></g>,
    wave: <path {...p} d="M3 12c2 0 2-5 4-5s2 9 4 9 2-9 4-9 2 5 4 5" />,
    thermo: <g {...p}><path d="M14 14.5V5a2 2 0 0 0-4 0v9.5a3.5 3.5 0 1 0 4 0z"/></g>,
    arrow: <path {...p} d="M5 12h14M13 6l6 6-6 6" />,
    trend: <g {...p}><path d="M3 16l5-5 4 3 7-8"/><path d="M21 6v5h-5"/></g>,
    gauge: <g {...p}><path d="M4 18a8 8 0 1 1 16 0"/><path d="M12 18l4-5"/><circle cx="12" cy="18" r="1.3"/></g>,
    mail: <g {...p}><rect x="3" y="5" width="18" height="14" rx="2"/><path d="M3.5 6.5 12 13l8.5-6.5"/></g>,
    sms: <g {...p}><path d="M21 12a8 8 0 0 1-11.5 7.2L4 20l1-4.2A8 8 0 1 1 21 12z"/><path d="M8.5 11h7M8.5 14h4"/></g>,
    audit: <g {...p}><circle cx="12" cy="12" r="3"/><path d="M3 12h6M15 12h6"/></g>,
    cloud: <g {...p}><path d="M7 18a4 4 0 0 1-.5-7.97A5.5 5.5 0 0 1 17.5 11 3.5 3.5 0 0 1 17 18z"/></g>,
    server: <g {...p}><rect x="3.5" y="4" width="17" height="7" rx="1.5"/><rect x="3.5" y="13" width="17" height="7" rx="1.5"/><path d="M7 7.5h.01M7 16.5h.01"/></g>,
    alert: <g {...p}><path d="M12 3l9 16H3z"/><path d="M12 10v4M12 17v.5"/></g>,
    clock: <g {...p}><circle cx="12" cy="12" r="8.5"/><path d="M12 7v5l3.5 2"/></g>,
    calendar: <g {...p}><rect x="3.5" y="5" width="17" height="16" rx="2"/><path d="M3.5 9.5h17M8 3v4M16 3v4"/></g>,
    pin: <g {...p}><path d="M12 21s7-6.4 7-11a7 7 0 1 0-14 0c0 4.6 7 11 7 11z"/><circle cx="12" cy="10" r="2.5"/></g>,
    cpu: <g {...p}><rect x="7" y="7" width="10" height="10" rx="2"/><path d="M10 11h4v4h-4z"/><path d="M9 2v3M15 2v3M9 19v3M15 19v3M2 9h3M2 15h3M19 9h3M19 15h3"/></g>,
    send: <path {...p} d="M4 12l16-7-7 16-2.5-6.5z" />,
    sparkles: <g {...p}><path d="M12 3l1.6 4.4L18 9l-4.4 1.6L12 15l-1.6-4.4L6 9l4.4-1.6z"/><path d="M18 14l.8 2.2L21 17l-2.2.8L18 20l-.8-2.2L15 17l2.2-.8z"/></g>,
    snow: <g {...p}><path d="M12 2v20M4 7l16 10M20 7L4 17"/><path d="M12 6l-2-2M12 6l2-2M12 18l-2 2M12 18l2 2"/></g>,
    branch: <g {...p}><circle cx="6" cy="6" r="2.5"/><circle cx="6" cy="18" r="2.5"/><circle cx="18" cy="8" r="2.5"/><path d="M6 8.5v7M15.5 8.5c0 4-3.5 3.5-9.5 7"/></g>,
  };
  return <svg width={size} height={size} viewBox="0 0 24 24" style={{flexShrink:0, ...style}}>{paths[name]}</svg>;
}

/* ---------- Logo ---------- */
export function Logo({ size = 26 }) {
  return (
    <div style={{display:'flex', alignItems:'center', gap:10}}>
      <svg width={size} height={size} viewBox="0 0 32 32" style={{flexShrink:0}}>
        <rect x="1" y="1" width="30" height="30" rx="7" fill="var(--accent)" />
        <g fill="none" stroke="var(--accent-ink)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M5 20l5-6 4 3 5-8" />
          <path d="M19 9h3.5" opacity="0.6" />
          <circle cx="10" cy="14" r="1.4" fill="var(--accent-ink)" stroke="none"/>
          <circle cx="14" cy="17" r="1.4" fill="var(--accent-ink)" stroke="none"/>
          <path d="M6 25h13" opacity="0.45" />
        </g>
      </svg>
      <div style={{lineHeight:1}}>
        <div style={{fontWeight:700, fontSize:15, letterSpacing:'-0.02em'}}>OpenSTEF<span style={{color:'var(--accent)'}}> Narrator</span></div>
        <div className="mono" style={{fontSize:9.5, color:'var(--ink-3)', letterSpacing:'0.04em', marginTop:1}}>FORECAST EXPLAINABILITY LAYER</div>
      </div>
    </div>
  );
}

/* ---------- Button ---------- */
export function Btn({ children, kind = 'ghost', size = 'md', icon, onClick, active, style, title }) {
  const [hover, setHover] = useState(false);
  const sizes = { sm:{p:'5px 10px', f:12, g:6}, md:{p:'8px 14px', f:13, g:7}, lg:{p:'11px 18px', f:14, g:8} };
  const s = sizes[size];
  const base = {
    display:'inline-flex', alignItems:'center', gap:s.g, padding:s.p, fontSize:s.f,
    fontFamily:'var(--font-ui)', fontWeight:500, border:'1px solid transparent',
    borderRadius:'var(--radius-sm)', cursor:'pointer', transition:'all .14s ease',
    whiteSpace:'nowrap', lineHeight:1.2, ...style,
  };
  const kinds = {
    primary: { background: hover?'var(--accent-2)':'var(--accent)', color:'var(--accent-ink)', boxShadow:'var(--shadow-sm)' },
    secondary: { background: hover?'var(--surface-3)':'var(--surface-2)', color:'var(--ink)', borderColor:'var(--line)' },
    ghost: { background: hover||active?'var(--surface-2)':'transparent', color: active?'var(--ink)':'var(--ink-2)', borderColor: active?'var(--line)':'transparent' },
    outline: { background:hover?'var(--accent-weak)':'transparent', color:'var(--accent)', borderColor:'var(--accent)' },
  };
  return (
    <button title={title} onClick={onClick} onMouseEnter={()=>setHover(true)} onMouseLeave={()=>setHover(false)}
            style={{...base, ...kinds[kind]}}>
      {icon && <Icon name={icon} size={s.f+2} />}{children}
    </button>
  );
}

/* ---------- Badge ---------- */
export function Badge({ children, tone = 'neutral', mono = true }) {
  const tones = {
    ok:   { bg:'var(--ok-bg)', c:'var(--ok)' },
    warn: { bg:'var(--warn-bg)', c:'var(--warn)' },
    bad:  { bg:'var(--bad-bg)', c:'var(--bad)' },
    accent:{ bg:'var(--accent-weak)', c:'var(--accent)' },
    neutral:{ bg:'var(--surface-2)', c:'var(--ink-2)' },
  };
  const t = tones[tone];
  return <span className={mono?'mono':''} style={{ display:'inline-flex', alignItems:'center', gap:5,
    background:t.bg, color:t.c, fontSize:10.5, fontWeight:600, padding:'3px 8px', borderRadius:99,
    letterSpacing:'0.02em', whiteSpace:'nowrap' }}>{children}</span>;
}

/* ---------- Stat ---------- */
export function Stat({ label, value, unit, sub, color }) {
  return (
    <div style={{display:'flex', flexDirection:'column', gap:3}}>
      <div className="mono" style={{fontSize:10, letterSpacing:'0.05em', textTransform:'uppercase', color:'var(--ink-3)'}}>{label}</div>
      <div style={{display:'flex', alignItems:'baseline', gap:4}}>
        <span className="tnum" style={{fontSize:24, fontWeight:600, letterSpacing:'-0.02em', color: color||'var(--ink)', fontFamily:'var(--font-mono)'}}>{value}</span>
        {unit && <span className="mono" style={{fontSize:12, color:'var(--ink-3)'}}>{unit}</span>}
      </div>
      {sub && <div style={{fontSize:11.5, color:'var(--ink-3)'}}>{sub}</div>}
    </div>
  );
}

/* ---------- Card ---------- */
export function Card({ children, style, pad = 18 }) {
  return <div style={{ background:'var(--surface)', border:'1px solid var(--line)', borderRadius:'var(--radius)',
    boxShadow:'var(--shadow-sm)', padding:pad, ...style }}>{children}</div>;
}

/* ---------- Select ---------- */
export function Select({ value, onChange, options }) {
  return (
    <div style={{position:'relative'}}>
      <select value={value} onChange={e=>onChange(e.target.value)} style={{
        appearance:'none', width:'100%', padding:'8px 30px 8px 11px', fontSize:13, fontFamily:'var(--font-ui)',
        background:'var(--surface)', color:'var(--ink)', border:'1px solid var(--line)',
        borderRadius:'var(--radius-sm)', cursor:'pointer' }}>
        {options.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
      </select>
      <div style={{position:'absolute', right:9, top:'50%', transform:'translateY(-50%)', pointerEvents:'none', color:'var(--ink-3)'}}>
        <Icon name="chevdown" size={15} />
      </div>
    </div>
  );
}

/* ---------- CodeBlock ---------- */
export function CodeBlock({ code, lang = 'python' }) {
  const [copied, setCopied] = useState(false);
  function copy(){ navigator.clipboard?.writeText(code.replace(/<[^>]*>/g, '')).then(()=>{ setCopied(true); setTimeout(()=>setCopied(false),1400); }); }
  return (
    <div style={{position:'relative', background:'var(--surface-2)', border:'1px solid var(--line)',
         borderRadius:'var(--radius)', overflow:'hidden'}}>
      <div style={{display:'flex', alignItems:'center', justifyContent:'space-between', padding:'7px 10px 7px 13px',
           borderBottom:'1px solid var(--line)', background:'var(--surface-3)'}}>
        <span className="mono" style={{fontSize:10.5, color:'var(--ink-3)', letterSpacing:'0.04em'}}>{lang}</span>
        <Btn kind="ghost" size="sm" icon={copied?'check':'copy'} onClick={copy}>{copied?'Copied':'Copy'}</Btn>
      </div>
      <pre className="mono" style={{margin:0, padding:'13px 15px', fontSize:12.5, lineHeight:1.65,
           color:'var(--ink)', overflowX:'auto'}}><code dangerouslySetInnerHTML={{__html: code}} /></pre>
    </div>
  );
}

/* ---------- Segmented control ---------- */
export function Segmented({ options, value, onChange, size='md' }) {
  const fs = size==='sm'?11.5:12.5;
  return (
    <div style={{display:'inline-flex', background:'var(--surface-2)', border:'1px solid var(--line)',
                 borderRadius:'var(--radius-sm)', padding:2, gap:2}}>
      {options.map(o => {
        const val = typeof o==='object'?o.value:o, lab = typeof o==='object'?o.label:o, ic = typeof o==='object'?o.icon:null;
        const on = val===value;
        return (
          <button key={val} onClick={()=>onChange(val)} style={{
            display:'inline-flex', alignItems:'center', gap:5, padding:size==='sm'?'4px 9px':'5px 11px',
            fontSize:fs, fontFamily:'var(--font-ui)', fontWeight: on?600:500, cursor:'pointer',
            border:'none', borderRadius:'calc(var(--radius-sm) - 1px)',
            background: on?'var(--surface)':'transparent', color: on?'var(--ink)':'var(--ink-2)',
            boxShadow: on?'var(--shadow-sm)':'none', transition:'all .14s ease' }}>
            {ic && <Icon name={ic} size={fs+1} />}{lab}
          </button>
        );
      })}
    </div>
  );
}
