"""
Score 202: Buy Timing — Simple 7-Factor (100pts)
C1 Value (35pts): F1 yield band
C2 Growth Engine (20pts): F2 payout + weighted DGR
C3 Discount (15pts): F3 MDD
C4 Timing (30pts): F5 SMA + F6 RSI + F7 BB
"""
import os
import json
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
        'div':  read(os.path.join(STATIC_DIR, ticker, 'dividends.json')),
        'fin':  read(os.path.join(STATIC_DIR, ticker, 'financials.json')),
        'mkt':  read(os.path.join(LIVE_DIR,   'market.json')),
    }


def _calc_weighted_dgr(div_data: list) -> float | None:
    """5-year linear-weighted DGR: DGR_Y4*1 + ... + DGR_Y0*5 / 15"""
    from datetime import datetime
    current_year = datetime.today().year

    regular = sorted(
        [d for d in div_data if not d.get('is_special') and d.get('dps', 0) > 0],
        key=lambda x: x['ex_date'],
    )
    if not regular:
        return None

    # Build annual DPS dict by year — exclude current year (incomplete)
    annual: dict[int, float] = {}
    for d in regular:
        yr = int(d['ex_date'][:4])
        if yr < current_year:
            annual[yr] = annual.get(yr, 0.0) + d['dps']

    if len(annual) < 2:
        return None

    years = sorted(annual.keys(), reverse=True)
    # Y0 = most recent full year, need at least 5 YoY growth rates
    dgr_rates = []
    for i in range(min(5, len(years) - 1)):
        y0, y1 = years[i], years[i + 1]
        if annual[y1] > 0:
            dgr_rates.append((annual[y0] - annual[y1]) / annual[y1])

    if len(dgr_rates) < 2:
        return None

    # Pad to 5 with first available if fewer than 5
    while len(dgr_rates) < 5:
        dgr_rates.append(dgr_rates[-1])

    weights = [5, 4, 3, 2, 1]  # Y0 weight=5, Y4 weight=1
    total = sum(r * w for r, w in zip(dgr_rates, weights))
    return total / 15


def _score_f1(vb: dict) -> tuple[float, str]:
    mn, mx, cur = vb.get('yield_min_5y'), vb.get('yield_max_5y'), vb.get('current_yield')
    if None in (mn, mx, cur):
        return 0.0, 'N/A'
    if (mx - mn) == 0:
        return 0.0, 'BAND_MISSING'
    return round(min(35, max(0, (cur - mn) / (mx - mn) * 35)), 2), 'OK'


def _score_f2(vb: dict, div_data: list) -> tuple[float, str]:
    ttm_eps = vb.get('ttm_eps')
    annual_dps = vb.get('annual_dps')
    if not ttm_eps or ttm_eps <= 0 or not annual_dps:
        return 10.0, 'ESTIMATED'  # neutral when EPS unavailable

    payout = annual_dps / ttm_eps
    wdgr = _calc_weighted_dgr(div_data)
    if wdgr is None:
        return 10.0, 'DGR_NA'

    if payout <= 0.65 and wdgr >= 0.10:
        return 20.0, f'PR={payout:.1%},DGR={wdgr:.1%}'
    elif payout <= 0.75 and wdgr > 0.05:
        return 10.0, f'PR={payout:.1%},DGR={wdgr:.1%}'
    return 0.0, f'PR={payout:.1%},DGR={wdgr:.1%}'


def _score_f3(snap: dict) -> tuple[float, str]:
    price, high = snap.get('current_price'), snap.get('high_52w')
    if not price or not high or high == 0:
        return 0.0, 'N/A'
    mdd = (price - high) / high
    if mdd <= -0.20:
        return 15.0, f'MDD={mdd:.1%}'
    elif mdd <= -0.15:
        return 8.0, f'MDD={mdd:.1%}'
    return 0.0, f'MDD={mdd:.1%}'


def _score_f5(snap: dict) -> tuple[float, str]:
    s13, s40 = snap.get('sma_13w'), snap.get('sma_40w')
    if None in (s13, s40):
        return 0.0, 'N/A'
    return (8.0, '13W<40W') if s13 < s40 else (0.0, '13W>=40W')


def _score_f6(snap: dict) -> tuple[float, str]:
    rsi = snap.get('rsi_14w')
    if rsi is None:
        return 0.0, 'N/A'
    if rsi <= 30:
        return 10.0, f'RSI={rsi:.1f}'
    elif rsi <= 40:
        return 7.0, f'RSI={rsi:.1f}'
    elif rsi <= 50:
        return 3.0, f'RSI={rsi:.1f}'
    return 0.0, f'RSI={rsi:.1f}'


def _score_f7(snap: dict) -> tuple[float, str]:
    price, bb_l, bb_m = snap.get('current_price'), snap.get('bb_lower'), snap.get('bb_mid')
    if None in (price, bb_l, bb_m):
        return 0.0, 'N/A'
    span = bb_m - bb_l
    if price <= bb_l:
        return 12.0, 'AT_LOWER'
    elif span > 0 and price <= bb_l + span * 0.33:
        return 8.0, 'NEAR_LOWER'
    elif price < bb_m:
        return 4.0, 'BELOW_MID'
    return 0.0, 'ABOVE_MID'


def compute_202(ticker: str) -> dict:
    d = _load(ticker)
    div_data = d['div'].get('data', [])

    f1, d1 = _score_f1(d['vb'])
    f2, d2 = _score_f2(d['vb'], div_data)
    f3, d3 = _score_f3(d['snap'])
    f5, d5 = _score_f5(d['snap'])
    f6, d6 = _score_f6(d['snap'])
    f7, d7 = _score_f7(d['snap'])

    total = f1 + f2 + f3 + f5 + f6 + f7
    f2_blocked = (f2 == 0)

    if f2_blocked:
        signal = 'F2_BLOCKED'
    elif total >= 80:
        signal = 'IMMEDIATE_BUY'
    elif total >= 60:
        signal = 'WATCH'
    else:
        signal = 'WAIT'

    return {
        'ticker': ticker,
        'score': round(total, 2),
        'signal': signal,
        'f2_blocked': f2_blocked,
        'factors': {
            'f1_yield_band': {'score': f1, 'detail': d1},
            'f2_growth_payout': {'score': f2, 'detail': d2},
            'f3_mdd':        {'score': f3, 'detail': d3},
            'f5_sma':        {'score': f5, 'detail': d5},
            'f6_rsi':        {'score': f6, 'detail': d6},
            'f7_bb':         {'score': f7, 'detail': d7},
        },
    }
