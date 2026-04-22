import os
import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from pipeline.config import STATIC_DIR, LIVE_DIR
from pipeline.engines.simulation import compute_simulation

router = APIRouter()


def _load_tickers() -> list[str]:
    path = os.path.join(STATIC_DIR, 'tickers.json')
    with open(path) as f:
        return [t['ticker'] for t in json.load(f)['tickers']]


def _load_simulation(ticker: str) -> dict | None:
    path = os.path.join(LIVE_DIR, ticker, 'simulation.json')
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return None


class SimulationRequest(BaseModel):
    buy_price: float | None = None


@router.get('/{ticker}')
def get_simulation(ticker: str):
    ticker = ticker.upper()
    tickers = _load_tickers()
    if ticker not in tickers:
        raise HTTPException(status_code=404, detail=f'{ticker} not found')

    result = _load_simulation(ticker)
    if not result:
        raise HTTPException(status_code=404, detail=f'{ticker} simulation not yet computed. Use POST to run.')

    return result


@router.post('/{ticker}')
def run_simulation(ticker: str, body: SimulationRequest = SimulationRequest()):
    ticker = ticker.upper()
    tickers = _load_tickers()
    if ticker not in tickers:
        raise HTTPException(status_code=404, detail=f'{ticker} not found')

    try:
        result = compute_simulation(ticker, buy_price=body.buy_price)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return result
