import { useEffect, useState } from 'react'
import { ArrowLeft, TrendingUp } from 'lucide-react'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from 'recharts'
import { api } from '../api/client'
import SignalBadge from '../components/SignalBadge'
import StatCard from '../components/StatCard'

const SCENARIO_COLORS = {
  base:   '#60a5fa',
  bull:   '#34d399',
  bear:   '#f87171',
  freeze: '#94a3b8',
}

function fmt(n, digits = 2) {
  if (n == null) return '—'
  return Number(n).toFixed(digits)
}
function pct(n) {
  if (n == null) return '—'
  return (n * 100).toFixed(2) + '%'
}

export default function TickerDetail({ ticker, onBack }) {
  const [data, setData]       = useState(null)
  const [simInput, setSimInput] = useState('')
  const [simResult, setSimResult] = useState(null)
  const [loading, setLoading] = useState(true)
  const [simLoading, setSimLoading] = useState(false)

  useEffect(() => {
    setLoading(true)
    setSimResult(null)
    Promise.all([
      api.tickers.get(ticker),
      api.scores.get(ticker),
      api.simulation.get(ticker).catch(() => null),
      api.news.get(ticker).catch(() => null),
    ]).then(([info, scores, sim, news]) => {
      setData({ info, scores, sim, news })
      if (sim?.buy_price) setSimInput(String(sim.buy_price))
    }).finally(() => setLoading(false))
  }, [ticker])

  async function runSim() {
    setSimLoading(true)
    try {
      const price = parseFloat(simInput) || null
      const result = await api.simulation.run(ticker, price)
      setSimResult(result)
    } finally {
      setSimLoading(false)
    }
  }

  if (loading) return <p className="text-slate-400 p-8">로딩 중…</p>
  if (!data) return null

  const { info, scores, sim: baseSim, news } = data
  const sim = simResult || baseSim
  const snap = info.snapshot || {}

  // YOC chart data
  const yocData = sim
    ? Array.from({ length: 10 }, (_, i) => ({
        year: `Y${i + 1}`,
        ...Object.fromEntries(
          Object.entries(sim.yoc_by_year || {}).map(([sc, arr]) => [
            sc, arr[i]?.yoc != null ? +(arr[i].yoc * 100).toFixed(2) : null
          ])
        ),
      }))
    : []

  return (
    <div>
      <button
        onClick={onBack}
        className="flex items-center gap-2 text-slate-400 hover:text-slate-200 mb-6 text-sm transition-colors"
      >
        <ArrowLeft size={16} /> 대시보드로 돌아가기
      </button>

      {/* Header */}
      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="text-3xl font-bold text-slate-100">{ticker}</h1>
          <p className="text-slate-400 mt-1">{info.name} · {info.sector}</p>
        </div>
        <div className="flex flex-col items-end gap-1">
          <span className="text-2xl font-semibold text-slate-100">${fmt(snap.current_price)}</span>
          <span className="text-slate-400 text-sm">배당수익률 {pct(snap.current_yield)}</span>
        </div>
      </div>

      {/* Snapshot stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3 mb-6">
        <StatCard label="연간 DPS"     value={`$${fmt(snap.annual_dps)}`} />
        <StatCard label="52주 고/저"   value={`$${fmt(snap.high_52w)} / $${fmt(snap.low_52w)}`} />
        <StatCard label="RSI (14W)"    value={fmt(snap.rsi_14w, 1)} />
        <StatCard label="SMA 13W"      value={`$${fmt(snap.sma_13w)}`} />
        <StatCard label="SMA 40W"      value={`$${fmt(snap.sma_40w)}`} />
        <StatCard label="BB 하단"      value={`$${fmt(snap.bb_lower)}`} highlight />
      </div>

      {/* Scores */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        {[
          { num: '201', label: '매수시점', score: scores.score_201, signal: scores.signal_201 },
          { num: '202', label: '배당성장', score: scores.score_202, signal: scores.signal_202 },
          { num: '203', label: '지속가능성', score: scores.score_203, signal: scores.signal_203 },
        ].map(({ num, label, score, signal }) => (
          <div key={num} className="bg-slate-800 rounded-lg p-4 border border-slate-700">
            <div className="flex justify-between items-center mb-2">
              <span className="text-slate-400 text-sm">{num} {label}</span>
              <SignalBadge signal={signal} />
            </div>
            <div className="text-3xl font-bold text-slate-100">{fmt(score, 1)}</div>
            <div className="mt-2 bg-slate-700 rounded-full h-1.5">
              <div
                className="h-1.5 rounded-full bg-blue-400"
                style={{ width: `${Math.min(score || 0, 100)}%` }}
              />
            </div>
          </div>
        ))}
      </div>

      {/* Red flags */}
      {scores.red_flags?.length > 0 && (
        <div className="mb-6 p-4 bg-red-900/20 border border-red-800/40 rounded-lg">
          <p className="text-red-400 font-semibold text-sm mb-2">🚩 Red Flags ({scores.red_flag_count})</p>
          <div className="flex flex-wrap gap-2">
            {scores.red_flags.map(f => (
              <span key={f} className="bg-red-500/20 text-red-300 text-xs px-2 py-1 rounded border border-red-500/30">
                {f}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Simulation */}
      <div className="bg-slate-800 rounded-lg border border-slate-700 p-5 mb-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <TrendingUp size={18} className="text-blue-400" />
            <h2 className="text-lg font-semibold text-slate-100">10년 배당 시뮬레이션</h2>
            {sim?.freeze && (
              <span className="text-xs bg-slate-600 text-slate-300 px-2 py-0.5 rounded">FREEZE</span>
            )}
          </div>
          <div className="flex items-center gap-2">
            <span className="text-slate-400 text-sm">매수가 $</span>
            <input
              type="number"
              value={simInput}
              onChange={e => setSimInput(e.target.value)}
              className="w-24 bg-slate-700 border border-slate-600 rounded px-2 py-1 text-slate-100 text-sm"
              placeholder="현재가"
            />
            <button
              onClick={runSim}
              disabled={simLoading}
              className="bg-blue-600 hover:bg-blue-500 text-white text-sm px-3 py-1 rounded transition-colors disabled:opacity-50"
            >
              {simLoading ? '계산 중…' : '계산'}
            </button>
          </div>
        </div>

        {sim ? (
          <>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
              <StatCard label="매수가"       value={`$${fmt(sim.buy_price)}`} />
              <StatCard label="현재 배당수익률" value={pct(sim.current_yield)} />
              <StatCard label="가중 DGR"    value={pct(sim.weighted_dgr)} />
              <StatCard label="목표매수가 (5% YOC)" value={`$${fmt(sim.target_price_5pct)}`} highlight />
            </div>

            {/* YOC chart */}
            <ResponsiveContainer width="100%" height={240}>
              <LineChart data={yocData} margin={{ top: 4, right: 16, bottom: 4, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis dataKey="year" tick={{ fill: '#94a3b8', fontSize: 12 }} />
                <YAxis tickFormatter={v => v + '%'} tick={{ fill: '#94a3b8', fontSize: 12 }} />
                <Tooltip
                  contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 6 }}
                  formatter={(v, name) => [`${v}%`, name]}
                />
                <Legend wrapperStyle={{ fontSize: 12, color: '#94a3b8' }} />
                {Object.entries(SCENARIO_COLORS).map(([sc, color]) => (
                  <Line
                    key={sc}
                    type="monotone"
                    dataKey={sc}
                    stroke={color}
                    dot={false}
                    strokeWidth={sc === (sim.active_scenario || 'base') ? 2.5 : 1.5}
                    strokeDasharray={sc === 'freeze' ? '4 4' : undefined}
                  />
                ))}
              </LineChart>
            </ResponsiveContainer>

            {/* YOC Y10 summary */}
            <div className="mt-4 grid grid-cols-4 gap-2">
              {Object.entries(sim.yoc_by_year || {}).map(([sc, arr]) => {
                const y10 = arr[9]
                return (
                  <div key={sc} className="text-center">
                    <p className="text-slate-500 text-xs mb-1">{sc}</p>
                    <p className="font-semibold" style={{ color: SCENARIO_COLORS[sc] }}>
                      {y10?.yoc != null ? pct(y10.yoc) : '—'}
                    </p>
                    <p className="text-slate-500 text-xs">${fmt(y10?.annual_dps)}/주</p>
                  </div>
                )
              })}
            </div>
          </>
        ) : (
          <p className="text-slate-500 text-sm">시뮬레이션 데이터 없음. 위 계산 버튼으로 실행하세요.</p>
        )}
      </div>

      {/* News */}
      {news && (
        <div className="bg-slate-800 rounded-lg border border-slate-700 p-5">
          <div className="flex items-center gap-3 mb-4">
            <h2 className="text-lg font-semibold text-slate-100">최근 뉴스</h2>
            <span className={`text-xs px-2 py-0.5 rounded border
              ${news.tone === 'POSITIVE' ? 'text-emerald-400 border-emerald-500/40 bg-emerald-500/10'
              : news.tone === 'NEGATIVE' ? 'text-red-400 border-red-500/40 bg-red-500/10'
              : 'text-slate-400 border-slate-600 bg-slate-700'}`}>
              {news.tone}
            </span>
            <span className="text-slate-500 text-xs">
              ↑{news.positive_count} ↓{news.negative_count}
              {news.redflag_detected && ' 🚩'}
            </span>
          </div>
          <div className="space-y-3 max-h-80 overflow-y-auto">
            {(news.articles || []).slice(0, 10).map((a, i) => (
              <a
                key={i}
                href={a.url}
                target="_blank"
                rel="noopener noreferrer"
                className="block p-3 bg-slate-900/60 rounded hover:bg-slate-700/60 transition-colors"
              >
                <p className="text-slate-200 text-sm font-medium line-clamp-2">{a.title}</p>
                <div className="flex items-center gap-3 mt-1.5">
                  <span className="text-slate-500 text-xs">{a.source}</span>
                  <span className={`text-xs
                    ${a.overall_sentiment_label?.includes('Bullish') ? 'text-emerald-400'
                    : a.overall_sentiment_label?.includes('Bearish') ? 'text-red-400'
                    : 'text-slate-500'}`}>
                    {a.overall_sentiment_label}
                  </span>
                </div>
              </a>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
