import { useEffect, useState } from 'react'
import { ExternalLink } from 'lucide-react'
import { api } from '../api/client'

const TONE_STYLE = {
  POSITIVE: 'text-emerald-400 border-emerald-500/40 bg-emerald-500/10',
  NEGATIVE: 'text-red-400 border-red-500/40 bg-red-500/10',
  NEUTRAL:  'text-slate-400 border-slate-600 bg-slate-700/40',
  REDFLAG:  'text-red-400 border-red-500/40 bg-red-500/10',
}

export default function News() {
  const [news, setNews]       = useState([])
  const [loading, setLoading] = useState(true)
  const [active, setActive]   = useState(null)

  useEffect(() => {
    api.news.list()
      .then(d => {
        setNews(d.news)
        if (d.news.length > 0) setActive(d.news[0].ticker)
      })
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <p className="text-slate-400 p-8">로딩 중…</p>

  const current = news.find(n => n.ticker === active)

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-slate-100">뉴스</h1>
        <p className="text-slate-400 text-sm mt-1">종목별 최신 뉴스 & 센티먼트</p>
      </div>

      {/* Ticker tabs */}
      <div className="flex flex-wrap gap-2 mb-6">
        {news.map(n => (
          <button
            key={n.ticker}
            onClick={() => setActive(n.ticker)}
            className={`px-3 py-1.5 rounded text-sm font-medium transition-colors
              ${active === n.ticker
                ? 'bg-blue-600 text-white'
                : 'bg-slate-800 text-slate-400 hover:text-slate-200 border border-slate-700'}`}
          >
            {n.ticker}
            {n.tone && (
              <span className={`ml-2 text-xs
                ${n.tone === 'POSITIVE' ? 'text-emerald-400'
                : n.tone === 'NEGATIVE' ? 'text-red-400'
                : 'text-slate-500'}`}>
                {n.tone === 'POSITIVE' ? '↑' : n.tone === 'NEGATIVE' ? '↓' : '–'}
              </span>
            )}
            {n.redflag_detected && <span className="ml-1 text-xs">🚩</span>}
          </button>
        ))}
      </div>

      {/* Sentiment summary */}
      {current && (
        <>
          <div className="flex items-center gap-4 mb-5">
            <span className={`text-sm px-3 py-1 rounded border ${TONE_STYLE[current.tone] || TONE_STYLE.NEUTRAL}`}>
              {current.tone || 'NEUTRAL'}
            </span>
            <span className="text-slate-400 text-sm">
              긍정 {current.positive_count} · 부정 {current.negative_count}
              {current.redflag_detected && ' · 🚩 Red Flag 감지'}
            </span>
            {current.updated_at && (
              <span className="text-slate-600 text-xs ml-auto">{current.updated_at}</span>
            )}
          </div>

          {/* Articles */}
          <div className="space-y-3">
            {(current.top_articles || []).map((a, i) => {
              const bull = a.overall_sentiment_label?.includes('Bullish')
              const bear = a.overall_sentiment_label?.includes('Bearish')
              return (
                <a
                  key={i}
                  href={a.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex gap-4 p-4 bg-slate-800 rounded-lg border border-slate-700 hover:border-slate-600 hover:bg-slate-750 transition-colors group"
                >
                  <div className="flex-1 min-w-0">
                    <p className="text-slate-200 text-sm font-medium group-hover:text-white transition-colors line-clamp-2">
                      {a.title}
                    </p>
                    <p className="text-slate-500 text-xs mt-2 line-clamp-2">{a.summary}</p>
                    <div className="flex items-center gap-3 mt-2">
                      <span className="text-slate-600 text-xs">{a.source}</span>
                      <span className={`text-xs ${bull ? 'text-emerald-400' : bear ? 'text-red-400' : 'text-slate-500'}`}>
                        {a.overall_sentiment_label}
                      </span>
                      <span className="text-slate-600 text-xs">
                        관련도 {a.relevance_score ? (parseFloat(a.relevance_score) * 100).toFixed(0) + '%' : '—'}
                      </span>
                    </div>
                  </div>
                  <ExternalLink size={14} className="text-slate-600 group-hover:text-slate-400 flex-shrink-0 mt-1 transition-colors" />
                </a>
              )
            })}
          </div>
        </>
      )}
    </div>
  )
}
