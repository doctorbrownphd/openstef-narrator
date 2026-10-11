import React from 'react';

export function FactText({ text, highlight = true, style }) {
  if (!text) return null;
  const parts = text.split(/(«[^»]*»)/g);
  return (
    <span style={style}>
      {parts.map((seg, i) => {
        if (seg.startsWith('«') && seg.endsWith('»')) {
          const v = seg.slice(1, -1);
          return highlight
            ? <span key={i} className="mono" style={{background:'var(--fact-bg)', color:'var(--fact-ink)', fontWeight:600,
                padding:'0 4px', borderRadius:4, fontSize:'0.92em', whiteSpace:'nowrap'}}>{v}</span>
            : <strong key={i} style={{color:'var(--ink)', fontWeight:600}}>{v}</strong>;
        }
        return <React.Fragment key={i}>{seg}</React.Fragment>;
      })}
    </span>
  );
}
