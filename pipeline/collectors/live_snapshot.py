import os
import json
import yfinance as yf
from datetime import datetime
from pipeline.config import STATIC_DIR, LIVE_DIR
from pipeline.collectors.price_history import fetch_price_history


def save_live_snapshot(ticker: str) -> dict:
    os.makedirs(os.path.join(LIVE_DIR, ticker), exist_ok=True)

    # 최신 주봉 기술지표 (yfinance 기반 price_history)
    ph = fetch_price_history(ticker)
    latest = ph['data'][-1]

    # yfinance quote: 현재가 / 52W high/low 보완
    tk = yf.Ticker(ticker)
    info = tk.fast_info
    current_price = float(getattr(info, 'last_price', None) or latest['close'])
    high_52w = float(getattr(info, 'year_high', None) or latest.get('high_52w') or 0)
    low_52w = float(getattr(info, 'year_low', None) or 0)

    # 배당수익률: dividends.json 최근 4분기 합산
    div_path = os.path.join(STATIC_DIR, ticker, 'dividends.json')
    annual_dps = 0.0
    if os.path.exists(div_path):
        with open(div_path) as f:
            div_data = json.load(f)
        regular = sorted(
            [d for d in div_data['data'] if not d['is_special'] and d['dps'] > 0],
            key=lambda x: x['ex_date'], reverse=True,
        )
        annual_dps = sum(d['dps'] for d in regular[:4])

    current_yield = round(annual_dps / current_price, 4) if current_price > 0 else None

    # PE: valuation_bands.json에서
    vb_path = os.path.join(STATIC_DIR, ticker, 'valuation_bands.json')
    current_pe = None
    if os.path.exists(vb_path):
        with open(vb_path) as f:
            current_pe = json.load(f).get('current_pe')

    snapshot = {
        'ticker': ticker,
        'snapshot_date': datetime.today().strftime('%Y-%m-%d'),
        'current_price': round(current_price, 2),
        'current_yield': current_yield,
        'annual_dps': round(annual_dps, 4),
        'current_pe': current_pe,
        'high_52w': round(high_52w, 2),
        'low_52w': round(low_52w, 2),
        'sma_13w': latest.get('sma_13w'),
        'sma_40w': latest.get('sma_40w'),
        'rsi_14w': latest.get('rsi_14w'),
        'bb_upper': latest.get('bb_upper'),
        'bb_mid': latest.get('bb_mid'),
        'bb_lower': latest.get('bb_lower'),
    }

    path = os.path.join(LIVE_DIR, ticker, 'snapshot.json')
    with open(path, 'w') as f:
        json.dump(snapshot, f, indent=2)

    yield_str = f"{current_yield*100:.2f}%" if current_yield else "N/A"
    print(f"[{ticker}] snapshot.json 저장 완료 | 가격: ${current_price} | 배당수익률: {yield_str}")
    return snapshot
