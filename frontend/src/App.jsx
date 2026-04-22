import { useState } from 'react'
import { LayoutDashboard, TrendingUp, Briefcase, Newspaper, RefreshCw } from 'lucide-react'
import { api } from './api/client'
import Dashboard from './pages/Dashboard'
import TickerDetail from './pages/TickerDetail'
import Portfolio from './pages/Portfolio'
import News from './pages/News'

const TABS = [
  { id: 'dashboard', label: '대시보드',  Icon: LayoutDashboard },
  { id: 'portfolio', label: '포트폴리오', Icon: Briefcase },
  { id: 'news',      label: '뉴스',      Icon: Newspaper },
]

export default function App() {
  const [tab, setTab]           = useState('dashboard')
  const [ticker, setTicker]     = useState(null)
  const [refreshing, setRefreshing] = useState(false)

  function selectTicker(t) {
    setTicker(t)
    setTab('detail')
  }

  function goBack() {
    setTicker(null)
    setTab('dashboard')
  }

  async function handleRefreshAll() {
    if (!confirm('전체 데이터를 갱신할까요? (백그라운드로 실행됩니다)')) return
    setRefreshing(true)
    try {
      await api.refresh.all()
      alert('갱신이 백그라운드에서 시작되었습니다.')
    } catch {
      alert('갱신 요청 실패')
    } finally {
      setRefreshing(false)
    }
  }

  return (
    <div className="min-h-screen bg-slate-900 flex flex-col">
      {/* Navbar */}
      <header className="border-b border-slate-800 bg-slate-900/80 backdrop-blur sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 flex items-center gap-1 h-14">
          <div className="flex items-center gap-2 mr-6">
            <TrendingUp size={20} className="text-emerald-400" />
            <span className="font-bold text-slate-100 text-sm">DividendManager</span>
          </div>

          {TABS.map(({ id, label, Icon }) => (
            <button
              key={id}
              onClick={() => { setTab(id); setTicker(null) }}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded text-sm transition-colors
                ${tab === id || (id === 'dashboard' && tab === 'detail')
                  ? 'bg-slate-800 text-slate-100'
                  : 'text-slate-400 hover:text-slate-200'}`}
            >
              <Icon size={15} />
              {label}
            </button>
          ))}

          <div className="ml-auto">
            <button
              onClick={handleRefreshAll}
              disabled={refreshing}
              className="flex items-center gap-1.5 text-slate-500 hover:text-slate-300 text-sm transition-colors disabled:opacity-50"
            >
              <RefreshCw size={14} className={refreshing ? 'animate-spin' : ''} />
              갱신
            </button>
          </div>
        </div>
      </header>

      {/* Main */}
      <main className="max-w-7xl mx-auto px-4 py-8 w-full flex-1">
        {tab === 'dashboard' && <Dashboard onSelectTicker={selectTicker} />}
        {tab === 'detail' && ticker && <TickerDetail ticker={ticker} onBack={goBack} />}
        {tab === 'portfolio' && <Portfolio />}
        {tab === 'news' && <News />}
      </main>
    </div>
  )
}
