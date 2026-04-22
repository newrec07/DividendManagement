"""
Weekly refresh: every Friday after market close (Railway Cron: 0 17 * * 5)
Updates live data + re-scores all tickers.
"""
import os
import sys
import json
import logging
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline.config import STATIC_DIR, LOGS_DIR
from pipeline.collectors.live_snapshot import save_live_snapshot
from pipeline.collectors.consensus import save_consensus
from pipeline.collectors.market import save_market
from pipeline.collectors.news import save_news
from pipeline.engines.score_runner import score_ticker
from pipeline.engines.simulation import save_simulation

os.makedirs(LOGS_DIR, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOGS_DIR, 'weekly_refresh.log'), encoding='utf-8'),
        logging.StreamHandler(),
    ]
)
log = logging.getLogger(__name__)


def refresh_ticker(ticker: str):
    save_live_snapshot(ticker)
    save_consensus(ticker)
    save_news(ticker)
    score_ticker(ticker, save_to_db=True)
    save_simulation(ticker)


def run():
    path = os.path.join(STATIC_DIR, 'tickers.json')
    with open(path) as f:
        tickers = [t['ticker'] for t in json.load(f)['tickers']]

    log.info(f'Weekly refresh start — {len(tickers)} tickers')
    save_market()

    completed, failed = [], []
    for ticker in tickers:
        try:
            refresh_ticker(ticker)
            completed.append(ticker)
            log.info(f'[{ticker}] refresh OK')
        except Exception as e:
            log.error(f'[{ticker}] refresh FAIL: {e}', exc_info=True)
            failed.append(ticker)

    log.info(f'Weekly refresh done — {len(completed)} OK / {len(failed)} FAIL')
    if failed:
        log.warning(f'Failed tickers: {failed}')


if __name__ == '__main__':
    run()
