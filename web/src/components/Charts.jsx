import { useState, useRef, useEffect } from 'react';

const START_HOUR = 14;

function clockLabel(absHour) {
  const day = Math.floor(absHour / 24), hod = absHour % 24;
  const d = day === 0 ? 'today' : day === 1 ? 'tomorrow' : `in ${day} days`;
  return { day: d, time: `${String(hod).padStart(2, '0')}:00`, label: `${d} ${String(hod).padStart(2, '0')}:00` };
}

export function ForecastChart({ fc, height = 320 }) {
  const wrapRef = useRef(null);
  const [w, setW] = useState(760);
  const [hover, setHover] = useState(null);

  useEffect(() => {
    if (!wrapRef.current) return;
    const ro = new ResizeObserver(es => setW(es[0].contentRect.width));
    ro.observe(wrapRef.current);
    return () => ro.disconnect();
  }, []);

  const pad = { l: 46, r: 44, t: 18, b: 30 };
  const iw = Math.max(160, w - pad.l - pad.r), ih = height - pad.t - pad.b;
  const pts = fc.points, N = pts.length;
  const maxLoad = Math.max(fc.cap, ...pts.map(p => p.p90)) * 1.08;
  const x = h => pad.l + (h / (N - 1)) * iw;
  const y = v => pad.t + ih - (v / maxLoad) * ih;
  const tMin = 0, tMax = 70;
  const yT = v => pad.t + ih - ((v - tMin) / (tMax - tMin)) * ih;

  let band = `M ${x(0)} ${y(pts[0].p90)}`;
  pts.forEach(p => band += ` L ${x(p.h)} ${y(p.p90)}`);
  for (let i = N - 1; i >= 0; i--) band += ` L ${x(pts[i].h)} ${y(pts[i].p10)}`;
  band += ' Z';

  let line = '';
  pts.forEach((p, i) => line += (i ? ' L' : 'M') + ` ${x(p.h)} ${y(p.p50)}`);

  let temp = '';
  pts.forEach((p, i) => temp += (i ? ' L' : 'M') + ` ${x(p.h)} ${yT(p.temp)}`);

  const peak = fc.peak;

  function onMove(e) {
    const r = e.currentTarget.getBoundingClientRect();
    const px = (e.clientX - r.left) * (w / r.width);
    setHover(Math.max(0, Math.min(N - 1, Math.round((px - pad.l) / iw * (N - 1)))));
  }

  const hp = hover != null ? pts[hover] : null;

  return (
    <div ref={wrapRef} style={{ width: '100%', position: 'relative' }}>
      <svg viewBox={`0 0 ${w} ${height}`} width="100%" height={height} style={{ display: 'block', fontFamily: 'var(--font-mono)' }}
           onMouseMove={onMove} onMouseLeave={() => setHover(null)}>
        {[0, 0.25, 0.5, 0.75, 1].map((fr, k) => {
          const v = fr * maxLoad;
          return <g key={k}><line x1={pad.l} x2={pad.l + iw} y1={y(v)} y2={y(v)} stroke="var(--line)" />
            <text x={pad.l - 7} y={y(v) + 3} textAnchor="end" fontSize="9.5" fill="var(--ink-3)">{v.toFixed(0)}</text></g>;
        })}
        {pts.filter(p => p.hod % 6 === 0).map(p => (
          <g key={p.h}>
            {p.hod === 0 && <line x1={x(p.h)} x2={x(p.h)} y1={pad.t} y2={pad.t + ih} stroke="var(--line-strong)" strokeDasharray="2 3" opacity="0.6" />}
            <text x={x(p.h)} y={height - 9} textAnchor="middle" fontSize="9" fill="var(--ink-3)">{String(p.hod).padStart(2, '0')}</text>
          </g>
        ))}
        <line x1={pad.l} x2={pad.l + iw} y1={y(fc.cap)} y2={y(fc.cap)} stroke="var(--f-cap)" strokeWidth="1.6" strokeDasharray="5 3" />
        <text x={pad.l + iw} y={y(fc.cap) - 5} textAnchor="end" fontSize="9.5" fill="var(--f-cap)" fontWeight="600">rating {fc.cap.toFixed(1)} MW</text>
        <path d={band} fill="var(--f-band)" opacity="0.20" />
        <path d={temp} fill="none" stroke="var(--f-temp)" strokeWidth="1.4" strokeDasharray="3 3" opacity="0.85" />
        <text x={pad.l + iw + 6} y={yT(pts[N - 1].temp) + 3} fontSize="9" fill="var(--f-temp)">{pts[N - 1].temp.toFixed(0)}&deg;</text>
        <path d={line} fill="none" stroke="var(--f-load)" strokeWidth="2.2" strokeLinejoin="round" />
        <line x1={x(peak.h)} x2={x(peak.h)} y1={pad.t} y2={pad.t + ih} stroke="var(--accent)" strokeWidth="1" opacity="0.5" />
        <circle cx={x(peak.h)} cy={y(peak.p50)} r="4" fill="var(--accent)" stroke="var(--surface)" strokeWidth="1.6" />
        <text x={x(peak.h)} y={y(peak.p50) - 9} textAnchor="middle" fontSize="9.5" fontWeight="600" fill="var(--accent)">peak {Math.round(peak.pct * 100)}%</text>
        {hp && <g><line x1={x(hp.h)} x2={x(hp.h)} y1={pad.t} y2={pad.t + ih} stroke="var(--ink)" strokeWidth="1" />
          <circle cx={x(hp.h)} cy={y(hp.p50)} r="3.4" fill="var(--ink)" stroke="var(--surface)" strokeWidth="1.4" /></g>}
      </svg>
      {hp && <div className="mono" style={{ position: 'absolute', top: 6, left: Math.min(w - 160, Math.max(8, x(hp.h) + 8)),
        background: 'var(--ink)', color: 'var(--ink-inv)', padding: '6px 9px', borderRadius: 'var(--radius-sm)', fontSize: 11,
        pointerEvents: 'none', whiteSpace: 'nowrap', boxShadow: 'var(--shadow-md)' }}>
        <div style={{ opacity: .6, fontSize: 10 }}>{clockLabel(hp.abs).label}</div>
        <div style={{ fontWeight: 600 }}>{hp.p50.toFixed(2)} MW</div>
        <div style={{ opacity: .7, fontSize: 10 }}>band {hp.p10.toFixed(1)}&ndash;{hp.p90.toFixed(1)} &middot; {hp.temp.toFixed(0)}&deg;F</div>
      </div>}
    </div>
  );
}

export function CapacityGauge({ pct, height = 58 }) {
  const wrapRef = useRef(null);
  const [w, setW] = useState(320);

  useEffect(() => {
    if (!wrapRef.current) return;
    const ro = new ResizeObserver(es => setW(es[0].contentRect.width));
    ro.observe(wrapRef.current);
    return () => ro.disconnect();
  }, []);

  const max = 1.15, bx = 10, bw = w - 20, by = 22, bh = 12;
  const X = v => bx + (v / max) * bw;
  const zones = [{ a: 0, b: 0.75, c: 'var(--ok)' }, { a: 0.75, b: 0.9, c: 'var(--warn)' }, { a: 0.9, b: 1.0, c: 'var(--f-driver)' }, { a: 1.0, b: max, c: 'var(--bad)' }];
  const p = Math.max(0, Math.min(max, pct));

  return (
    <div ref={wrapRef} style={{ width: '100%' }}>
      <svg viewBox={`0 0 ${w} ${height}`} width="100%" height={height} style={{ display: 'block', fontFamily: 'var(--font-mono)' }}>
        {zones.map((z, i) => (<rect key={i} x={X(z.a)} y={by} width={X(z.b) - X(z.a)} height={bh} fill={z.c} opacity="0.32"
          rx={i === 0 ? 3 : 0} />))}
        <line x1={X(1)} x2={X(1)} y1={by - 5} y2={by + bh + 5} stroke="var(--f-cap)" strokeWidth="1.6" />
        <text x={X(1)} y={by + bh + 16} textAnchor="middle" fontSize="8.5" fill="var(--f-cap)">rating</text>
        <g transform={`translate(${X(p)},0)`}>
          <path d={`M0 ${by - 7} l-4 -6 l8 0 Z`} fill="var(--ink)" />
          <line x1="0" x2="0" y1={by - 7} y2={by + bh + 2} stroke="var(--ink)" strokeWidth="1.6" />
        </g>
        <text x={X(p)} y={by - 12} textAnchor="middle" fontSize="11" fontWeight="600" fill="var(--ink)">{Math.round(pct * 100)}%</text>
        {[0, 0.5, 1.0].map(v => <text key={v} x={X(v)} y={by - 12} textAnchor="middle" fontSize="8" fill="var(--ink-3)" opacity={v === 0 || v === 0.5 ? 1 : 0}>{Math.round(v * 100)}</text>)}
      </svg>
    </div>
  );
}
