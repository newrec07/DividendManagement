const COLORS = {
  IMMEDIATE_BUY: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/40',
  STRONG:        'bg-emerald-500/20 text-emerald-400 border-emerald-500/40',
  WATCH:         'bg-amber-500/20 text-amber-400 border-amber-500/40',
  HOLD:          'bg-blue-500/20 text-blue-400 border-blue-500/40',
  CAUTION:       'bg-orange-500/20 text-orange-400 border-orange-500/40',
  DANGER:        'bg-red-500/20 text-red-400 border-red-500/40',
  C2_BLOCKED:    'bg-slate-500/20 text-slate-400 border-slate-500/40',
}

export default function SignalBadge({ signal }) {
  if (!signal) return <span className="text-slate-500 text-xs">—</span>
  const cls = COLORS[signal] ?? 'bg-slate-500/20 text-slate-400 border-slate-500/40'
  return (
    <span className={`inline-block px-2 py-0.5 rounded border text-xs font-medium ${cls}`}>
      {signal}
    </span>
  )
}
