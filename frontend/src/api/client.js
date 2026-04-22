// dev: proxied via vite → localhost:8000
// prod: same origin (FastAPI serves both API and SPA)
const BASE = (import.meta.env.VITE_API_URL ?? '') + '/api'

async function get(path) {
  const res = await fetch(BASE + path)
  if (!res.ok) throw new Error(`${res.status} ${path}`)
  return res.json()
}

async function post(path, body) {
  const res = await fetch(BASE + path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
  })
  if (!res.ok) throw new Error(`${res.status} ${path}`)
  return res.json()
}

async function del(path) {
  const res = await fetch(BASE + path, { method: 'DELETE' })
  if (!res.ok) throw new Error(`${res.status} ${path}`)
  return res.json()
}

export const api = {
  tickers:  {
    list:   ()       => get('/tickers/'),
    get:    (t)      => get(`/tickers/${t}`),
  },
  scores:   {
    list:   ()       => get('/scores/'),
    get:    (t)      => get(`/scores/${t}`),
  },
  simulation: {
    get:    (t)      => get(`/simulation/${t}`),
    run:    (t, buy_price) => post(`/simulation/${t}`, buy_price ? { buy_price } : {}),
  },
  news:     {
    list:   ()       => get('/news/'),
    get:    (t)      => get(`/news/${t}`),
  },
  portfolio: {
    get:    ()       => get('/portfolio/'),
    summary: ()      => get('/portfolio/summary'),
    add:    (body)   => post('/portfolio/', body),
    remove: (t)      => del(`/portfolio/${t}`),
  },
  refresh:  {
    all:    ()       => post('/refresh/'),
    one:    (t)      => post(`/refresh/${t}`),
  },
}
