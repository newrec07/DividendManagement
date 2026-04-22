"""
Score 203: Dividend Sustainability (100pts)
L1 Quantitative (70pts): FCF coverage gate + 8 financial metrics
L2 Qualitative (30pts): EPS revision + insider + news + guidance + credit + regulatory
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
    tickers_raw = read(os.path.join(STATIC_DIR, 'tickers.json'))
    ticker_info = next(
        (t for t in tickers_raw.get('tickers', []) if t['ticker'] == ticker), {}
    )
    return {
        'fin':       read(os.path.join(STATIC_DIR, ticker, 'financials.json')),
        'div':       read(os.path.join(STATIC_DIR, ticker, 'dividends.json')),
        'vb':        read(os.path.join(STATIC_DIR, ticker, 'valuation_bands.json')),
        'news':      read(os.path.join(LIVE_DIR,   ticker, 'news.json')),
        'cons':      read(os.path.join(LIVE_DIR,   ticker, 'consensus.json')),
        'ticker_info': ticker_info,
    }


# ─── LAYER 1 ───────────────────────────────────────────────────────────────────

def _l1_f1_fcf_coverage(cashflow_q: list) -> tuple[str, str]:
    desc = sorted(cashflow_q, key=lambda x: x['date'], reverse=True)
    fcf_vals = [q['fcf'] for q in desc[:4] if q.get('fcf') is not None]
    ttm_fcf = sum(fcf_vals) if len(fcf_vals) == 4 else None

    div_paid_vals = [abs(q.get('dividends_paid') or 0) for q in desc[:4]]
    ttm_div = sum(div_paid_vals)

    if ttm_fcf is None:
        return 'UNKNOWN', 'FCF_NA'
    if ttm_div == 0:
        return 'PASS', f'FCF={ttm_fcf/1e9:.1f}B,DivPaid=NA'

    ratio = ttm_fcf / ttm_div
    return ('PASS' if ratio >= 1.0 else 'FAIL'), f'FCF/Div={ratio:.2f}'


def _l1_f2_cash_payout(cashflow_q: list) -> tuple[float, str]:
    desc = sorted(cashflow_q, key=lambda x: x['date'], reverse=True)
    fcf_vals = [q['fcf'] for q in desc[:4] if q.get('fcf') is not None]
    ttm_fcf = sum(fcf_vals) if len(fcf_vals) == 4 else None
    div_vals = [abs(q.get('dividends_paid') or 0) for q in desc[:4]]
    ttm_div = sum(div_vals)

    if not ttm_fcf or ttm_fcf <= 0:
        return 5.0, 'FCF_NA'
    if ttm_div == 0:
        return 5.0, 'DIVPAID_NA'
    ratio = ttm_div / ttm_fcf
    if ratio <= 0.70:
        return 10.0, f'CPR={ratio:.1%}'
    elif ratio <= 0.85:
        return 5.0, f'CPR={ratio:.1%}'
    return 0.0, f'CPR={ratio:.1%}'


def _l1_f3_eps_cagr(income_q: list) -> tuple[float, str]:
    desc = sorted(income_q, key=lambda x: x['date'], reverse=True)
    recent_ni = sum(q.get('net_income') or 0 for q in desc[:4])

    for years in (10, 7, 5):
        cutoff = (datetime.today() - timedelta(days=365 * years)).strftime('%Y-%m-%d')
        past = [q for q in sorted(income_q, key=lambda x: x['date']) if q['date'] <= cutoff]
        if len(past) >= 4:
            old_ni = sum(q.get('net_income') or 0 for q in past[-4:])
            if old_ni > 0 and recent_ni > 0:
                cagr = (recent_ni / old_ni) ** (1 / years) - 1
                if cagr >= 0.07:
                    return 10.0, f'EPS_CAGR={cagr:.1%}({years}y)'
                elif cagr >= 0.03:
                    return 6.0, f'EPS_CAGR={cagr:.1%}({years}y)'
                elif cagr >= 0:
                    return 3.0, f'EPS_CAGR={cagr:.1%}({years}y)'
                return 0.0, f'EPS_CAGR={cagr:.1%}({years}y)'
    return 3.0, 'HISTORY_SHORT'


def _l1_f4_interest_coverage(income_q: list) -> tuple[float, str]:
    desc = sorted(income_q, key=lambda x: x['date'], reverse=True)
    oi = sum(q.get('operating_income') or 0 for q in desc[:4])
    ie = sum(q.get('interest_expense') or 0 for q in desc[:4])

    if ie <= 0:
        return 10.0, 'NO_INTEREST'
    cov = oi / ie
    if cov >= 5:
        return 10.0, f'IC={cov:.1f}x'
    elif cov >= 3:
        return 6.0, f'IC={cov:.1f}x'
    elif cov >= 1.5:
        return 2.0, f'IC={cov:.1f}x'
    return 0.0, f'IC={cov:.1f}x'


def _l1_f5_retained_earnings(balance_a: list) -> tuple[float, str]:
    data = [r for r in sorted(balance_a, key=lambda x: x['date']) if r.get('retained_earnings') is not None]
    if len(data) < 3:
        return 5.0, 'DATA_NA'
    increases = sum(1 for i in range(1, len(data)) if data[i]['retained_earnings'] > data[i-1]['retained_earnings'])
    ratio = increases / (len(data) - 1)
    if ratio >= 0.70:
        return 10.0, f'RE_UP={ratio:.0%}'
    elif ratio >= 0.40:
        return 5.0, f'RE_MIX={ratio:.0%}'
    return 0.0, f'RE_DOWN={ratio:.0%}'


def _l1_f6_de_ratio(balance_a: list, sector_de: float | None) -> tuple[float, str]:
    if not balance_a:
        return 3.0, 'DATA_NA'
    latest = sorted(balance_a, key=lambda x: x['date'], reverse=True)[0]
    debt = latest.get('total_debt')
    equity = latest.get('total_equity')
    if debt is None or equity is None or equity == 0:
        return 3.0, 'DATA_NA'

    de = debt / abs(equity)

    if sector_de is None or sector_de >= 999:
        if de <= 1.0:
            return 10.0, f'DE={de:.2f}'
        elif de <= 2.0:
            return 6.0, f'DE={de:.2f}'
        elif de <= 3.0:
            return 3.0, f'DE={de:.2f}'
        return 0.0, f'DE={de:.2f}'

    if de <= sector_de * 0.7:
        return 10.0, f'DE={de:.2f},s={sector_de:.2f}'
    elif de <= sector_de * 1.0:
        return 6.0, f'DE={de:.2f},s={sector_de:.2f}'
    elif de <= sector_de * 1.3:
        return 3.0, f'DE={de:.2f},s={sector_de:.2f}'
    return 0.0, f'DE={de:.2f},s={sector_de:.2f}'


def _l1_f7_shares_trend(balance_a: list) -> tuple[float, str]:
    data = sorted([(r['date'], r['shares_outstanding']) for r in balance_a if r.get('shares_outstanding')], key=lambda x: x[0])
    if len(data) < 2:
        return 3.0, 'DATA_NA'
    trend = (data[-1][1] - data[0][1]) / data[0][1]
    if trend <= -0.10:
        return 5.0, f'shares={trend:.1%}'
    elif trend <= 0:
        return 3.0, f'shares={trend:.1%}'
    return 0.0, f'shares={trend:.1%}'


def _l1_f8_roic_wacc(income_q: list, balance_a: list, wacc: float | None) -> tuple[float, str]:
    if wacc is None:
        return 3.0, 'WACC_NA'
    desc = sorted(income_q, key=lambda x: x['date'], reverse=True)
    oi = sum(q.get('operating_income') or 0 for q in desc[:4])
    nopat = oi * (1 - 0.21)
    latest = sorted(balance_a, key=lambda x: x['date'], reverse=True)[0] if balance_a else {}
    invested_capital = (latest.get('total_debt') or 0) + (latest.get('total_equity') or 0)
    if invested_capital <= 0:
        return 0.0, 'IC_NEGATIVE'
    roic = nopat / invested_capital
    if roic > wacc + 0.03:
        return 5.0, f'ROIC={roic:.1%}>WACC={wacc:.1%}'
    elif roic > wacc:
        return 3.0, f'ROIC={roic:.1%}>WACC={wacc:.1%}'
    return 0.0, f'ROIC={roic:.1%}<WACC={wacc:.1%}'


def _l1_f9_dgr_fcf_sync(div_data: list, cashflow_q: list) -> tuple[float, str]:
    from datetime import datetime as _dt
    current_year = _dt.today().year
    regular = sorted(
        [d for d in div_data if not d.get('is_special') and d.get('dps', 0) > 0],
        key=lambda x: x['ex_date'],
    )
    annual: dict[int, float] = {}
    for d in regular:
        yr = int(d['ex_date'][:4])
        if yr < current_year:
            annual[yr] = annual.get(yr, 0.0) + d['dps']
    years = sorted(annual.keys(), reverse=True)
    if len(years) < 6:
        return 5.0, 'HISTORY_SHORT'

    dps_now, dps_5y = annual[years[0]], annual[years[5]]
    dgr_5y = (dps_now / dps_5y) ** (1 / 5) - 1 if dps_5y > 0 else None

    cutoff_5y = (datetime.today() - timedelta(days=365 * 5)).strftime('%Y-%m-%d')
    desc = sorted(cashflow_q, key=lambda x: x['date'], reverse=True)
    ttm_now_vals = [q['fcf'] for q in desc[:4] if q.get('fcf') is not None]
    ttm_now = sum(ttm_now_vals) if len(ttm_now_vals) == 4 else None
    past = [q for q in sorted(cashflow_q, key=lambda x: x['date']) if q['date'] <= cutoff_5y]
    ttm_5y_vals = [q['fcf'] for q in past[-4:] if q.get('fcf') is not None] if len(past) >= 4 else []
    ttm_5y = sum(ttm_5y_vals) if len(ttm_5y_vals) == 4 else None

    if dgr_5y is None or ttm_now is None or ttm_5y is None or ttm_5y <= 0:
        return 5.0, 'DATA_NA'
    fcf_growth = (ttm_now / ttm_5y) ** (1 / 5) - 1

    if dgr_5y <= fcf_growth:
        return 10.0, f'DGR={dgr_5y:.1%}<=FCF={fcf_growth:.1%}'
    elif dgr_5y <= fcf_growth + 0.03:
        return 5.0, f'DGR={dgr_5y:.1%}~FCF={fcf_growth:.1%}'
    return 0.0, f'DGR={dgr_5y:.1%}>FCF={fcf_growth:.1%}'


# ─── LAYER 2 ───────────────────────────────────────────────────────────────────

def _l2_f1_eps_revision(cons: dict) -> tuple[float, str]:
    rev = cons.get('eps_revision_4w', 'NEUTRAL')
    if rev == 'UP':
        return 10.0, 'EPS_UP'
    elif rev == 'NEUTRAL':
        return 5.0, 'EPS_NEUTRAL'
    return 0.0, 'EPS_DOWN'


def _l2_f2_insider() -> tuple[float, str]:
    return 3.0, 'INSIDER_NA'


def _l2_f3_news_tone(news: dict) -> tuple[float, str]:
    tone = news.get('tone', 'NEUTRAL')
    if tone == 'POSITIVE':
        return 10.0, 'POSITIVE'
    elif tone == 'NEUTRAL':
        return 5.0, 'NEUTRAL'
    return 0.0, tone  # NEGATIVE or REDFLAG


def _l2_f4_guidance(news: dict) -> tuple[float, str]:
    text = ' '.join(
        (a.get('title', '') + ' ' + a.get('summary', '')).lower()
        for a in news.get('articles', [])
    )
    if any(k in text for k in ['guidance raised', 'guidance increased', 'raised outlook', 'raised guidance']):
        return 5.0, 'RAISED'
    if any(k in text for k in ['guidance lowered', 'guidance cut', 'guidance withdrawn', 'withdrew guidance', 'guidance lowered']):
        return 0.0, 'LOWERED'
    return 3.0, 'NEUTRAL'


def _l2_f5_credit(news: dict) -> tuple[float, str]:
    text = ' '.join(
        (a.get('title', '') + ' ' + a.get('summary', '')).lower()
        for a in news.get('articles', [])
    )
    if any(k in text for k in ['credit downgrade', 'rating downgrade', 'outlook negative']):
        return 0.0, 'DOWNGRADE'
    if any(k in text for k in ['credit upgrade', 'rating upgrade', 'outlook positive']):
        return 5.0, 'UPGRADE'
    return 5.0, 'STABLE'


def _l2_f6_regulatory(news: dict) -> tuple[float, str]:
    text = ' '.join(
        (a.get('title', '') + ' ' + a.get('summary', '')).lower()
        for a in news.get('articles', [])
    )
    if any(k in text for k in ['antitrust', 'windfall tax', 'regulatory action', 'fine imposed']):
        return 0.0, 'REG_RISK'
    if any(k in text for k in ['regulatory', 'investigation', 'probe']):
        return 2.0, 'REG_WATCH'
    return 5.0, 'CLEAN'


# ─── MAIN ──────────────────────────────────────────────────────────────────────

def compute_203(ticker: str) -> dict:
    d = _load(ticker)
    fin = d['fin']
    income_q = fin.get('income_quarterly', [])
    cashflow_q = fin.get('cashflow_quarterly', [])
    balance_a = fin.get('balance_annual', [])
    div_data = d['div'].get('data', [])
    ti = d['ticker_info']
    wacc = ti.get('wacc')
    sector_de = ti.get('sector_de_ratio')

    fcf_status, fcf_detail = _l1_f1_fcf_coverage(cashflow_q)
    lf2, ld2 = _l1_f2_cash_payout(cashflow_q)
    lf3, ld3 = _l1_f3_eps_cagr(income_q)
    lf4, ld4 = _l1_f4_interest_coverage(income_q)
    lf5, ld5 = _l1_f5_retained_earnings(balance_a)
    lf6, ld6 = _l1_f6_de_ratio(balance_a, sector_de)
    lf7, ld7 = _l1_f7_shares_trend(balance_a)
    lf8, ld8 = _l1_f8_roic_wacc(income_q, balance_a, wacc)
    lf9, ld9 = _l1_f9_dgr_fcf_sync(div_data, cashflow_q)

    l2f1, l2d1 = _l2_f1_eps_revision(d['cons'])
    l2f2, l2d2 = _l2_f2_insider()
    l2f3, l2d3 = _l2_f3_news_tone(d['news'])
    l2f4, l2d4 = _l2_f4_guidance(d['news'])
    l2f5, l2d5 = _l2_f5_credit(d['news'])
    l2f6, l2d6 = _l2_f6_regulatory(d['news'])

    l1_total = lf2 + lf3 + lf4 + lf5 + lf6 + lf7 + lf8 + lf9
    l2_total = l2f1 + l2f2 + l2f3 + l2f4 + l2f5 + l2f6
    total = l1_total + l2_total

    red_flags: list[str] = []
    if fcf_status == 'FAIL':
        red_flags.append('FCF_COVERAGE')
    if lf3 == 0:
        red_flags.append('EPS_NEGATIVE_CAGR')
    if lf4 == 0:
        red_flags.append('INTEREST_COV_LOW')
    if lf5 == 0:
        red_flags.append('RETAINED_EARNINGS_DOWN')
    if lf6 == 0:
        red_flags.append('DE_RATIO_HIGH')
    if lf8 == 0:
        red_flags.append('ROIC_BELOW_WACC')
    if lf9 == 0:
        red_flags.append('DGR_EXCEEDS_FCF')
    if d['news'].get('redflag_detected'):
        red_flags.append('NEWS_REDFLAG')

    if total >= 80:
        signal = 'STRONG'
    elif total >= 60:
        signal = 'CAUTION'
    else:
        signal = 'DANGER'

    return {
        'ticker': ticker,
        'score': round(total, 2),
        'signal': signal,
        'fcf_gate': fcf_status,
        'red_flag_count': len(red_flags),
        'red_flags': red_flags,
        'factors': {
            'l1_fcf_gate':         {'score': None, 'detail': fcf_detail},
            'l1_f2_cash_payout':   {'score': lf2,  'detail': ld2},
            'l1_f3_eps_cagr':      {'score': lf3,  'detail': ld3},
            'l1_f4_interest_cov':  {'score': lf4,  'detail': ld4},
            'l1_f5_retained_earn': {'score': lf5,  'detail': ld5},
            'l1_f6_de_ratio':      {'score': lf6,  'detail': ld6},
            'l1_f7_shares_trend':  {'score': lf7,  'detail': ld7},
            'l1_f8_roic_wacc':     {'score': lf8,  'detail': ld8},
            'l1_f9_dgr_fcf_sync':  {'score': lf9,  'detail': ld9},
            'l2_f1_eps_revision':  {'score': l2f1, 'detail': l2d1},
            'l2_f2_insider':       {'score': l2f2, 'detail': l2d2},
            'l2_f3_news_tone':     {'score': l2f3, 'detail': l2d3},
            'l2_f4_guidance':      {'score': l2f4, 'detail': l2d4},
            'l2_f5_credit':        {'score': l2f5, 'detail': l2d5},
            'l2_f6_regulatory':    {'score': l2f6, 'detail': l2d6},
        },
    }
