"""
Score 201: Buy Timing — Precision 9-Factor (100pts)
C1 Valuation (30pts): F1 yield band + F2 PE band
C2 Performance (30pts): F3 growth + F4 FCF CAGR + F5 payout
C3 Sentiment (20pts): F6 MDD + F7 VIX
C4 Timing (20pts): F8 SMA + F9 RSI + F10 BB
"""
import os
import json
from datetime import datetime, timedelta
from pipeline.config import STATIC_DIR, LIVE_DIR


def _load(ticker: str) -> dict:
    def read(path):
        if os.path.exists(path):
            with open(path) as f:
                return json.load(f)
        return {}
    return {
        'vb':   read(os.path.join(STATIC_DIR, ticker, 'valuation_bands.json')),
        'snap': read(os.path.join(LIVE_DIR,   ticker, 'snapshot.json')),
        'fin':  read(os.path.join(STATIC_DIR, ticker, 'financials.json')),
        'div':  read(os.path.join(STATIC_DIR, ticker, 'dividends.json')),
        'mkt':  read(os.path.join(LIVE_DIR,   'market.json')),
    }


def _ttm_fcf_at(cashflow_q: list, cutoff: str) -> float | None:
    past = [q for q in sorted(cashflow_q, key=lambda x: x['date']) if q['date'] <= cutoff]
    if len(past) < 4:
        return None
    vals = [q['fcf'] for q in past[-4:] if q.get('fcf') is not None]
    return sum(vals) if len(vals) == 4 else None


def _score_f1(vb: dict) -> tuple[float, str]:
    mn, mx, cur = vb.get('yield_min_5y'), vb.get('yield_max_5y'), vb.get('current_yield')
    if None in (mn, mx, cur):
        return 0.0, 'N/A'
    if (mx - mn) == 0:
        return 0.0, 'BAND_MISSING'
    return round(min(15, max(0, (cur - mn) / (mx - mn) * 15)), 2), 'OK'


def _score_f2(vb: dict) -> tuple[float, str]:
    mn, mx, cur = vb.get('pe_min_5y'), vb.get('pe_max_5y'), vb.get('current_pe')
    if None in (mn, mx, cur):
        return 0.0, 'N/A'
    if (mx - mn) == 0:
        return 0.0, 'BAND_MISSING'
    return round(min(15, max(0, (mx - cur) / (mx - mn) * 15)), 2), 'OK'


def _score_f3(income_q: list) -> tuple[float, str]:
    if len(income_q) < 5:
        return 0.0, 'N/A'
    desc = sorted(income_q, key=lambda x: x['date'], reverse=True)
    latest = desc[0]
    yr = latest['date'][:4]
    yoy = next((q for q in desc[4:8] if q['date'][:4] == str(int(yr) - 1)), None)
    if not yoy:
        return 0.0, 'YOY_MISSING'

    rev_pos = (latest.get('revenue') or 0) > (yoy.get('revenue') or 0) > 0
    l_eps = latest.get('eps_diluted') or latest.get('net_income')
    y_eps = yoy.get('eps_diluted') or yoy.get('net_income')
    eps_pos = bool(l_eps and y_eps and y_eps > 0 and l_eps > y_eps)

    if rev_pos and eps_pos:
        return 10.0, 'BOTH_POS'
    elif rev_pos or eps_pos:
        return 5.0, 'ONE_POS'
    return 0.0, 'NO_GROWTH'


def _score_f4(cashflow_q: list) -> tuple[float, str]:
    today = datetime.today().strftime('%Y-%m-%d')
    cutoff_3y = (datetime.today() - timedelta(days=365 * 3)).strftime('%Y-%m-%d')
    desc = sorted(cashflow_q, key=lambda x: x['date'], reverse=True)
    ttm_vals = [q['fcf'] for q in desc[:4] if q.get('fcf') is not None]
    ttm = sum(ttm_vals) if len(ttm_vals) == 4 else None
    ttm_3y = _ttm_fcf_at(cashflow_q, cutoff_3y)
    if ttm is None or ttm_3y is None or ttm_3y <= 0:
        return 0.0, 'N/A'
    cagr = (ttm / ttm_3y) ** (1 / 3) - 1
    if cagr >= 0.10:
        return 10.0, f'CAGR={cagr:.1%}'
    elif cagr > 0:
        return 7.0, f'CAGR={cagr:.1%}'
    return 0.0, f'CAGR={cagr:.1%}'


def _score_f5(vb: dict, income_q: list) -> tuple[float, str]:
    ttm_eps = vb.get('ttm_eps')
    annual_dps = vb.get('annual_dps')
    if ttm_eps and ttm_eps > 0 and annual_dps:
        payout = annual_dps / ttm_eps
        if payout <= 0.60:
            return 10.0, f'PR={payout:.1%}'
        elif payout <= 0.75:
            return 5.0, f'PR={payout:.1%}'
        return 0.0, f'PR={payout:.1%}'
    desc = sorted(income_q, key=lambda x: x['date'], reverse=True)
    ttm_eps_q = sum(q.get('eps_diluted') or 0 for q in desc[:4])
    if ttm_eps_q > 0 and annual_dps:
        payout = annual_dps / ttm_eps_q
        if payout <= 0.60:
            return 10.0, f'PR={payout:.1%}'
        elif payout <= 0.75:
            return 5.0, f'PR={payout:.1%}'
        return 0.0, f'PR={payout:.1%}'
    return 5.0, 'ESTIMATED'


def _score_f6(snap: dict) -> tuple[float, str]:
    price, high = snap.get('current_price'), snap.get('high_52w')
    if not price or not high or high == 0:
        return 0.0, 'N/A'
    mdd = (price - high) / high
    if mdd <= -0.20:
        return 10.0, f'MDD={mdd:.1%}'
    elif mdd <= -0.15:
        return 7.0, f'MDD={mdd:.1%}'
    elif mdd <= -0.10:
        return 4.0, f'MDD={mdd:.1%}'
    return 0.0, f'MDD={mdd:.1%}'


def _score_f7(mkt: dict) -> tuple[float, str]:
    vix = mkt.get('vix_current')
    if vix is None:
        return 4.0, 'VIX_NA'
    if vix >= 30:
        return 10.0, f'VIX={vix:.1f}'
    elif vix >= 25:
        return 7.0, f'VIX={vix:.1f}'
    elif vix >= 20:
        return 4.0, f'VIX={vix:.1f}'
    return 0.0, f'VIX={vix:.1f}'


def _score_f8(snap: dict) -> tuple[float, str]:
    s13, s40 = snap.get('sma_13w'), snap.get('sma_40w')
    if None in (s13, s40):
        return 0.0, 'N/A'
    return (6.0, '13W<40W') if s13 < s40 else (0.0, '13W>=40W')


def _score_f9(snap: dict) -> tuple[float, str]:
    rsi = snap.get('rsi_14w')
    if rsi is None:
        return 0.0, 'N/A'
    if rsi <= 30:
        return 6.0, f'RSI={rsi:.1f}'
    elif rsi <= 40:
        return 4.0, f'RSI={rsi:.1f}'
    elif rsi <= 50:
        return 2.0, f'RSI={rsi:.1f}'
    return 0.0, f'RSI={rsi:.1f}'


def _score_f10(snap: dict) -> tuple[float, str]:
    price, bb_l, bb_m = snap.get('current_price'), snap.get('bb_lower'), snap.get('bb_mid')
    if None in (price, bb_l, bb_m):
        return 0.0, 'N/A'
    span = bb_m - bb_l
    if price <= bb_l:
        return 8.0, 'AT_LOWER'
    elif span > 0 and price <= bb_l + span * 0.33:
        return 5.0, 'NEAR_LOWER'
    elif price < bb_m:
        return 2.0, 'BELOW_MID'
    return 0.0, 'ABOVE_MID'


def compute_201(ticker: str) -> dict:
    d = _load(ticker)
    income_q = d['fin'].get('income_quarterly', [])
    cashflow_q = d['fin'].get('cashflow_quarterly', [])

    f1, d1 = _score_f1(d['vb'])
    f2, d2 = _score_f2(d['vb'])
    f3, d3 = _score_f3(income_q)
    f4, d4 = _score_f4(cashflow_q)
    f5, d5 = _score_f5(d['vb'], income_q)
    f6, d6 = _score_f6(d['snap'])
    f7, d7 = _score_f7(d['mkt'])
    f8, d8 = _score_f8(d['snap'])
    f9, d9 = _score_f9(d['snap'])
    f10, d10 = _score_f10(d['snap'])

    total = f1 + f2 + f3 + f4 + f5 + f6 + f7 + f8 + f9 + f10
    c2_blocked = (f3 == 0 or f4 == 0)

    if c2_blocked:
        signal = 'C2_BLOCKED'
    elif total >= 80:
        signal = 'STRONG_BUY'
    elif total >= 60:
        signal = 'WATCH'
    else:
        signal = 'HOLD'

    return {
        'ticker': ticker,
        'score': round(total, 2),
        'signal': signal,
        'c2_blocked': c2_blocked,
        'factors': {
            'f1_yield_band': {'score': f1,  'detail': d1},
            'f2_pe_band':    {'score': f2,  'detail': d2},
            'f3_growth':     {'score': f3,  'detail': d3},
            'f4_fcf_cagr':   {'score': f4,  'detail': d4},
            'f5_payout':     {'score': f5,  'detail': d5},
            'f6_mdd':        {'score': f6,  'detail': d6},
            'f7_vix':        {'score': f7,  'detail': d7},
            'f8_sma':        {'score': f8,  'detail': d8},
            'f9_rsi':        {'score': f9,  'detail': d9},
            'f10_bb':        {'score': f10, 'detail': d10},
        },
    }
