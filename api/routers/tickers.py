import os
import json
from fastapi import APIRouter, HTTPException
from pipeline.config import STATIC_DIR, LIVE_DIR

router = APIRouter()


def _load_tickers() -> list[dict]:
    path = os.path.join(STATIC_DIR, 'tickers.json')
    with open(path) as f:
        return json.load(f)['tickers']


def _load_snapshot(ticker: str) -> dict:
    path = os.path.join(LIVE_DIR, ticker, 'snapshot.json')
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {}


@router.get('/')
def list_tickers():
    tickers = _load_tickers()
    result = []
    for t in tickers:
        snap = _load_snapshot(t['ticker'])
        result.append({
            **t,
            'current_price': snap.get('current_price'),
            'current_yield': snap.get('current_yield'),
            'annual_dps':    snap.get('annual_dps'),
            'snapshot_date': snap.get('snapshot_date'),
        })
    return {'tickers': result, 'count': len(result)}


@router.get('/{ticker}')
def get_ticker(ticker: str):
    ticker = ticker.upper()
    tickers = _load_tickers()
    info = next((t for t in tickers if t['ticker'] == ticker), None)
    if not info:
        raise HTTPException(status_code=404, detail=f'{ticker} not found')

    snap = _load_snapshot(ticker)

    vb_path = os.path.join(STATIC_DIR, ticker, 'valuation_bands.json')
    vb = {}
    if os.path.exists(vb_path):
        with open(vb_path) as f:
            vb = json.load(f)

    return {
        **info,
        'snapshot': snap,
        'valuation_bands': vb,
    }
