export default function StatCard({ label, value, sub, highlight }) {
  return (
    <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
      <p className="text-slate-400 text-xs mb-1">{label}</p>
      <p className={`text-xl font-semibold ${highlight ? 'text-emerald-400' : 'text-slate-100'}`}>
        {value ?? '—'}
      </p>
      {sub && <p className="text-slate-500 text-xs mt-1">{sub}</p>}
    </div>
  )
}
