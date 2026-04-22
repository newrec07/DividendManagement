import { useEffect, useState } from 'react'
import { RefreshCw } from 'lucide-react'
import { api } from '../api/client'
import SignalBadge from '../components/SignalBadge'

const COLS = [
  { key: 'ticker',      label: 'Ticker' },
  { key: 'score_201',   label: '매수시점 201' },
  { key: 'signal_201',  label: '' },
  { key: 'score_202',   label: '배당성장 202' },
  { key: 'signal_202',  label: '' },
  { key: 'score_203',   label: '지속성 203' },
  { key: 'signal_203',  label: '' },
  { key: 'c2_blocked',  label: 'C2' },
  { key: 'red_flag_count', label: '🚩' },
  { key: 'scored_at',   label: '업데이트' },
]

function ScoreCell({ val }) {
  if (val == null) return <span className="text-slate-500">—</span>
  const color = val >= 80 ? 'text-emerald-400' : val >= 60 ? 'text-amber-400' : 'text-red-400'
  return <span className={`font-mono font-semibold ${color}`}>{val.toFixed(1)}</span>
}

export default function Dashboard({ onSelectTicker }) {
  const [rows, setRows]       = useState([])
  const [loading, setLoading] = useState(true)
  const [sort, setSort]       = useState({ key: 'score_202', dir: 'desc' })

  useEffect(() => {
    api.scores.list()
      .then(d => setRows(d.scores))
      .finally(() => setLoading(false))
  }, [])

  const sorted = [...rows].sort((a, b) => {
    const av = a[sort.key] ?? -1
    const bv = b[sort.key] ?? -1
    return sort.dir === 'desc' ? bv - av : av - bv
  })

  function toggle(key) {
    setSort(s => s.key === key
      ? { key, dir: s.dir === 'desc' ? 'asc' : 'desc' }
      : { key, dir: 'desc' }
    )
  }

  if (loading) return <p className="text-slate-400 p-8">로딩 중…</p>

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">대시보드</h1>
          <p className="text-slate-400 text-sm mt-1">10개 배당주 스코어링 현황</p>
        </div>
      </div>

      <div className="overflow-x-auto rounded-lg border border-slate-700">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-700 bg-slate-800/60">
              {COLS.map(c => (
                <th
                  key={c.key}
                  onClick={() => ['score_201','score_202','score_203','red_flag_count'].includes(c.key) && toggle(c.key)}
                  className={`px-4 py-3 text-left text-slate-400 font-medium whitespace-nowrap
                    ${['score_201','score_202','score_203','red_flag_count'].includes(c.key) ? 'cursor-pointer hover:text-slate-200' : ''}
                    ${sort.key === c.key ? 'text-slate-200' : ''}`}
                >
                  {c.label || ''}
                  {sort.key === c.key && (sort.dir === 'desc' ? ' ↓' : ' ↑')}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sorted.map((row, i) => (
              <tr
                key={row.ticker}
                onClick={() => onSelectTicker(row.ticker)}
                className={`border-b border-slate-800 cursor-pointer transition-colors
                  hover:bg-slate-800/80
                  ${i % 2 === 0 ? 'bg-slate-900/40' : ''}`}
              >
                <td className="px-4 py-3 font-bold text-slate-100">{row.ticker}</td>
                <td className="px-4 py-3"><ScoreCell val={row.score_201} /></td>
                <td className="px-4 py-3"><SignalBadge signal={row.signal_201} /></td>
                <td className="px-4 py-3"><ScoreCell val={row.score_202} /></td>
                <td className="px-4 py-3"><SignalBadge signal={row.signal_202} /></td>
                <td className="px-4 py-3"><ScoreCell val={row.score_203} /></td>
                <td className="px-4 py-3"><SignalBadge signal={row.signal_203} /></td>
                <td className="px-4 py-3">
                  {row.c2_blocked
                    ? <span className="text-slate-400 text-xs">BLOCKED</span>
                    : <span className="text-emerald-500 text-xs">OK</span>}
                </td>
                <td className="px-4 py-3">
                  {row.red_flag_count > 0
                    ? <span className="text-red-400 font-semibold">{row.red_flag_count}</span>
                    : <span className="text-slate-500">0</span>}
                </td>
                <td className="px-4 py-3 text-slate-500 text-xs">{row.scored_at}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
