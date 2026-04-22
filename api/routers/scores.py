import os
import json
from fastapi import APIRouter, HTTPException
from pipeline.config import STATIC_DIR, LIVE_DIR

router = APIRouter()


def _load_tickers() -> list[str]:
    path = os.path.join(STATIC_DIR, 'tickers.json')
    with open(path) as f:
        return [t['ticker'] for t in json.load(f)['tickers']]


def _load_scores(ticker: str) -> dict | None:
    path = os.path.join(LIVE_DIR, ticker, 'scores.json')
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return None


@router.get('/')
def list_scores():
    tickers = _load_tickers()
    result = []
    for ticker in tickers:
        s = _load_scores(ticker)
        if s:
            result.append({
                'ticker':        s['ticker'],
                'scored_at':     s['scored_at'],
                'score_201':     s['score_201'],
                'score_202':     s['score_202'],
                'score_203':     s['score_203'],
                'signal_201':    s['signal_201'],
                'signal_202':    s['signal_202'],
                'signal_203':    s['signal_203'],
                'c2_blocked':    s['c2_blocked'],
                'red_flag_count': s['red_flag_count'],
            })
        else:
            result.append({'ticker': ticker, 'scored_at': None})
    return {'scores': result, 'count': len(result)}


@router.get('/{ticker}')
def get_scores(ticker: str):
    ticker = ticker.upper()
    tickers = _load_tickers()
    if ticker not in tickers:
        raise HTTPException(status_code=404, detail=f'{ticker} not found')

    s = _load_scores(ticker)
    if not s:
        raise HTTPException(status_code=404, detail=f'{ticker} scores not yet computed')

    return s
