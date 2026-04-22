import os
import json
import logging
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pipeline.config import STATIC_DIR
from pipeline.weekly_refresh import refresh_ticker, run

router = APIRouter()
log = logging.getLogger(__name__)


def _load_tickers() -> list[str]:
    path = os.path.join(STATIC_DIR, 'tickers.json')
    with open(path) as f:
        return [t['ticker'] for t in json.load(f)['tickers']]


def _do_refresh_all():
    try:
        run()
    except Exception as e:
        log.error(f'refresh_all failed: {e}', exc_info=True)


def _do_refresh_one(ticker: str):
    try:
        refresh_ticker(ticker)
    except Exception as e:
        log.error(f'refresh {ticker} failed: {e}', exc_info=True)


@router.post('/')
def refresh_all(background_tasks: BackgroundTasks):
    background_tasks.add_task(_do_refresh_all)
    return {'ok': True, 'message': 'Full refresh started in background'}


@router.post('/{ticker}')
def refresh_one(ticker: str, background_tasks: BackgroundTasks):
    ticker = ticker.upper()
    tickers = _load_tickers()
    if ticker not in tickers:
        raise HTTPException(status_code=404, detail=f'{ticker} not found')

    background_tasks.add_task(_do_refresh_one, ticker)
    return {'ok': True, 'message': f'{ticker} refresh started in background'}
