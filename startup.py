"""
Railway startup: bootstrap live data if missing, then launch uvicorn.
"""
import os
import sys
import json
import logging
import subprocess

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger('startup')

BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, 'data', 'static')
LIVE_DIR   = os.path.join(BASE_DIR, 'data', 'live')


def _tickers() -> list[str]:
    path = os.path.join(STATIC_DIR, 'tickers.json')
    if not os.path.exists(path):
        log.error('data/static/tickers.json not found — aborting bootstrap')
        return []
    with open(path) as f:
        return [t['ticker'] for t in json.load(f)['tickers']]


def _needs_bootstrap() -> bool:
    tickers = _tickers()
    if not tickers:
        return False
    first = tickers[0]
    return not os.path.exists(os.path.join(LIVE_DIR, first, 'scores.json'))


def bootstrap():
    log.info('Live data missing — running initial refresh...')
    try:
        from pipeline.weekly_refresh import run
        run()
        log.info('Bootstrap complete')
    except Exception as e:
        log.error(f'Bootstrap failed: {e}', exc_info=True)


def main():
    if _needs_bootstrap():
        bootstrap()
    else:
        log.info('Live data found — skipping bootstrap')

    port = os.getenv('PORT', '8000')
    log.info(f'Starting uvicorn on port {port}')
    os.execvp('uvicorn', [
        'uvicorn', 'api.main:app',
        '--host', '0.0.0.0',
        '--port', port,
        '--workers', '1',
    ])


if __name__ == '__main__':
    main()
