import os
import json
import requests
from datetime import datetime
from pipeline.config import FMP_KEY, LIVE_DIR

FMP_QUOTE_URL = 'https://financialmodelingprep.com/stable/quote'


def save_market() -> dict:
    os.makedirs(LIVE_DIR, exist_ok=True)

    res = requests.get(FMP_QUOTE_URL, params={'symbol': '^VIX', 'apikey': FMP_KEY}, timeout=15)
    res.raise_for_status()
    data = res.json()

    vix = float(data[0]['price']) if data else None

    market = {
        'snapshot_date': datetime.today().strftime('%Y-%m-%d'),
        'vix_current': vix,
        'vix_updated_at': datetime.today().isoformat(),
    }

    path = os.path.join(LIVE_DIR, 'market.json')
    with open(path, 'w') as f:
        json.dump(market, f, indent=2)

    print(f"[market] VIX: {vix}")
    return market
