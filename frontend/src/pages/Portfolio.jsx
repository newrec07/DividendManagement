import { useEffect, useState } from 'react'
import { Plus, Trash2 } from 'lucide-react'
import { api } from '../api/client'
import SignalBadge from '../components/SignalBadge'

function fmt(n, d = 2) { return n != null ? Number(n).toFixed(d) : '—' }
function pct(n) { return n != null ? (n * 100).toFixed(2) + '%' : '—' }

const EMPTY_FORM = { ticker: '', shares: '', avg_cost: '', memo: '' }

export default function Portfolio() {
  const [summary, setSummary]   = useState(null)
  const [loading, setLoading]   = useState(true)
  const [form, setForm]         = useState(EMPTY_FORM)
  const [adding, setAdding]     = useState(false)
  const [showForm, setShowForm] = useState(false)
  const [err, setErr]           = useState('')

  function load() {
    setLoading(true)
    api.portfolio.summary()
      .then(setSummary)
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  async function handleAdd(e) {
    e.preventDefault()
    setErr('')
    if (!form.ticker || !form.shares || !form.avg_cost) {
      setErr('Ticker, 수량, 평균단가는 필수입니다.')
      return
    }
    setAdding(true)
    try {
      await api.portfolio.add({
        ticker:   form.ticker.toUpperCase(),
        shares:   parseFloat(form.shares),
        avg_cost: parseFloat(form.avg_cost),
        memo:     form.memo || null,
      })
      setForm(EMPTY_FORM)
      setShowForm(false)
      load()
    } catch (e) {
      setErr(e.message)
    } finally {
      setAdding(false)
    }
  }

  async function handleRemove(ticker) {
    if (!confirm(`${ticker}를 포트폴리오에서 제거할까요?`)) return
    await api.portfolio.remove(ticker)
    load()
  }

  if (loading) return <p className="text-slate-400 p-8">로딩 중…</p>

  const holdings = summary?.holdings || []

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">포트폴리오</h1>
          <p className="text-slate-400 text-sm mt-1">보유 종목 수익 및 배당 현황</p>
        </div>
        <button
          onClick={() => setShowForm(s => !s)}
          className="flex items-center gap-2 bg-blue-600 hover:bg-blue-500 text-white text-sm px-3 py-2 rounded transition-colors"
        >
          <Plus size={16} /> 종목 추가
        </button>
      </div>

      {/* Add form */}
      {showForm && (
        <form onSubmit={handleAdd} className="bg-slate-800 rounded-lg border border-slate-700 p-5 mb-6">
          <h3 className="text-slate-200 font-semibold mb-4">종목 추가 / 수정</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-3">
            {[
              { key: 'ticker',   label: 'Ticker', placeholder: 'ADP' },
              { key: 'shares',   label: '수량',    placeholder: '10' },
              { key: 'avg_cost', label: '평균단가', placeholder: '200.00' },
              { key: 'memo',     label: '메모',    placeholder: '선택사항' },
            ].map(({ key, label, placeholder }) => (
              <div key={key}>
                <label className="block text-slate-400 text-xs mb-1">{label}</label>
                <input
                  type={key === 'shares' || key === 'avg_cost' ? 'number' : 'text'}
                  step={key === 'avg_cost' ? '0.01' : '0.001'}
                  value={form[key]}
                  onChange={e => setForm(f => ({ ...f, [key]: e.target.value }))}
                  placeholder={placeholder}
                  className="w-full bg-slate-700 border border-slate-600 rounded px-3 py-1.5 text-slate-100 text-sm"
                />
              </div>
            ))}
          </div>
          {err && <p className="text-red-400 text-sm mb-3">{err}</p>}
          <div className="flex gap-2">
            <button
              type="submit"
              disabled={adding}
              className="bg-blue-600 hover:bg-blue-500 text-white text-sm px-4 py-1.5 rounded transition-colors disabled:opacity-50"
            >
              {adding ? '저장 중…' : '저장'}
            </button>
            <button
              type="button"
              onClick={() => { setShowForm(false); setErr('') }}
              className="bg-slate-700 hover:bg-slate-600 text-slate-300 text-sm px-4 py-1.5 rounded transition-colors"
            >
              취소
            </button>
          </div>
        </form>
      )}

      {/* Summary totals */}
      {summary && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-6">
          {[
            { label: '총 평가금액',   value: `$${fmt(summary.total_value)}` },
            { label: '총 투자금액',   value: `$${fmt(summary.total_cost)}` },
            { label: '평가손익',      value: `$${fmt(summary.total_gain_loss)}`,
              hl: summary.total_gain_loss >= 0 },
            { label: '연간 배당금',   value: `$${fmt(summary.total_annual_div)}`, hl: true },
            { label: '포트폴리오 YOC', value: pct(summary.portfolio_yield), hl: true },
          ].map(({ label, value, hl }) => (
            <div key={label} className="bg-slate-800 rounded-lg p-4 border border-slate-700">
              <p className="text-slate-400 text-xs mb-1">{label}</p>
              <p className={`text-xl font-semibold ${hl ? 'text-emerald-400' : 'text-slate-100'}`}>{value}</p>
            </div>
          ))}
        </div>
      )}

      {/* Holdings table */}
      {holdings.length === 0 ? (
        <div className="text-center py-16 text-slate-500">
          <p className="mb-2">보유 종목이 없습니다.</p>
          <p className="text-sm">위 &quot;종목 추가&quot; 버튼으로 추가하세요.</p>
        </div>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-slate-700">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-700 bg-slate-800/60">
                {['Ticker','수량','평균단가','현재가','평가금액','손익','손익률','연배당','YOC','Y10 YOC','신호',''].map(h => (
                  <th key={h} className="px-4 py-3 text-left text-slate-400 font-medium whitespace-nowrap">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {holdings.map((h, i) => (
                <tr key={h.ticker} className={`border-b border-slate-800 ${i % 2 === 0 ? 'bg-slate-900/40' : ''}`}>
                  <td className="px-4 py-3 font-bold text-slate-100">{h.ticker}</td>
                  <td className="px-4 py-3 text-slate-300">{h.shares}</td>
                  <td className="px-4 py-3 text-slate-300">${fmt(h.avg_cost)}</td>
                  <td className="px-4 py-3 text-slate-300">${fmt(h.current_price)}</td>
                  <td className="px-4 py-3 text-slate-200 font-medium">${fmt(h.market_value)}</td>
                  <td className={`px-4 py-3 font-medium ${h.gain_loss >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                    ${fmt(h.gain_loss)}
                  </td>
                  <td className={`px-4 py-3 ${h.gain_loss_pct >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                    {pct(h.gain_loss_pct)}
                  </td>
                  <td className="px-4 py-3 text-slate-300">${fmt(h.annual_div)}</td>
                  <td className="px-4 py-3 text-emerald-400">{pct(h.yoc)}</td>
                  <td className="px-4 py-3 text-blue-400">{h.yoc_y10 != null ? pct(h.yoc_y10) : '—'}</td>
                  <td className="px-4 py-3"><SignalBadge signal={h.signal_202} /></td>
                  <td className="px-4 py-3">
                    <button
                      onClick={() => handleRemove(h.ticker)}
                      className="text-slate-600 hover:text-red-400 transition-colors"
                    >
                      <Trash2 size={14} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
