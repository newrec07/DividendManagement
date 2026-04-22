import os
import json
import yfinance as yf
from datetime import datetime
from pipeline.config import STATIC_DIR


def is_special_dividend(dps: float, prev_dps: float, trailing_avg: float) -> bool:
    if dps <= 0:
        return False
    if trailing_avg > 0 and dps > trailing_avg * 3.0:
        return True
    if prev_dps > 0 and dps > prev_dps * 3.0:
        return True
    return False


def fetch_dividends(ticker: str) -> dict:
    tk = yf.Ticker(ticker)
    divs = tk.dividends

    if divs.empty:
        raise ValueError(f"{ticker}: 배당 데이터 없음")

    # yfinance returns a Series: index=ex_date, value=dps
    raw_sorted = sorted(
        [{'ex_date': idx.tz_localize(None).strftime('%Y-%m-%d'), 'dps': float(val)}
         for idx, val in divs.items()],
        key=lambda x: x['ex_date'],
    )

    records = []
    for i, r in enumerate(raw_sorted):
        dps = r['dps']
        prev_dps = raw_sorted[i - 1]['dps'] if i > 0 else 0.0
        trailing = raw_sorted[max(0, i - 4):i]
        trailing_avg = sum(x['dps'] for x in trailing) / len(trailing) if trailing else 0.0
        special = is_special_dividend(dps, prev_dps, trailing_avg)

        records.append({
            'ex_date': r['ex_date'],
            'pay_date': '',
            'record_date': '',
            'declaration_date': '',
            'dps': dps,
            'is_special': special,
            'label': '',
        })

    return {
        'ticker': ticker,
        'updated_at': datetime.today().strftime('%Y-%m-%d'),
        'data': records,
    }


def save_dividends(ticker: str) -> dict:
    ticker_dir = os.path.join(STATIC_DIR, ticker)
    os.makedirs(ticker_dir, exist_ok=True)

    result = fetch_dividends(ticker)

    path = os.path.join(ticker_dir, 'dividends.json')
    with open(path, 'w') as f:
        json.dump(result, f, indent=2)

    specials = sum(1 for r in result['data'] if r['is_special'])
    print(f"[{ticker}] dividends.json 저장 완료 ({len(result['data'])}건 / 특별배당 {specials}건)")
    return result
