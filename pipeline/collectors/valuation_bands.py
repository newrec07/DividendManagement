import os
import json
import pandas as pd
from datetime import datetime, timedelta
from pipeline.config import STATIC_DIR


def _load_json(ticker: str, filename: str) -> dict:
    path = os.path.join(STATIC_DIR, ticker, filename)
    if not os.path.exists(path):
        raise FileNotFoundError(f"{ticker}/{filename} 없음 — 먼저 수집 필요")
    with open(path) as f:
        return json.load(f)


def fetch_valuation_bands(ticker: str) -> dict:
    today = datetime.today()

    # 이미 저장된 price_history.json 활용 (FMP/yfinance 중립)
    ph = _load_json(ticker, 'price_history.json')
    ph_records = ph['data']
    df = pd.DataFrame(ph_records)
    df['date'] = pd.to_datetime(df['date'])
    df = df.set_index('date').sort_index()
    df['close'] = df['close'].astype(float)

    current_price = float(df['close'].iloc[-1])

    # 배당 이력에서 연간 DPS (최근 4분기 합산, 특별배당 제외)
    div_data = _load_json(ticker, 'dividends.json')
    regular_divs = sorted(
        [d for d in div_data['data'] if not d['is_special'] and d['dps'] > 0],
        key=lambda x: x['ex_date'], reverse=True,
    )
    annual_dps = sum(d['dps'] for d in regular_divs[:4])
    current_yield = annual_dps / current_price if current_price > 0 else 0

    # 재무 데이터에서 TTM EPS (최근 4분기 합산)
    fin_data = _load_json(ticker, 'financials.json')
    income_q = fin_data.get('income_quarterly', [])
    recent_income = sorted(income_q, key=lambda x: x['date'], reverse=True)[:4]
    ttm_net_income = sum(r.get('net_income') or 0 for r in recent_income)

    balance_a = fin_data.get('balance_annual', [])
    recent_balance = sorted(balance_a, key=lambda x: x['date'], reverse=True)
    shares = next((b.get('shares_outstanding') for b in recent_balance if b.get('shares_outstanding')), None)
    ttm_eps = (ttm_net_income / shares) if (shares and shares > 0) else None
    current_pe = (current_price / ttm_eps) if ttm_eps and ttm_eps > 0 else None

    # 5년 배당수익률 밴드
    cutoff_5y = today - timedelta(days=365 * 5)
    df_5y = df[df.index >= pd.Timestamp(cutoff_5y)].copy()
    if annual_dps > 0 and len(df_5y) > 10:
        df_5y['yield_implied'] = annual_dps / df_5y['close']
        yield_min_5y = round(float(df_5y['yield_implied'].quantile(0.05)), 4)
        yield_max_5y = round(float(df_5y['yield_implied'].quantile(0.95)), 4)
    else:
        yield_min_5y = None
        yield_max_5y = None

    # 5년 PE 밴드
    if ttm_eps and ttm_eps > 0 and len(df_5y) > 10:
        df_5y['pe_implied'] = df_5y['close'] / ttm_eps
        pe_min_5y = round(float(df_5y['pe_implied'].quantile(0.05)), 2)
        pe_max_5y = round(float(df_5y['pe_implied'].quantile(0.95)), 2)
    else:
        pe_min_5y = None
        pe_max_5y = None

    return {
        'ticker': ticker,
        'updated_at': today.strftime('%Y-%m-%d'),
        'current_price': round(current_price, 2),
        'current_yield': round(current_yield, 4),
        'annual_dps': round(annual_dps, 4),
        'current_pe': round(current_pe, 2) if current_pe else None,
        'ttm_eps': round(ttm_eps, 4) if ttm_eps else None,
        'pe_min_5y': pe_min_5y,
        'pe_max_5y': pe_max_5y,
        'yield_min_5y': yield_min_5y,
        'yield_max_5y': yield_max_5y,
        'roic_10y_avg': None,
    }


def save_valuation_bands(ticker: str) -> dict:
    ticker_dir = os.path.join(STATIC_DIR, ticker)
    os.makedirs(ticker_dir, exist_ok=True)

    result = fetch_valuation_bands(ticker)

    path = os.path.join(ticker_dir, 'valuation_bands.json')
    with open(path, 'w') as f:
        json.dump(result, f, indent=2)

    print(f"[{ticker}] valuation_bands.json 저장 완료")
    print(f"  현재가: ${result['current_price']} | 연간DPS: ${result['annual_dps']} | 현재PE: {result['current_pe']}")
    print(f"  PE 밴드: {result['pe_min_5y']} ~ {result['pe_max_5y']}")
    if result['yield_min_5y']:
        print(f"  배당수익률 밴드: {result['yield_min_5y']*100:.2f}% ~ {result['yield_max_5y']*100:.2f}%")
    return result
