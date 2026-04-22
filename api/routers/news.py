import os
import json
from fastapi import APIRouter, HTTPException, Query
from pipeline.config import STATIC_DIR, LIVE_DIR

router = APIRouter()


def _load_tickers() -> list[str]:
    path = os.path.join(STATIC_DIR, 'tickers.json')
    with open(path) as f:
        return [t['ticker'] for t in json.load(f)['tickers']]


def _load_news(ticker: str) -> dict | None:
    path = os.path.join(LIVE_DIR, ticker, 'news.json')
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return None


@router.get('/')
def list_news(limit: int = Query(default=5, ge=1, le=20, description='articles per ticker')):
    tickers = _load_tickers()
    result = []
    for ticker in tickers:
        n = _load_news(ticker)
        if n:
            result.append({
                'ticker':          ticker,
                'updated_at':      n.get('updated_at'),
                'tone':            n.get('tone'),
                'positive_count':  n.get('positive_count'),
                'negative_count':  n.get('negative_count'),
                'redflag_detected': n.get('redflag_detected'),
                'top_articles':    n.get('articles', [])[:limit],
            })
        else:
            result.append({'ticker': ticker, 'updated_at': None, 'tone': None})
    return {'news': result}


@router.get('/{ticker}')
def get_news(ticker: str):
    ticker = ticker.upper()
    tickers = _load_tickers()
    if ticker not in tickers:
        raise HTTPException(status_code=404, detail=f'{ticker} not found')

    n = _load_news(ticker)
    if not n:
        raise HTTPException(status_code=404, detail=f'{ticker} news not yet collected')

    return n
