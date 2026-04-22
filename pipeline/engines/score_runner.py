"""
Score runner: compute all three scores for each ticker and save results.
Saves to:
  - data/live/{ticker}/scores.json  (local cache)
  - Supabase score_cache_global table (upsert)
"""
import os
import sys
import json
import logging
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from pipeline.config import LIVE_DIR, STATIC_DIR
from pipeline.engines.score_201 import compute_201
from pipeline.engines.score_202 import compute_202
from pipeline.engines.score_203 import compute_203

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger(__name__)


def _save_local(ticker: str, result: dict):
    path = os.path.join(LIVE_DIR, ticker, 'scores.json')
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        json.dump(result, f, indent=2)


def _upsert_supabase(ticker: str, result: dict):
    try:
        from pipeline.config import SUPABASE_URL, SUPABASE_KEY
        import requests
        payload = {
            'ticker':       ticker,
            'scored_at':    result['scored_at'],
            'score_201':    result['score_201'],
            'score_202':    result['score_202'],
            'score_203':    result['score_203'],
            'signal_201':   result['signal_201'],
            'signal_202':   result['signal_202'],
            'signal_203':   result['signal_203'],
            'c2_blocked':   result['c2_blocked'],
            'red_flag_count': result['red_flag_count'],
            'details_json': json.dumps(result['details']),
        }
        headers = {
            'apikey':        SUPABASE_KEY,
            'Authorization': f'Bearer {SUPABASE_KEY}',
            'Content-Type':  'application/json',
            'Prefer':        'resolution=merge-duplicates',
        }
        url = f'{SUPABASE_URL}/rest/v1/score_cache_global'
        res = requests.post(url, json=payload, headers=headers, timeout=10)
        if res.status_code not in (200, 201):
            log.warning(f'[{ticker}] Supabase upsert failed: {res.status_code} {res.text[:200]}')
        else:
            log.info(f'[{ticker}] Supabase upsert OK')
    except Exception as e:
        log.warning(f'[{ticker}] Supabase upsert error: {e}')


def score_ticker(ticker: str, save_to_db: bool = True) -> dict:
    log.info(f'[{ticker}] scoring...')

    r201 = compute_201(ticker)
    r202 = compute_202(ticker)
    r203 = compute_203(ticker)

    result = {
        'ticker':       ticker,
        'scored_at':    datetime.today().strftime('%Y-%m-%d'),
        'score_201':    r201['score'],
        'score_202':    r202['score'],
        'score_203':    r203['score'],
        'signal_201':   r201['signal'],
        'signal_202':   r202['signal'],
        'signal_203':   r203['signal'],
        'c2_blocked':   r201['c2_blocked'],
        'red_flag_count': r203['red_flag_count'],
        'red_flags':    r203['red_flags'],
        'details': {
            '201': r201['factors'],
            '202': r202['factors'],
            '203': r203['factors'],
        },
    }

    _save_local(ticker, result)
    if save_to_db:
        _upsert_supabase(ticker, result)

    print(
        f'[{ticker}] 201={r201["score"]:5.1f} {r201["signal"]:<12} | '
        f'202={r202["score"]:5.1f} {r202["signal"]:<14} | '
        f'203={r203["score"]:5.1f} {r203["signal"]}'
        + (f' | RED_FLAGS={r203["red_flag_count"]}' if r203['red_flag_count'] else '')
    )
    return result


def run_all(save_to_db: bool = True):
    path = os.path.join(STATIC_DIR, 'tickers.json')
    with open(path) as f:
        tickers = [t['ticker'] for t in json.load(f)['tickers']]

    results = []
    for ticker in tickers:
        try:
            results.append(score_ticker(ticker, save_to_db=save_to_db))
        except Exception as e:
            log.error(f'[{ticker}] score failed: {e}', exc_info=True)

    print(f'\n완료: {len(results)}/{len(tickers)}개 스코어링')
    return results


if __name__ == '__main__':
    no_db = '--no-db' in sys.argv
    tickers_arg = [a for a in sys.argv[1:] if not a.startswith('--')]
    if tickers_arg:
        for t in tickers_arg:
            score_ticker(t.upper(), save_to_db=not no_db)
    else:
        run_all(save_to_db=not no_db)
