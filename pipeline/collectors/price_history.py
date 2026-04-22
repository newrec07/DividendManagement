import os
import json
import pandas as pd
import ta
import yfinance as yf
from datetime import datetime
from pipeline.config import STATIC_DIR


def fetch_price_history(ticker: str) -> dict:
    today = datetime.today()

    # yfinance: 5년 주봉 (W-FRI resample)
    tk = yf.Ticker(ticker)
    df = tk.history(period='6y', interval='1d', auto_adjust=True)

    if df.empty:
        raise ValueError(f"{ticker}: 주가 데이터 없음")

    df.index = df.index.tz_localize(None)
    df = df[['Open', 'High', 'Low', 'Close', 'Volume']].rename(columns=str.lower)

    # 일봉 → 주봉 (금요일 기준)
    weekly = df.resample('W-FRI').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum',
    }).dropna()

    weekly = weekly.tail(260)
    close = weekly['close']

    weekly['sma_13w'] = close.rolling(window=13).mean()
    weekly['sma_40w'] = close.rolling(window=40).mean()
    weekly['high_52w'] = weekly['high'].rolling(window=52).max()
    weekly['rsi_14w'] = ta.momentum.RSIIndicator(close, window=14).rsi()

    bb = ta.volatility.BollingerBands(close, window=40, window_dev=2)
    weekly['bb_upper'] = bb.bollinger_hband()
    weekly['bb_mid']   = bb.bollinger_mavg()
    weekly['bb_lower'] = bb.bollinger_lband()

    weekly = weekly.round(4)
    weekly.index = weekly.index.strftime('%Y-%m-%d')
    weekly.index.name = 'date'
    records = weekly.reset_index()
    records.columns = [c.lower() for c in records.columns]
    records = records.where(pd.notna(records), None).to_dict(orient='records')

    return {
        'ticker': ticker,
        'updated_at': today.strftime('%Y-%m-%d'),
        'data': records,
    }


def save_price_history(ticker: str) -> dict:
    ticker_dir = os.path.join(STATIC_DIR, ticker)
    os.makedirs(ticker_dir, exist_ok=True)

    result = fetch_price_history(ticker)

    path = os.path.join(ticker_dir, 'price_history.json')
    with open(path, 'w') as f:
        json.dump(result, f, indent=2)

    print(f"[{ticker}] price_history.json 저장 완료 ({len(result['data'])}주)")
    return result
