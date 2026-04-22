import os
import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from pipeline.config import STATIC_DIR, LIVE_DIR, BASE_DIR

router = APIRouter()

PORTFOLIO_PATH = os.path.join(BASE_DIR, 'data', 'portfolio.json')


def _load_tickers_meta() -> dict[str, dict]:
    path = os.path.join(STATIC_DIR, 'tickers.json')
    with open(path) as f:
        return {t['ticker']: t for t in json.load(f)['tickers']}


def _load_portfolio() -> dict:
    if os.path.exists(PORTFOLIO_PATH):
        with open(PORTFOLIO_PATH) as f:
            return json.load(f)
    return {'holdings': []}


def _save_portfolio(data: dict):
    os.makedirs(os.path.dirname(PORTFOLIO_PATH), exist_ok=True)
    with open(PORTFOLIO_PATH, 'w') as f:
        json.dump(data, f, indent=2)


def _load_scores(ticker: str) -> dict:
    path = os.path.join(LIVE_DIR, ticker, 'scores.json')
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {}


def _load_snapshot(ticker: str) -> dict:
    path = os.path.join(LIVE_DIR, ticker, 'snapshot.json')
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {}


def _load_simulation(ticker: str) -> dict:
    path = os.path.join(LIVE_DIR, ticker, 'simulation.json')
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {}


class HoldingRequest(BaseModel):
    ticker: str
    shares: float
    avg_cost: float
    memo: str | None = None


@router.get('/')
def get_portfolio():
    return _load_portfolio()


@router.post('/')
def add_holding(body: HoldingRequest):
    ticker = body.ticker.upper()
    meta = _load_tickers_meta()
    if ticker not in meta:
        raise HTTPException(status_code=404, detail=f'{ticker} not in watchlist')

    data = _load_portfolio()
    existing = next((h for h in data['holdings'] if h['ticker'] == ticker), None)
    if existing:
        existing['shares']   = body.shares
        existing['avg_cost'] = body.avg_cost
        existing['memo']     = body.memo
    else:
        data['holdings'].append({
            'ticker':   ticker,
            'shares':   body.shares,
            'avg_cost': body.avg_cost,
            'memo':     body.memo,
        })

    _save_portfolio(data)
    return {'ok': True, 'ticker': ticker}


@router.delete('/{ticker}')
def remove_holding(ticker: str):
    ticker = ticker.upper()
    data = _load_portfolio()
    before = len(data['holdings'])
    data['holdings'] = [h for h in data['holdings'] if h['ticker'] != ticker]
    if len(data['holdings']) == before:
        raise HTTPException(status_code=404, detail=f'{ticker} not in portfolio')
    _save_portfolio(data)
    return {'ok': True, 'ticker': ticker}


@router.get('/summary')
def portfolio_summary():
    data = _load_portfolio()
    holdings = data.get('holdings', [])

    result = []
    total_value = 0.0
    total_cost  = 0.0
    total_annual_div = 0.0

    for h in holdings:
        ticker = h['ticker']
        snap   = _load_snapshot(ticker)
        scores = _load_scores(ticker)
        sim    = _load_simulation(ticker)

        current_price = snap.get('current_price') or h['avg_cost']
        shares        = h['shares']
        avg_cost      = h['avg_cost']
        annual_dps    = snap.get('annual_dps', 0) or 0

        market_value  = shares * current_price
        cost_basis    = shares * avg_cost
        gain_loss     = market_value - cost_basis
        gain_loss_pct = (gain_loss / cost_basis) if cost_basis else 0
        annual_div    = shares * annual_dps
        yoc           = (annual_dps / avg_cost) if avg_cost else 0

        # YOC Y10 from base scenario
        yoc_y10 = None
        if sim and 'yoc_by_year' in sim:
            base = sim['yoc_by_year'].get('base', [])
            if len(base) >= 10:
                yoc_y10 = base[9].get('yoc')

        total_value    += market_value
        total_cost     += cost_basis
        total_annual_div += annual_div

        result.append({
            'ticker':        ticker,
            'shares':        shares,
            'avg_cost':      avg_cost,
            'current_price': current_price,
            'market_value':  round(market_value, 2),
            'gain_loss':     round(gain_loss, 2),
            'gain_loss_pct': round(gain_loss_pct, 4),
            'annual_dps':    annual_dps,
            'annual_div':    round(annual_div, 2),
            'yoc':           round(yoc, 4),
            'yoc_y10':       yoc_y10,
            'signal_201':    scores.get('signal_201'),
            'signal_202':    scores.get('signal_202'),
            'signal_203':    scores.get('signal_203'),
            'red_flag_count': scores.get('red_flag_count'),
            'memo':          h.get('memo'),
        })

    return {
        'holdings':        result,
        'total_value':     round(total_value, 2),
        'total_cost':      round(total_cost, 2),
        'total_gain_loss': round(total_value - total_cost, 2),
        'total_annual_div': round(total_annual_div, 2),
        'portfolio_yield': round(total_annual_div / total_cost, 4) if total_cost else 0,
    }
